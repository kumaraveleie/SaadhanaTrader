"""§5.7 — MA crossover (component of Triple confluence).

Faithful Python port of ChrisMoody's *Ultimate Moving Average*
TradingView script (``CM_Ultimate_MA_MTF``). The TC component is the
Sec.5.10 entry; this module is also the stand-alone candidate function
for the deferred ``ma_crossover`` cohort (see §14a registry).

Pine source:
``pine/external_references/ultimate_ma_chrismoody.pine``. The Pine
script is purely visual (plots one or two MAs with direction-coloured
lines and optional cross-dots) — it does NOT emit a "qualified" or
"signal" boolean. The qualified-bullish-crossover semantics in this
module are **port-added** for cohort qualification:
  • ``qualified=True`` requires a fresh bullish crossover within
    ``signal_freshness_bars``, slope_pct ≥ ``min_slope_pct``, AND the
    fast MA rising over ``direction_smoothe_bars`` (Pine's ``smoothe``).
  • ``signal_freshness_bars`` is port-added (not in Pine).

Faithful-port notes:
  • HullMA uses **half-up rounding** of ``sqrt(n)`` to match Pine's
    ``round(sqrt(len))``. Python's built-in ``round()`` is banker's
    rounding (half-to-even); we use ``int(sqrt(n) + 0.5)`` for the
    correct half-up semantics on positive sqrt values.
  • TEMA matches Pine's ``3 * (ema1 - ema2) + ema3`` (algebraically
    identical to ``3*ema1 - 3*ema2 + ema3``).
  • ``direction_smoothe_bars`` (default 2) mirrors Pine's ``smoothe``
    input — it gates the qualified flag on whether the fast MA has
    risen over the trailing ``smoothe`` bars (Pine: ``ma_up = out1
    >= out1[smoothe]``). In Pine this drives line colour only; in
    our cohort context it acts as a secondary anti-whipsaw filter
    alongside the slope-on-slow-MA check.
  • Multi-timeframe support (Pine: ``security(tickerid, res, out)``)
    is **deferred** for v1 — the §14a registry locks Triple confluence
    + MA crossover cohorts to ``timeframes_supported=['daily']`` per
    Sec.14a.4. MTF is a Wave 1+ extension.

Pure-function design per CLAUDE.md: takes a DataFrame, returns a
dict — no side effects, no I/O. The TS mirror must agree to ≤ 1e-6
tolerance (parity tests in S2.x).
"""

from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np
import pandas as pd

from saadhana_filter.indicators.primitives import ema, sma

MAType = Literal["SMA", "EMA", "WMA", "HullMA", "VWMA", "RMA", "TEMA"]
ALLOWED_MA_TYPES: tuple[MAType, ...] = (
    "SMA",
    "EMA",
    "WMA",
    "HullMA",
    "VWMA",
    "RMA",
    "TEMA",
)


class MACrossoverResult(TypedDict, total=False):
    qualified: bool
    fast_ma: float | None
    slow_ma: float | None
    slope_pct: float | None
    crossover_bar: int | None
    ma_type: str
    reason: str


def _wma(s: pd.Series, n: int) -> pd.Series:
    """Linear-weighted moving average. Weights are 1..n; latest bar is heaviest."""
    weights = np.arange(1, n + 1, dtype=float)
    weight_sum = weights.sum()

    def _w(window: np.ndarray) -> float:
        return float(np.dot(window, weights) / weight_sum)

    return s.rolling(n, min_periods=n).apply(_w, raw=True)


