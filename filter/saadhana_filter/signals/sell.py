"""§8 — SELL exit triggers for held positions.

A position generates SELL the moment **any** of these triggers fires.
Triggers are evaluated in spec order so the first match wins (and is
recorded as the outcome enum in the §17 ledger).

Hard stops (§8.1, full close):
- ``STOP_HIT``            — close ≤ current_stop
- ``CATASTROPHIC_BREAK``  — close < 50-EMA on RVOL ≥ 2.0x

Profit-tier triggers (§8.2, partial close, then trail):
- ``T1_HIT``              — close ≥ entry × 1.05  (sell 33%, stop → breakeven)
- ``T2_HIT``              — close ≥ entry × 1.10  (sell 33%, trail with 20-EMA)
- ``T3_TRAIL_BREAK``      — close < 20-EMA after T2 hit (final 33%)

Trend-deterioration (§8.3, full close):
- ``STAGE_SHIFT_EXIT``    — Stage 2 → Stage 3 (close < 30W SMA, SMA flat/falling)
- ``SCORE_COLLAPSE_EXIT`` — Pro-Setup Score ≤ 5 for 2 consecutive days
- ``INST_SELL_EXIT``      — institutional SELL on 2 of last 5 bars
- ``RSI_DIVERGENCE_EXIT`` — RSI > 80 with bearish divergence vs price

Time-based (§8.4, optional):
- ``TIME_EXIT``           — between −2% and +2% for 30 days with declining score
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import numpy as np
import pandas as pd

from saadhana_filter.indicators.conditions import _flow_flags, pro_setup_score
from saadhana_filter.indicators.primitives import ema, rsi, rvol, sma

# ──────────────────────────────────────────────────────────────────────────
# Spec constants (§8)
# ──────────────────────────────────────────────────────────────────────────
CATASTROPHIC_RVOL = 2.0
SCORE_COLLAPSE_THRESHOLD = 5
SCORE_COLLAPSE_CONSECUTIVE_DAYS = 2
INST_SELL_LOOKBACK = 5
INST_SELL_REQUIRED = 2
RSI_DIVERGENCE_THRESHOLD = 80.0
RSI_DIVERGENCE_LOOKBACK = 14
TIME_EXIT_DAYS = 30
TIME_EXIT_BAND_PCT = 0.02
T1_TRIGGER_PCT = 0.05
T2_TRIGGER_PCT = 0.10


class SellReason(StrEnum):
    """§17 outcome enum subset — populated when SELL fires."""

    STOP_HIT = "STOP_HIT"
    CATASTROPHIC_BREAK = "CATASTROPHIC_BREAK"
    T1_HIT = "T1_HIT"
    T2_HIT = "T2_HIT"
    T3_TRAIL_BREAK = "T3_TRAIL_BREAK"
    STAGE_SHIFT_EXIT = "STAGE_SHIFT_EXIT"
    SCORE_COLLAPSE_EXIT = "SCORE_COLLAPSE_EXIT"
    INST_SELL_EXIT = "INST_SELL_EXIT"
    RSI_DIVERGENCE_EXIT = "RSI_DIVERGENCE_EXIT"
    TIME_EXIT = "TIME_EXIT"


@dataclass(frozen=True)
class Position:
    """Open-position state carried into §8 evaluation.

    Stops widen only via the §7 ladder (T1 → breakeven, T2 → trail with
    20-EMA). The ledger (Phase H) is the source of truth; this dataclass
    is the snapshot the engine sees on a given scan day.
    """

    symbol: str
    entry_date: date
    entry_price: float
    initial_stop: float
    current_stop: float
    t1_hit: bool = False
    t2_hit: bool = False


def _is_partial(reason: SellReason) -> bool:
    """T1 / T2 / T3 are partial closes; everything else is a full close."""
    return reason in {SellReason.T1_HIT, SellReason.T2_HIT, SellReason.T3_TRAIL_BREAK}


def evaluate_sell(df: pd.DataFrame, position: Position) -> SellReason | None:
    """§8 — evaluate SELL triggers in spec order. Returns the first match
    or ``None`` if none fire.

    ``df`` must include enough lookback to compute 200-EMA, ATR(14),
    RVOL(50), 30W SMA, RSI(14) and the §5 Pro-Setup Score series.
    """
    last = df.iloc[-1]
    close_today = float(last["close"])

    # §8.1 — hard stops
    if close_today <= position.current_stop:
        return SellReason.STOP_HIT

    e50 = ema(df["close"], 50).iloc[-1]
    today_rvol = rvol(df["volume"], 50).iloc[-1]
    if (
        not pd.isna(e50)
        and close_today < e50
        and not pd.isna(today_rvol)
        and today_rvol >= CATASTROPHIC_RVOL
    ):
        return SellReason.CATASTROPHIC_BREAK

    # §8.2 — profit ladder
    # T3 trails the 20-EMA only after T2 hit.
    e20 = ema(df["close"], 20).iloc[-1]
    if position.t2_hit and not pd.isna(e20) and close_today < e20:
        return SellReason.T3_TRAIL_BREAK
    if not position.t2_hit and close_today >= position.entry_price * (1 + T2_TRIGGER_PCT):
        return SellReason.T2_HIT
    if not position.t1_hit and close_today >= position.entry_price * (1 + T1_TRIGGER_PCT):
        return SellReason.T1_HIT

    # §8.3 — trend deterioration
    sma_30w = sma(df["close"], 150)
    if not pd.isna(sma_30w.iloc[-1]):
        sma_falling = sma_30w.diff().iloc[-1] <= 0
        if close_today < sma_30w.iloc[-1] and sma_falling:
            return SellReason.STAGE_SHIFT_EXIT

    score_series = pro_setup_score(df)["score"]
    if len(score_series) >= SCORE_COLLAPSE_CONSECUTIVE_DAYS:
        recent = score_series.iloc[-SCORE_COLLAPSE_CONSECUTIVE_DAYS:]
        if (recent <= SCORE_COLLAPSE_THRESHOLD).all():
            return SellReason.SCORE_COLLAPSE_EXIT

    _buys, sells = _flow_flags(df)
    if sells.iloc[-INST_SELL_LOOKBACK:].sum() >= INST_SELL_REQUIRED:
        return SellReason.INST_SELL_EXIT

    if _rsi_bearish_divergence(df):
        return SellReason.RSI_DIVERGENCE_EXIT

    # §8.4 — time exit (optional). Not yet wired; needs entry context.
    if _time_exit(df, position, score_series):
        return SellReason.TIME_EXIT

    return None


def _rsi_bearish_divergence(df: pd.DataFrame) -> bool:
    """RSI > 80 today AND a bearish divergence vs price in last N bars.

    Bearish divergence here = price made a higher high than ``N`` bars
    ago while RSI made a lower high. Both conditions must hold.
    """
    r = rsi(df["close"], 14)
    if pd.isna(r.iloc[-1]) or r.iloc[-1] <= RSI_DIVERGENCE_THRESHOLD:
        return False
    if len(df) <= RSI_DIVERGENCE_LOOKBACK:
        return False
    price_now = df["close"].iloc[-1]
    price_then = df["close"].iloc[-RSI_DIVERGENCE_LOOKBACK]
    rsi_now = r.iloc[-1]
    rsi_then = r.iloc[-RSI_DIVERGENCE_LOOKBACK]
    if pd.isna(rsi_then):
        return False
    return bool(price_now > price_then and rsi_now < rsi_then)


def _time_exit(df: pd.DataFrame, position: Position, score: pd.Series) -> bool:
    """§8.4 — between ±2% of entry for 30 days with score declining."""
    if position.entry_date is None:
        return False
    days_since_entry = (df.index[-1].date() - position.entry_date).days
    if days_since_entry < TIME_EXIT_DAYS:
        return False
    last_n_close = df["close"].iloc[-TIME_EXIT_DAYS:]
    if last_n_close.empty:
        return False
    pct = (last_n_close - position.entry_price) / position.entry_price
    in_band = pct.abs().max() <= TIME_EXIT_BAND_PCT
    if not in_band:
        return False
    # Score declining over the last 30 bars
    if len(score) < TIME_EXIT_DAYS:
        return False
    score_window = score.iloc[-TIME_EXIT_DAYS:]
    declining = bool(np.polyfit(range(len(score_window)), score_window.values, 1)[0] < 0)
    return declining
