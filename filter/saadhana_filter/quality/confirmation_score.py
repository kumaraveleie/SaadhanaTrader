"""Sec.0.7.6 — Confirmation Score Filter (candidate Diamond Layer 7).

For each (symbol, signal_date), compute a 0-5 score combining five
independent end-of-day-readable signals. Used as a post-hoc filter
on cohort qualified candidates: cohort fires → confirmation score
gates → trade taken.

Per-component contract for BUY signals (the only direction we
support in v2). The mirrored SELL semantics are documented inline
for the future short-side cohorts but not implemented here.

  +1  RSI(14) > 45        — momentum not extremely oversold
  +1  ADX(14) > 15        — trend strength sufficient (not whipsaw)
  +1  close > VWAP(20)    — price above 20-bar volume-weighted mean
  +1  MACD line > signal  — short-term momentum aligned with trend
  +1  close > SMA(20)     — price above mid-line of BB(20) band

The score collapses to an integer 0..5; the cohort declares an
optional ``min_confirmation_score`` threshold (typical: 2 of 5 mild,
3 of 5 strict, 4-5 of 5 Diamond-tier).

Daily-VWAP note: classical VWAP is a session-anchored intraday
metric; on daily bars we substitute a 20-bar rolling VWAP
(``∑(close × volume) / ∑(volume)`` over the last 20 bars). This
matches what TradingView's daily-chart "VWAP" pseudoindicator does
when forced onto a daily timeframe.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
import pandas as pd

from saadhana_filter.indicators.primitives import ema, macd, rsi, sma


class ConfirmationScoreResult(TypedDict, total=False):
    score: int                   # 0..5
    rsi_pass: bool
    adx_pass: bool
    vwap_pass: bool
    macd_pass: bool
    bb_pass: bool
    rsi_value: float | None
    adx_value: float | None
    vwap_value: float | None
    macd_hist: float | None
    sma20_value: float | None
    reason: str


# ─────────────────────────────────────────────────────────────────────
# ADX (Welles Wilder) — not in primitives.py; lives here to keep the
# discipline module self-contained.
# ─────────────────────────────────────────────────────────────────────
def _adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Return ADX(n) using Wilder's smoothing.

    DM+ = max(high − high[1], 0) when greater than max(low[1] − low, 0)
    DM− = max(low[1] − low, 0)  when greater than max(high − high[1], 0)
    TR  = max(high − low, |high − close[1]|, |low − close[1]|)
    DI+ = 100 × Wilder(DM+) / Wilder(TR)
    DI- = 100 × Wilder(DM-) / Wilder(TR)
    DX  = 100 × |DI+ − DI−| / (DI+ + DI−)
    ADX = Wilder(DX) over n bars
    """
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    # Wilder's smoothing = EMA with alpha = 1/n.
    plus_dm_n = plus_dm.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    minus_dm_n = minus_dm.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    tr_n = tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    plus_di = 100.0 * plus_dm_n / tr_n.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm_n / tr_n.replace(0.0, np.nan)
    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    return dx.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _rolling_vwap(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Rolling N-bar VWAP — daily-bar substitute for intraday session VWAP.

    Numerator: cumulative (close × volume) over the last n bars.
    Denominator: cumulative volume over the last n bars.
    """
    pv = (df["close"] * df["volume"]).rolling(n, min_periods=n).sum()
    v = df["volume"].rolling(n, min_periods=n).sum()
    return pv / v.replace(0.0, np.nan)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────
def compute_confirmation_score(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    rsi_threshold: float = 45.0,
    adx_threshold: float = 15.0,
    vwap_window: int = 20,
    sma_window: int = 20,
    side: str = "BUY",
) -> ConfirmationScoreResult:
    """Compute the 0-5 confirmation score at ``on_bar`` (default: last bar).

    For ``side='BUY'`` (default), each component contributes +1 when its
    bullish condition holds. ``side='SELL'`` mirrors the inequalities
    (reserved; v2 cohorts are long-only).
    """
    if on_bar is None:
        on_bar = len(df) - 1
    if on_bar < max(adx_threshold and 14, vwap_window, sma_window, 26 + 9):  # MACD slow + signal
        return ConfirmationScoreResult(
            score=0,
            rsi_pass=False,
            adx_pass=False,
            vwap_pass=False,
            macd_pass=False,
            bb_pass=False,
            rsi_value=None,
            adx_value=None,
            vwap_value=None,
            macd_hist=None,
            sma20_value=None,
            reason="insufficient_history",
        )

    close = df["close"]
    rsi14 = rsi(close, 14)
    adx14 = _adx(df, 14)
    vwap_n = _rolling_vwap(df, vwap_window)
    macd_df = macd(close, 12, 26, 9)
    sma20 = sma(close, sma_window)

    rsi_v = float(rsi14.iloc[on_bar]) if not pd.isna(rsi14.iloc[on_bar]) else None
    adx_v = float(adx14.iloc[on_bar]) if not pd.isna(adx14.iloc[on_bar]) else None
    vwap_v = float(vwap_n.iloc[on_bar]) if not pd.isna(vwap_n.iloc[on_bar]) else None
    macd_line = float(macd_df["macd"].iloc[on_bar]) if not pd.isna(macd_df["macd"].iloc[on_bar]) else None
    macd_signal = float(macd_df["signal"].iloc[on_bar]) if not pd.isna(macd_df["signal"].iloc[on_bar]) else None
    sma20_v = float(sma20.iloc[on_bar]) if not pd.isna(sma20.iloc[on_bar]) else None
    close_v = float(close.iloc[on_bar])

    if side.upper() == "BUY":
        rsi_pass = rsi_v is not None and rsi_v > rsi_threshold
        adx_pass = adx_v is not None and adx_v > adx_threshold
        vwap_pass = vwap_v is not None and close_v > vwap_v
        macd_pass = (
            macd_line is not None and macd_signal is not None and macd_line > macd_signal
        )
        bb_pass = sma20_v is not None and close_v > sma20_v
    else:  # SELL
        rsi_pass = rsi_v is not None and rsi_v < (100.0 - rsi_threshold)
        adx_pass = adx_v is not None and adx_v > adx_threshold
        vwap_pass = vwap_v is not None and close_v < vwap_v
        macd_pass = (
            macd_line is not None and macd_signal is not None and macd_line < macd_signal
        )
        bb_pass = sma20_v is not None and close_v < sma20_v

    score = int(rsi_pass) + int(adx_pass) + int(vwap_pass) + int(macd_pass) + int(bb_pass)

    return ConfirmationScoreResult(
        score=score,
        rsi_pass=bool(rsi_pass),
        adx_pass=bool(adx_pass),
        vwap_pass=bool(vwap_pass),
        macd_pass=bool(macd_pass),
        bb_pass=bool(bb_pass),
        rsi_value=rsi_v,
        adx_value=adx_v,
        vwap_value=vwap_v,
        macd_hist=(macd_line - macd_signal) if (macd_line is not None and macd_signal is not None) else None,
        sma20_value=sma20_v,
    )
