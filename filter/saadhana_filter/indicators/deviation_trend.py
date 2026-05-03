"""§5.9 — Deviation Trend (component of Triple confluence).

Faithful Python port of BigBeluga's *Deviation Trend Profile*
TradingView script. The indicator name says "Deviation Trend" and the
input group is labeled "Standart Deviation Levels", but the actual
math is **ATR-based bands around an SMA centerline** — neither std-dev
nor linear regression. Trend detection is a 5-bar SMA slope normalized
over the trailing 500-bar maximum, with hysteresis at ±0.1 normalized-
slope crossings.

The Pine source lives at
``pine/external_references/deviation_trend_bigbeluga.pine``. This
module is a clean-room reimplementation of the math in that file.
Volume-profile rendering from the source is intentionally out of
scope (chart-side visual, not a candidate-function input).

Faithful-port quirk: Pine's
``ta.percentile_linear_interpolation(slope, 500, 100)`` returns the
maximum of ``slope`` over the trailing 500 bars. When that maximum
is ≤ 0 (rare — all slopes in window non-positive), the normalization
produces nonsense ratios. We do **not** guard against this — the
ratio passes through and any spurious flip is recorded. Forensics
§18 catches such cases via drift detection.

Note: ``signal_freshness_bars`` is a port-added cohort-qualification
parameter, not present in BigBeluga's Pine source.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
import pandas as pd

from saadhana_filter.indicators.primitives import atr as wilder_atr
from saadhana_filter.indicators.primitives import sma


class DeviationTrendResult(TypedDict, total=False):
    qualified: bool
    direction: int  # +1 bullish · -1 bearish · 0 not-yet-determined
    avg: float | None
    atr_value: float | None
    upper_1: float | None
    upper_2: float | None
    upper_3: float | None
    lower_1: float | None
    lower_2: float | None
    lower_3: float | None
    slope_5: float | None
    slope_norm: float | None
    flip_bar: int | None
    reason: str


def compute_deviation_trend(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    sma_length: int = 50,
    atr_length: int = 200,
    slope_lag: int = 5,
    percentile_window: int = 500,
    slope_threshold: float = 0.1,
    signal_freshness_bars: int = 3,
) -> DeviationTrendResult:
    """Sec.5.9 candidate function — faithful BigBeluga port.

    Trend transitions follow Pine's ``var trend`` hysteresis rule:
    bullish on ``crossover(slope_norm, +slope_threshold)`` while not
    already bullish; bearish on ``crossunder(slope_norm, -slope_threshold)``
    while currently bullish. Until the first bullish crossover,
    ``direction`` stays 0 (Pine's ``var trend = na`` initial state).
    """
    if on_bar is None:
        on_bar = len(df) - 1

    # ATR(atr_length) needs atr_length bars; the rolling-max over
    # percentile_window of slope_lag-differences needs
    # percentile_window + slope_lag bars.
    min_bars_needed = max(atr_length, percentile_window + slope_lag) + 1
    if on_bar + 1 < min_bars_needed:
        return DeviationTrendResult(
            qualified=False,
            direction=0,
            avg=None,
            atr_value=None,
            upper_1=None, upper_2=None, upper_3=None,
            lower_1=None, lower_2=None, lower_3=None,
            slope_5=None,
            slope_norm=None,
            flip_bar=None,
            reason="insufficient_history",
        )

    sub = df.iloc[: on_bar + 1]
    if (
        sub["close"].isna().any()
        or sub["high"].isna().any()
        or sub["low"].isna().any()
    ):
        return DeviationTrendResult(
            qualified=False,
            direction=0,
            reason="nan_input",
        )

    avg_series = sma(sub["close"], sma_length)
    atr_series = wilder_atr(sub, atr_length)

    avg_now = float(avg_series.iloc[-1])
    atr_now = float(atr_series.iloc[-1])

    # 5-bar SMA slope (avg - avg[5]) and its rolling-max normalisation.
    slope_series = avg_series - avg_series.shift(slope_lag)
    slope_max = slope_series.rolling(
        percentile_window, min_periods=percentile_window
    ).max()

    # Suppress numpy's divide-by-zero warning when slope_max is 0 —
    # the resulting NaN/inf is intentional and handled in the loop.
    with np.errstate(divide="ignore", invalid="ignore"):
        slope_norm_series = slope_series / slope_max

    norm_arr = slope_norm_series.to_numpy(dtype=float)
    direction_arr = np.zeros(len(norm_arr), dtype=int)
    current_trend = 0
    last_bullish_flip: int | None = None

    for i in range(1, len(norm_arr)):
        n_now = norm_arr[i]
        n_prev = norm_arr[i - 1]
        # Treat NaN OR inf as "no measurement" — same as Pine's na.
        if not np.isfinite(n_now) or not np.isfinite(n_prev):
            direction_arr[i] = current_trend
            continue
        # Bullish flip: crossover(+slope_threshold) AND not currently +1.
        if (
            n_prev <= slope_threshold
            and n_now > slope_threshold
            and current_trend != +1
        ):
            current_trend = +1
            last_bullish_flip = i
        # Bearish flip: crossunder(-slope_threshold) AND currently +1.
        elif (
            n_prev >= -slope_threshold
            and n_now < -slope_threshold
            and current_trend == +1
        ):
            current_trend = -1
        direction_arr[i] = current_trend

    direction_now = int(direction_arr[on_bar])

    flip_bar: int | None = None
    if (
        last_bullish_flip is not None
        and on_bar - last_bullish_flip < signal_freshness_bars
    ):
        flip_bar = last_bullish_flip

    qualified = bool(flip_bar is not None and direction_now == +1)

    slope_now_val = float(slope_series.iloc[-1])
    slope_norm_now = (
        float(slope_norm_series.iloc[-1])
        if np.isfinite(slope_norm_series.iloc[-1])
        else None
    )

    return DeviationTrendResult(
        qualified=qualified,
        direction=direction_now,
        avg=avg_now,
        atr_value=atr_now,
        upper_1=avg_now + atr_now * 1.0,
        upper_2=avg_now + atr_now * 2.0,
        upper_3=avg_now + atr_now * 3.0,
        lower_1=avg_now - atr_now * 1.0,
        lower_2=avg_now - atr_now * 2.0,
        lower_3=avg_now - atr_now * 3.0,
        slope_5=slope_now_val,
        slope_norm=slope_norm_now,
        flip_bar=flip_bar,
    )
