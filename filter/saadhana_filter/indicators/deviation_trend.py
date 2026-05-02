"""§5.9 — Deviation Trend (component of Triple confluence).

Adapts BigBeluga's *Deviation Trend Profile* TradingView script. A
linear-regression line fit on the trailing ``length`` bars (anchored
at the most recent swing-low pivot) plus std-dev bands at ``dev_mult``
sigma. Trend direction flips when close pierces a band; the cohort
``qualified=True`` requires a bullish band cross AND positive slope —
the slope filter is what kills sideways false positives.

The volume-profile visualisation from BigBeluga's script is
intentionally out of scope (chart-side, not a candidate-function
input). This module only emits the trend-band signal.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
import pandas as pd


class DeviationTrendResult(TypedDict, total=False):
    qualified: bool
    direction: int  # +1 or -1
    trend_line: float | None
    upper: float | None
    lower: float | None
    slope: float | None
    sigma: float | None
    cross_bar: int | None
    reason: str


def _find_swing_low_pivot(low: np.ndarray, *, lookback: int) -> int | None:
    """Return the index of the most recent confirmed swing-low pivot,
    or ``None`` if no pivot lives in the array.

    A pivot at index ``i`` requires ``low[i]`` to be the minimum of
    bars ``[i-lookback, i+lookback]`` — so the most recent confirmable
    pivot is at most ``lookback`` bars from the end.
    """
    n = len(low)
    for i in range(n - lookback - 1, lookback - 1, -1):
        window = low[i - lookback : i + lookback + 1]
        if low[i] == window.min():
            return i
    return None


def _regression_line_and_sigma(close: np.ndarray) -> tuple[float, float, float, float]:
    """Fit ``y = slope * x + intercept`` over the full ``close`` array.

    Returns ``(slope, intercept, sigma, trend_value_at_last_bar)``.
    ``sigma`` is the population std-dev (ddof=0) of residuals, matching
    Pine's ``ta.stdev()`` default.
    """
    n = len(close)
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, close, 1)
    fitted = slope * x + intercept
    resid = close - fitted
    sigma = float(np.std(resid, ddof=0))
    trend_value = float(slope * (n - 1) + intercept)
    return float(slope), float(intercept), sigma, trend_value


def compute_deviation_trend(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    length: int = 100,
    dev_mult: float = 2.0,
    pivot_lookback: int = 5,
    signal_freshness_bars: int = 3,
    min_init_bars: int = 100,
) -> DeviationTrendResult:
    """Sec.5.9 candidate function.

    Returns the result for ``on_bar`` (default = last bar of ``df``).
    """
    if on_bar is None:
        on_bar = len(df) - 1

    n_bars = on_bar + 1
    if n_bars < max(length, min_init_bars):
        return DeviationTrendResult(
            qualified=False,
            direction=0,
            trend_line=None,
            upper=None,
            lower=None,
            slope=None,
            sigma=None,
            cross_bar=None,
            reason="insufficient_history",
        )

    close_full = df["close"].iloc[: on_bar + 1].to_numpy(dtype=float)
    high_full = df["high"].iloc[: on_bar + 1].to_numpy(dtype=float)
    low_full = df["low"].iloc[: on_bar + 1].to_numpy(dtype=float)
    if (
        np.isnan(close_full[-length:]).any()
        or np.isnan(high_full[-length:]).any()
        or np.isnan(low_full[-length:]).any()
    ):
        return DeviationTrendResult(
            qualified=False,
            direction=0,
            trend_line=None,
            upper=None,
            lower=None,
            slope=None,
            sigma=None,
            cross_bar=None,
            reason="nan_input",
        )

    # Pivot anchor — find most recent swing-low in the trailing length.
    window_low = low_full[-length:]
    pivot_offset = _find_swing_low_pivot(window_low, lookback=pivot_lookback)
    no_pivot_anchor = pivot_offset is None

    # Anchor index in window-local coords. If no pivot, use bar 0
    # (first bar of the window) per spec graceful fallback.
    anchor = pivot_offset if pivot_offset is not None else 0

    # Fit regression on the slice from anchor to end-of-window. The
    # spec says the line is "anchored at the pivot" — taking the slice
    # from anchor onwards realises that.
    fit_window = window_low[anchor:]
    fit_close = close_full[-length:][anchor:]
    if fit_close.size < 5:
        # Pivot near the very end — slice too small to fit; fall back
        # to the full window with a reason flag.
        fit_close = close_full[-length:]
        no_pivot_anchor = True
    slope, intercept, sigma, trend_now = _regression_line_and_sigma(fit_close)

    upper_now = trend_now + dev_mult * sigma
    lower_now = trend_now - dev_mult * sigma

    # Build the per-bar bands across the window so the cross detection
    # has prior-bar values to compare against.
    n_fit = fit_close.size
    x = np.arange(n_fit, dtype=float)
    fitted = slope * x + intercept
    upper_arr = fitted + dev_mult * sigma
    lower_arr = fitted - dev_mult * sigma

    # Direction state per bar within the fit window.
    direction = np.zeros(n_fit, dtype=int)
    direction[0] = +1 if fit_close[0] >= fitted[0] else -1
    for i in range(1, n_fit):
        if fit_close[i] > upper_arr[i - 1]:
            direction[i] = +1
        elif fit_close[i] < lower_arr[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]

    direction_now = int(direction[-1])

    # Find most recent bullish cross within signal_freshness_bars.
    cross_bar: int | None = None
    earliest = max(1, n_fit - signal_freshness_bars)
    for i in range(n_fit - 1, earliest - 1, -1):
        if direction[i - 1] != +1 and direction[i] == +1:
            # Translate window-local index back to df-absolute index.
            cross_bar = on_bar - (n_fit - 1 - i)
            break

    # Degenerate sigma (perfectly flat residuals) — treat any
    # close ≠ trend as a cross. Forensics flag.
    degenerate_sigma = sigma == 0.0

    qualified = bool(
        cross_bar is not None
        and direction_now == +1
        and slope > 0.0
    )

    result = DeviationTrendResult(
        qualified=qualified,
        direction=direction_now,
        trend_line=float(trend_now),
        upper=float(upper_now),
        lower=float(lower_now),
        slope=float(slope),
        sigma=float(sigma),
        cross_bar=cross_bar,
    )
    if no_pivot_anchor:
        result["reason"] = "no_pivot_anchor"
    elif degenerate_sigma:
        result["reason"] = "degenerate_sigma"
    return result
