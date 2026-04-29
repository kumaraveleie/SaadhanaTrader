"""§5.4 + §6 + §7 — risk levels and the Downside Resistance Score.

``risk_levels(df)`` packages everything a BUY signal needs at entry:
the entry price (today's close), the initial stop, and the §7 profit
ladder targets (T1 +5%, T2 +10%; T3 trails the 20-EMA).

``downside_resistance_score(df)`` produces the §6 transparency metric
(0..100). It is *descriptive*, not used to decide BUY/SELL — it lives
alongside the signal so the user can eyeball the historical drawdown
risk profile of the candidate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from saadhana_filter.indicators.primitives import atr, ema, entry_stop, sma

# ──────────────────────────────────────────────────────────────────────────
# §6 Downside Resistance Score component weights (sum to 100)
# ──────────────────────────────────────────────────────────────────────────
DRS_WEIGHTS: dict[str, int] = {
    "stage_2_strength": 20,
    "distance_from_52wl": 15,
    "atr_tightness": 15,
    "inst_flow_90d": 20,
    "ema_stack_quality": 15,
    "drawdown_depth_recent": 15,
}

PROFIT_T1_PCT = 0.05
PROFIT_T2_PCT = 0.10


@dataclass(frozen=True)
class RiskLevels:
    """§5.4 + §7 — paired entry/stop/target levels emitted with each BUY."""

    entry_price: float
    stop_loss: float
    target_t1: float
    target_t2: float
    risk_pct: float
    reward_pct: float  # to T1
    rr_ratio: float  # T1 reward / stop risk


def risk_levels(df: pd.DataFrame) -> RiskLevels:
    """Compute entry/stop/T1/T2 from the most recent bar of ``df``.

    Stop is the §5.4 ``entry_stop`` primitive (max of 20-EMA and
    5-bar low − ATR×0.5). Targets are the spec §7 profit-ladder rungs
    (+5%, +10% from entry).
    """
    close = df["close"]
    a = atr(df, 14)
    stop = entry_stop(df, atr_series=a)
    entry = float(close.iloc[-1])
    s = float(stop.iloc[-1])
    t1 = entry * (1.0 + PROFIT_T1_PCT)
    t2 = entry * (1.0 + PROFIT_T2_PCT)
    risk = (entry - s) / entry
    reward = (t1 - entry) / entry
    rr = reward / risk if risk > 0 else 0.0
    return RiskLevels(
        entry_price=entry,
        stop_loss=s,
        target_t1=t1,
        target_t2=t2,
        risk_pct=risk,
        reward_pct=reward,
        rr_ratio=rr,
    )


# ──────────────────────────────────────────────────────────────────────────
# §6 Downside Resistance Score
# ──────────────────────────────────────────────────────────────────────────
def _stage_2_strength(close: pd.Series, sma_30w: pd.Series) -> float:
    """(close − 30W SMA) / 30W SMA, clamped to [0, 1]."""
    if pd.isna(sma_30w.iloc[-1]) or sma_30w.iloc[-1] <= 0:
        return 0.0
    raw = (close.iloc[-1] - sma_30w.iloc[-1]) / sma_30w.iloc[-1]
    return float(np.clip(raw, 0.0, 1.0))


def _distance_from_52wl(close: pd.Series, low_52w: pd.Series) -> float:
    """(close − 52WL) / 52WL, capped at 100% then normalized to [0, 1]."""
    if pd.isna(low_52w.iloc[-1]) or low_52w.iloc[-1] <= 0:
        return 0.0
    raw = (close.iloc[-1] - low_52w.iloc[-1]) / low_52w.iloc[-1]
    return float(np.clip(raw, 0.0, 1.0))


def _atr_tightness(close: pd.Series, atr_series: pd.Series) -> float:
    """1 − ATR(14) / close, clamped to [0, 1]. Lower vol → higher score."""
    if pd.isna(atr_series.iloc[-1]) or close.iloc[-1] <= 0:
        return 0.0
    return float(np.clip(1.0 - atr_series.iloc[-1] / close.iloc[-1], 0.0, 1.0))


def _inst_flow_90d(df: pd.DataFrame) -> float:
    """Cumulative institutional accumulation (90 bars) normalized to [0, 1].

    Same buy/sell flag definition as §5.3: up-bar with RVOL ≥ 1.5x is a
    buy, down-bar with RVOL ≥ 1.5x is a sell.
    """
    from saadhana_filter.indicators.conditions import _flow_flags  # local to avoid cycle

    buys, sells = _flow_flags(df)
    score = (buys.rolling(90, min_periods=90).sum() - sells.rolling(90, min_periods=90).sum()).iloc[
        -1
    ]
    if pd.isna(score):
        return 0.0
    # 30 net buys over 90 bars is a strong accumulation; normalize that
    # to ~1.0 and clamp.
    return float(np.clip(score / 30.0, 0.0, 1.0))


def _ema_stack_quality(close: pd.Series) -> float:
    """5 > 20 > 50 > 200 in clean order → 1.0; each violation drops 0.25."""
    e5 = ema(close, 5).iloc[-1]
    e20 = ema(close, 20).iloc[-1]
    e50 = ema(close, 50).iloc[-1]
    e200 = ema(close, 200).iloc[-1]
    if any(pd.isna(v) for v in (e5, e20, e50, e200)):
        return 0.0
    score = 1.0
    if not (e5 > e20):
        score -= 0.25
    if not (e20 > e50):
        score -= 0.25
    if not (e50 > e200):
        score -= 0.25
    return float(np.clip(score, 0.0, 1.0))


def _drawdown_depth_recent(close: pd.Series) -> float:
    """1 − max-drawdown over last 90 bars, normalized to [0, 1]."""
    window = close.tail(90)
    if len(window) < 2:
        return 0.0
    rolling_max = window.cummax()
    dd = (window / rolling_max - 1.0).min()  # most negative
    if pd.isna(dd):
        return 0.0
    return float(np.clip(1.0 + dd, 0.0, 1.0))


def downside_resistance_score(df: pd.DataFrame) -> float:
    """§6 — return a 0..100 transparency metric on the most recent bar.

    Each component contributes its weight × normalized [0, 1] value.
    The final score is the integer sum, in [0, 100].
    """
    close = df["close"]
    sma_30w = sma(close, 150)
    a = atr(df, 14)
    low_52w = df["low"].rolling(252, min_periods=60).min()

    components = {
        "stage_2_strength": _stage_2_strength(close, sma_30w),
        "distance_from_52wl": _distance_from_52wl(close, low_52w),
        "atr_tightness": _atr_tightness(close, a),
        "inst_flow_90d": _inst_flow_90d(df),
        "ema_stack_quality": _ema_stack_quality(close),
        "drawdown_depth_recent": _drawdown_depth_recent(close),
    }
    weighted = sum(DRS_WEIGHTS[k] * v for k, v in components.items())
    return float(np.clip(weighted, 0.0, 100.0))