def _hull(s: pd.Series, n: int) -> pd.Series:
    """Hull MA = WMA(2*WMA(s, n/2) − WMA(s, n), round(sqrt(n))).

    Matches Pine's ``ta.hma()`` definition exactly. Pine uses
    ``round(sqrt(len))`` (half-up); Python's ``round()`` is banker's
    rounding so we use ``int(sqrt(n) + 0.5)`` for half-up semantics
    on positive sqrt values. ``len/2`` in Pine v3 (the version of the
    source script) performs integer division on int inputs, matching
    our ``int(n // 2)``.
    """
    half = max(1, int(n // 2))
    sqrt_n = max(1, int(np.sqrt(n) + 0.5))  # half-up to match Pine round()
    raw = 2.0 * _wma(s, half) - _wma(s, n)
    return _wma(raw, sqrt_n)


def _vwma(close: pd.Series, volume: pd.Series, n: int) -> pd.Series:
    """Volume-weighted moving average over n bars."""
    pv = (close * volume).rolling(n, min_periods=n).sum()
    v = volume.rolling(n, min_periods=n).sum()
    return pv / v.replace(0.0, np.nan)


def _rma(s: pd.Series, n: int) -> pd.Series:
    """RMA (Wilder's smoothing) — same as EMA with alpha = 1/n."""
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _tema(s: pd.Series, n: int) -> pd.Series:
    """Triple EMA: 3·EMA − 3·EMA(EMA) + EMA(EMA(EMA)).

    Needs ~3·n bars to warm up; before that the result has NaN.
    """
    e1 = ema(s, n)
    e2 = ema(e1, n)
    e3 = ema(e2, n)
    return 3.0 * e1 - 3.0 * e2 + e3


def _compute_ma(
    df: pd.DataFrame,
    *,
    n: int,
    ma_type: MAType,
    source: str,
) -> pd.Series:
    """Dispatch a single MA computation based on ``ma_type``.

    ``source`` is the column name (``close``, ``hl2``, ``ohlc4``, …);
    ``hl2`` and ``ohlc4`` are computed on the fly when the column is
    not pre-materialised.
    """
    if source == "close":
        s = df["close"]
    elif source == "hl2":
        s = (df["high"] + df["low"]) / 2.0
    elif source == "ohlc4":
        s = (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
    elif source in df.columns:
        s = df[source]
    else:
        raise ValueError(f"unknown ma source: {source!r}")

    if ma_type == "SMA":
        return sma(s, n)
    if ma_type == "EMA":
        return ema(s, n)
    if ma_type == "WMA":
        return _wma(s, n)
    if ma_type == "HullMA":
        return _hull(s, n)
    if ma_type == "VWMA":
        return _vwma(s, df["volume"], n)
    if ma_type == "RMA":
        return _rma(s, n)
    if ma_type == "TEMA":
        return _tema(s, n)
    raise ValueError(f"unknown ma_type: {ma_type!r}")


def compute_ma_crossover(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    fast_period: int = 20,
    slow_period: int = 50,
    ma_type: MAType = "TEMA",
    slope_window: int = 3,
    min_slope_pct: float = 0.0,
    direction_smoothe_bars: int = 2,
    signal_freshness_bars: int = 5,
    source: str = "close",
) -> MACrossoverResult:
    """Sec.5.7 candidate function.

    Returns the result for ``on_bar`` (default = last bar of ``df``).
    The slow MA is locked to EMA per spec — ``ma_type`` only controls
    the fast MA, matching Pine's behaviour (``avg2`` is always EMA via
    ``atype2 == 1`` defaults in the source script's two-MA setup).

    Qualified semantics (port-added; Pine is viz-only):
      • A bullish crossover (``fast`` was ≤ ``slow``, now strictly >)
        fired within the trailing ``signal_freshness_bars``;
      • Slow-MA slope ≥ ``min_slope_pct`` over ``slope_window`` bars
        (default 0.0 — pure crossover; raise to filter weak trends);
      • Fast MA is rising over the trailing ``direction_smoothe_bars``
        (Pine: ``ma_up = out1 >= out1[smoothe]``). In Pine this drives
        line colour; here it acts as a secondary anti-whipsaw filter.
    """
    if ma_type not in ALLOWED_MA_TYPES:
        raise ValueError(
            f"ma_type must be one of {ALLOWED_MA_TYPES}, got {ma_type!r}"
        )

    if on_bar is None:
        on_bar = len(df) - 1

    # Required history per spec §5.7 edge case + a generous TEMA warm-up.
    # The fast-MA smoothing check needs at least ``direction_smoothe_bars``
    # of history; included in the binding max.
    min_bars_needed = max(
        slow_period + slope_window,
        slow_period + direction_smoothe_bars,
    )
    if ma_type == "TEMA":
        min_bars_needed = max(min_bars_needed, 3 * fast_period)
    if on_bar < min_bars_needed:
        return MACrossoverResult(
            qualified=False,
            fast_ma=None,
            slow_ma=None,
            slope_pct=None,
            crossover_bar=None,
            ma_type=ma_type,
            reason="insufficient_history",
        )

    fast_ma = _compute_ma(df, n=fast_period, ma_type=ma_type, source=source)
    slow_ma = _compute_ma(df, n=slow_period, ma_type="EMA", source=source)

    f_now, s_now = fast_ma.iloc[on_bar], slow_ma.iloc[on_bar]
    if pd.isna(f_now) or pd.isna(s_now):
        return MACrossoverResult(
            qualified=False,
            fast_ma=None,
            slow_ma=None,
            slope_pct=None,
            crossover_bar=None,
            ma_type=ma_type,
            reason="ma_warmup_nan",
        )

    slow_lag = slow_ma.iloc[on_bar - slope_window]
    slope_pct = float((s_now - slow_lag) / slow_lag * 100.0) if slow_lag else 0.0

    # Pine's ``ma_up = out1 >= out1[smoothe]`` — direction-smoothing
    # check on the FAST MA over ``direction_smoothe_bars``. Without
    # MTF support, ``out1 = avg`` so this collapses to a fast-MA
    # rising check.
    f_lag = fast_ma.iloc[on_bar - direction_smoothe_bars]
    fast_rising = bool(not pd.isna(f_lag) and f_now >= f_lag)

    # Walk back up to signal_freshness_bars looking for the most
    # recent bullish cross (fast was ≤ slow, then strictly >).
    crossover_bar: int | None = None
    earliest = max(min_bars_needed, on_bar - signal_freshness_bars + 1)
    for i in range(on_bar, earliest - 1, -1):
        if i - 1 < 0:
            break
        f_i, s_i = fast_ma.iloc[i], slow_ma.iloc[i]
        f_prev, s_prev = fast_ma.iloc[i - 1], slow_ma.iloc[i - 1]
        if any(pd.isna(v) for v in (f_i, s_i, f_prev, s_prev)):
            continue
        if f_prev <= s_prev and f_i > s_i:
            crossover_bar = i
            break

    qualified = bool(
        crossover_bar is not None
        and slope_pct >= min_slope_pct
        and f_now > s_now
        and fast_rising
    )
    return MACrossoverResult(
        qualified=qualified,
        fast_ma=float(f_now),
        slow_ma=float(s_now),
        slope_pct=slope_pct,
        crossover_bar=crossover_bar,
        ma_type=ma_type,
    )
