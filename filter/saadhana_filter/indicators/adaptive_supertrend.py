"""§5.8 — Adaptive SuperTrend (component of Triple confluence).

Faithful Python port of AlgoAlpha's *ML Adaptive SuperTrend*
TradingView script. The K-means output (the cluster centroid the
current ATR maps to) **replaces the raw ATR** in the SuperTrend
formula — a single SuperTrend ``factor`` (default 3.0) is multiplied
by that variable centroid. This is the meaningful adaptive behaviour:
in calm regimes the centroid is small (tight bands), in volatile
regimes the centroid is large (wide bands). There is **no** separate
"low/mid/high multiplier" model — that was a misreading of the source
script in the previous port.

Pine source:
``pine/external_references/ml_adaptive_supertrend_algoalpha.pine``.
This module is a clean-room reimplementation of the math in that file.

Direction sign convention — DOCUMENTED, NOT A BUG:
  Pine's ``dir == -1`` means uptrend (Pine: ``superTrend := dir == -1
  ? lowerBand : upperBand``); ``bullish_signal = ta.crossunder(dir, 0)``
  fires when dir transitions from ≥0 to <0. Our port returns ``+1`` for
  uptrend to stay consistent with every other indicator in the codebase.
  The K-means and SuperTrend math are identical to Pine; only the sign
  on the returned ``direction`` field is inverted relative to Pine.

Faithful-port notes:
  • K-means seeding uses linear interpolation between min/max ATR over
    ``training_data_period`` (Pine: ``low + (high - low) * percentile``
    for percentiles {0.25, 0.5, 0.75}). No RNG, no seed parameter — the
    full iteration is deterministic given the input series.
  • Pine's strict-inequality cluster assignment is preserved: a point
    is assigned to a cluster only when its distance to that cluster is
    strictly less than to BOTH others. Tied points are unassigned for
    that iteration (rare on continuous-valued ATR; matches Pine).
  • ``confirm_signals=True`` (default) is the Pine non-repainting
    convention: a bullish flip detected at bar ``j`` is reported as
    ``qualified`` only on bar ``j+1`` — the next confirmed close.
  • ``signal_freshness_bars`` is port-added for cohort qualification,
    not present in the Pine source.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np
import pandas as pd

from saadhana_filter.indicators.primitives import atr as wilder_atr

ClusterLabel = Literal["low", "mid", "high", "init"]


class AdaptiveSuperTrendResult(TypedDict, total=False):
    qualified: bool
    direction: int  # +1 uptrend / -1 downtrend / 0 unset
    super_trend: float | None
    active_cluster: ClusterLabel
    assigned_centroid: float | None
    factor: float | None
    flip_bar: int | None
    atr_value: float | None
    reason: str


def _kmeans_3_linear_seeds(
    volatility_window: np.ndarray, *, max_iter: int = 50
) -> np.ndarray:
    """Pine-faithful K-means(3) on a 1-D ATR window.

    Initial centroids: ``low + (high - low) * percentile`` for
    percentiles {0.25, 0.5, 0.75} (low/mid/high).
    Convergence: iterate until centroids stabilise (or ``max_iter``).
    Strict-inequality assignment: a point is assigned only when its
    distance to one centroid is strictly less than to BOTH others
    (matches Pine). Tied points are unassigned for that iteration.
    Empty clusters keep the previous centroid (Pine: na-mean would
    halt the while loop; we preserve the prior centroid instead so
    the iteration can continue toward stability on the other clusters).

    Returns the sorted centroids (ascending: low, mid, high).
    """
    finite = volatility_window[np.isfinite(volatility_window)]
    if finite.size < 3:
        # Not enough data — return three identical centers; the caller
        # treats this via the standard cluster-assignment path (all
        # distances equal → cluster 0 wins via argmin).
        return np.full(3, float(finite.mean()) if finite.size else 0.0)

    vol_low = float(finite.min())
    vol_high = float(finite.max())
    span = vol_high - vol_low
    if span == 0.0:
        return np.full(3, vol_low)

    # Pine-faithful linear-interpolation seeds.
    centroids = np.array(
        [
            vol_low + span * 0.25,  # low
            vol_low + span * 0.5,   # mid
            vol_low + span * 0.75,  # high
        ],
        dtype=float,
    )

    for _ in range(max_iter):
        d_low = np.abs(finite - centroids[0])
        d_mid = np.abs(finite - centroids[1])
        d_high = np.abs(finite - centroids[2])

        # Strict-inequality assignment per Pine.
        in_low = (d_low < d_mid) & (d_low < d_high)
        in_mid = (d_mid < d_low) & (d_mid < d_high)
        in_high = (d_high < d_low) & (d_high < d_mid)

        new_centroids = centroids.copy()
        if in_low.any():
            new_centroids[0] = float(finite[in_low].mean())
        if in_mid.any():
            new_centroids[1] = float(finite[in_mid].mean())
        if in_high.any():
            new_centroids[2] = float(finite[in_high].mean())

        if np.allclose(new_centroids, centroids, rtol=0.0, atol=1e-12):
            centroids = new_centroids
            break
        centroids = new_centroids

    return np.sort(centroids)


def compute_adaptive_supertrend(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    atr_period: int = 10,
    training_data_period: int = 100,
    factor: float = 3.0,
    signal_freshness_bars: int = 3,
    confirm_signals: bool = True,
) -> AdaptiveSuperTrendResult:
    """Sec.5.8 candidate function — faithful AlgoAlpha port.

    Computes ATR(``atr_period``), runs K-means(3) on the trailing
    ``training_data_period`` ATR values with linear-interp seeds,
    picks the centroid the current ATR is closest to, and computes
    SuperTrend with that centroid as the ATR substitute multiplied
    by ``factor``. ``qualified=True`` requires a bullish flip within
    the trailing ``signal_freshness_bars``.

    With ``confirm_signals=True`` (Pine default), the qualified flip
    is detected on the bar AFTER it happens (non-repainting).
    """
    if on_bar is None:
        on_bar = len(df) - 1

    # ATR(atr_period) finite from index atr_period - 1; K-means slice
    # of training_data_period bars must all be finite, so the first
    # K-means bar is at index (atr_period - 1) + (training_data_period - 1)
    # = atr_period + training_data_period - 2. Need at least one bar
    # of K-means history, so total bars ≥ atr_period + training_data_period - 1.
    min_bars_needed = atr_period + training_data_period - 1
    if on_bar + 1 < min_bars_needed:
        return AdaptiveSuperTrendResult(
            qualified=False,
            direction=0,
            super_trend=None,
            active_cluster="init",
            assigned_centroid=None,
            factor=None,
            flip_bar=None,
            atr_value=None,
            reason="insufficient_history",
        )

    sub = df.iloc[: on_bar + 1].copy()
    atr_series = wilder_atr(sub, atr_period)
    atr_arr = atr_series.to_numpy(dtype=float)

    if not np.isfinite(atr_arr[-1]) or atr_arr[-1] <= 0:
        return AdaptiveSuperTrendResult(
            qualified=False,
            direction=0,
            super_trend=None,
            active_cluster="init",
            assigned_centroid=None,
            factor=None,
            flip_bar=None,
            atr_value=None,
            reason="atr_nan_or_nonpositive",
        )

    high = sub["high"].to_numpy(dtype=float)
    low = sub["low"].to_numpy(dtype=float)
    close = sub["close"].to_numpy(dtype=float)
    hl2 = (high + low) / 2.0
    n_bars = len(close)

    # Trajectory storage.
    super_trend = np.full(n_bars, np.nan)
    direction = np.zeros(n_bars, dtype=int)  # 0 = unset
    final_upper = np.full(n_bars, np.nan)
    final_lower = np.full(n_bars, np.nan)
    centroid_used = np.full(n_bars, np.nan)
    cluster_labels: list[ClusterLabel] = ["init"] * n_bars

    for i in range(n_bars):
        if not np.isfinite(atr_arr[i]) or atr_arr[i] <= 0:
            continue
        # K-means window: trailing training_data_period bars, all finite.
        if i + 1 < training_data_period:
            continue
        window = atr_arr[i + 1 - training_data_period : i + 1]
        if not np.all(np.isfinite(window)):
            continue

        # TODO(wave-7.7-automl): K-means runs every bar in the trajectory
        # — faithful to Pine but expensive at ~25-30 min per cohort run on
        # 497 symbols × 750 days. Optimization candidate: cache centroids
        # across consecutive bars (window changes by 1 bar/step → centroids
        # drift slowly → re-fit every 10 bars → ~10x speedup). Validate
        # via a per-bar-fit vs cached comparison on a backtest sample to
        # ensure signal sequences stay byte-identical or within tolerance.
        centroids = _kmeans_3_linear_seeds(window)

        # Assign current ATR to the closest centroid by absolute distance.
        # Tie-break: argmin selects the first (lowest-index) on ties,
        # which after sorting means the smaller-vol cluster wins —
        # consistent with Pine's distances.indexof(distances.min()).
        atr_now = atr_arr[i]
        dists = np.abs(centroids - atr_now)
        cluster_idx = int(np.argmin(dists))
        assigned_centroid = float(centroids[cluster_idx])
        cluster_labels[i] = ("low", "mid", "high")[cluster_idx]
        centroid_used[i] = assigned_centroid

        # SuperTrend bands using the centroid as the ATR substitute.
        basic_upper = hl2[i] + factor * assigned_centroid
        basic_lower = hl2[i] - factor * assigned_centroid

        # Pine ratchet logic.
        if i == 0 or not np.isfinite(final_upper[i - 1]):
            final_upper[i] = basic_upper
            final_lower[i] = basic_lower
        else:
            # Pine: lowerBand := lowerBand > prevLowerBand or close[1] < prevLowerBand
            #                    ? lowerBand : prevLowerBand
            if basic_lower > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]:
                final_lower[i] = basic_lower
            else:
                final_lower[i] = final_lower[i - 1]
            # Pine: upperBand := upperBand < prevUpperBand or close[1] > prevUpperBand
            #                    ? upperBand : prevUpperBand
            if basic_upper < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]:
                final_upper[i] = basic_upper
            else:
                final_upper[i] = final_upper[i - 1]

        # Direction logic. Pine convention is inverted (Pine: -1=up, +1=down).
        # We translate at the boundary so direction[i] == +1 means uptrend
        # in our convention (consistent with the rest of the codebase).
        #
        # Pine:
        #   if na(atr[1]):                                  _direction := 1   (initial: down)
        #   else if prevSuperTrend == prevUpperBand:        _direction := close > upperBand ? -1 : 1
        #   else:                                            _direction := close < lowerBand ? 1 : -1
        # Our convention (+1 = uptrend):
        if i == 0 or not np.isfinite(super_trend[i - 1]):
            direction[i] = -1  # Pine na(atr[1]) initial = downtrend → our -1
        elif super_trend[i - 1] == final_upper[i - 1]:
            # Were on upper band (downtrend in Pine = -1 in ours).
            # Pine: close > upper ? -1 : 1 → ours: close > upper ? +1 : -1.
            direction[i] = +1 if close[i] > final_upper[i] else -1
        else:
            # Were on lower band (uptrend in Pine = +1 in ours).
            # Pine: close < lower ? 1 : -1 → ours: close < lower ? -1 : +1.
            direction[i] = -1 if close[i] < final_lower[i] else +1

        # Pine: superTrend := _direction == -1 ? lowerBand : upperBand
        # Our convention: +1 = uptrend → walk up the lower band.
        super_trend[i] = final_lower[i] if direction[i] == +1 else final_upper[i]

    # Bullish-flip detection.
    flip_bar: int | None = None
    if confirm_signals:
        # Pine: bullish_signal = ta.crossunder(dir[1], 0)
        # → flip detected on the bar AFTER it occurred.
        # Look for a bar j-1 in the window where the direction transitioned
        # to +1, with j (the confirmation bar) in
        # [on_bar - signal_freshness_bars + 1 .. on_bar].
        earliest_confirm = max(2, on_bar - signal_freshness_bars + 1)
        for j in range(on_bar, earliest_confirm - 1, -1):
            if (
                direction[j - 1] == +1
                and direction[j - 2] != +1
            ):
                flip_bar = j - 1  # actual flip bar; j is its confirmation bar
                break
    else:
        earliest = max(1, on_bar - signal_freshness_bars + 1)
        for i in range(on_bar, earliest - 1, -1):
            if direction[i] == +1 and direction[i - 1] != +1:
                flip_bar = i
                break

    direction_now = int(direction[on_bar])
    qualified = bool(flip_bar is not None and direction_now == +1)

    return AdaptiveSuperTrendResult(
        qualified=qualified,
        direction=direction_now,
        super_trend=(
            float(super_trend[on_bar]) if np.isfinite(super_trend[on_bar]) else None
        ),
        active_cluster=cluster_labels[on_bar],
        assigned_centroid=(
            float(centroid_used[on_bar]) if np.isfinite(centroid_used[on_bar]) else None
        ),
        factor=float(factor),
        flip_bar=flip_bar,
        atr_value=float(atr_arr[on_bar]),
    )
