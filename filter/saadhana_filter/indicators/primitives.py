"""Shared indicator math used by §5 conditions.

Each function is a pure transform: takes a DataFrame or Series, returns a
Series aligned to the input index. No side effects, no I/O. The TypeScript
mirror in ``trader/app/lib/indicators/`` must produce identical numbers
to ≤ 1e-6 tolerance (§16 parity tests).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    """Standard exponential moving average; same convention as TradingView."""
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    """Simple moving average over ``n`` bars."""
    return s.rolling(n, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI(n) using EMA-style smoothing of gains and losses."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.where(avg_loss != 0.0, 100.0)  # all gains → RSI 100
    return out


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Standard MACD: fast EMA − slow EMA, signal EMA, and histogram."""
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    line = fast_ema - slow_ema
    sig = ema(line, signal)
    hist = line - sig
    return pd.DataFrame({"macd": line, "signal": sig, "hist": hist}, index=close.index)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder's ATR(n). Expects ``high``, ``low``, ``close`` columns."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def bollinger_bandwidth(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    """Bollinger Band width as % of mid: ``(upper − lower) / mid * 100``."""
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return ((mid + k * sd) - (mid - k * sd)) / mid * 100.0


def rvol(volume: pd.Series, n: int = 50) -> pd.Series:
    """Relative volume: today / ``n``-bar simple average (excluding today).

    Computed as ``volume / volume.shift(1).rolling(n).mean()`` so the
    denominator is point-in-time and never includes the bar being scored.
    """
    avg = volume.shift(1).rolling(n, min_periods=n).mean()
    return volume / avg


def weekly_resample(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly (Friday close).

    Uses pandas' ``W-FRI`` to align with NSE weekly bars. Volume sums;
    OHLC follows standard week aggregation (open=first, high=max,
    low=min, close=last).
    """
    rule = "W-FRI"
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    return df.resample(rule).agg(agg).dropna(how="any")


def entry_stop(df: pd.DataFrame, atr_series: pd.Series | None = None) -> pd.Series:
    """§5.4 — entry stop = max(20-EMA, 5-bar low − ATR(14) × 0.5).

    ``5-bar low`` excludes the current bar (uses bars t-5..t-1) so the
    stop level is determined before today's price is known. ATR can be
    passed in to avoid double computation; otherwise it's computed here.
    """
    ema20 = ema(df["close"], 20)
    a = atr(df, 14) if atr_series is None else atr_series
    five_bar_low = df["low"].shift(1).rolling(5, min_periods=5).min()
    return pd.concat([ema20, five_bar_low - 0.5 * a], axis=1).max(axis=1)
