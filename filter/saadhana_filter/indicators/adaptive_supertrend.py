"""§5.8 — Adaptive SuperTrend (component of Triple confluence).

Adapts AlgoAlpha's *ML Adaptive SuperTrend* TradingView script. The
ATR multiplier is *learned* from a rolling K-means fit on the trailing
ATR series — band tightens in calm regimes, widens in volatile ones.

K-means is hand-rolled with ``n_clusters=3`` so the spec's
``kmeans_random_state`` reproducibility lock holds without an sklearn
dependency. A small init+Lloyd's algorithm on 50 floats is trivially
fast and fully deterministic given a fixed seed.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np
import pandas as pd

from saadhana_filter.indicators.primitives import atr as wilder_atr

ClusterLabel = Literal["low", "mid", "high", "init", "degenerate"]


class AdaptiveSuperTrendResult(TypedDict, total=False):
    qualified: bool
    direction: int  # +1 or -1
    active_band: float | None
    active_cluster: ClusterLabel
    mult_used: float | None
    flip_bar: int | None
    atr_i: float | None
    reason: str


def _kmeans_3(values: np.ndarray, *, seed: int, max_iter: int = 50) -> np.ndarray:
    """Tiny deterministic K-means for 3 clusters on a 1-D array.

    Returns sorted cluster centers (ascending). Re-running with the
    same ``seed`` and ``values`` produces byte-identical centers — the
    determinism guarantee required by Sec.5.8 golden case #6.

    Initial centers use percentile seeding (10/50/90) to converge fast
    on volatility regimes. Lloyd's algorithm iterates until labels
    stabilise or ``max_iter`` is reached.
    """
    rng = np.random.default_rng(seed)
    finite = values[np.isfinite(values)]
    if finite.size < 3:
        # Not enough data — return three identical centers so the
        # caller's degenerate-cluster check fires.
        return np.full(3, float(finite.mean()) if finite.size else 0.0)

    # Percentile seeding + a tiny rng-driven jitter for tie-break
    # determinism across identical percentile values.
    centers = np.percentile(finite, [10, 50, 90]).astype(float)
    centers += rng.normal(0, 1e-9, size=3)

    labels = np.zeros(finite.shape, dtype=int)
    for _ in range(max_iter):
        # Assign each point to the nearest center.
        distances = np.abs(finite[:, None] - centers[None, :])
        new_labels = distances.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        # Update centers; preserve previous center on empty cluster.
        for k in range(3):
            members = finite[labels == k]
            if members.size:
                centers[k] = members.mean()

    return np.sort(centers)


def _classify_cluster(atr_i: float, centers: np.ndarray) -> int:
    """Return 0/1/2 = low/mid/high based on nearest sorted center."""
    distances = np.abs(centers - atr_i)
    return int(distances.argmin())


def compute_adaptive_supertrend(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    atr_period: int = 14,
    cluster_window: int = 50,
    mult_low: float = 1.0,
    mult_mid: float = 2.0,
    mult_high: float = 3.0,
    kmeans_random_state: int = 20260502,
    min_init_bars: int = 100,
    signal_freshness_bars: int = 3,
    flat_vol_threshold_pct: float = 0.001,
) -> AdaptiveSuperTrendResult:
    """Sec.5.8 candidate function.

    Computes ATR(14), runs K-means(3) on the trailing ``cluster_window``
    ATR values, picks the multiplier corresponding to the cluster
    closest to ``ATR_i``, and runs the SuperTrend band logic with that
    multiplier. ``qualified=True`` requires a bullish band flip within
    the trailing ``signal_freshness_bars``.
    """
    if on_bar is None:
        on_bar = len(df) - 1

    n_bars = on_bar + 1
    if n_bars < atr_period + 5:
        return AdaptiveSuperTrendResult(
            qualified=False,
            direction=0,
            active_band=None,
            active_cluster="init",
            mult_used=None,
            flip_bar=None,
            atr_i=None,
            reason="insufficient_history",
        )

    sub = df.iloc[: on_bar + 1].copy()
    atr_series = wilder_atr(sub, atr_period)
    atr_i = atr_series.iloc[-1]
    if pd.isna(atr_i):
        return AdaptiveSuperTrendResult(
            qualified=False,
            direction=0,
            active_band=None,
            active_cluster="init",
            mult_used=None,
            flip_bar=None,
            atr_i=None,
            reason="atr_nan",
        )

    # Determine active multiplier + cluster label.
    if n_bars < min_init_bars:
        mult_used = mult_mid
        active_cluster: ClusterLabel = "init"
    else:
        window = atr_series.iloc[-cluster_window:].to_numpy()
        centers = _kmeans_3(window, seed=kmeans_random_state)
        spread = float(centers[-1] - centers[0])
        # Degenerate = all centers within 0.001 of each other (spec edge case).
        if spread < 0.001:
            mult_used = mult_mid
            active_cluster = "degenerate"
        else:
            cluster_idx = _classify_cluster(float(atr_i), centers)
            mult_used = (mult_low, mult_mid, mult_high)[cluster_idx]
            active_cluster = ("low", "mid", "high")[cluster_idx]

    # Flat-vol regime flag (forensics signal — spec edge case).
    close_now = float(sub["close"].iloc[-1])
    if close_now > 0 and float(atr_i) / close_now < flat_vol_threshold_pct:
        # Not a hard reject — spec says "low-confidence regime", not
        # "skip". Keep computing the band but surface this in the
        # return so forensics can count it.
        flat_vol = True
    else:
        flat_vol = False

    # SuperTrend bands. We need the full trajectory to track the flip.
    high = sub["high"].to_numpy(dtype=float)
    low = sub["low"].to_numpy(dtype=float)
    close = sub["close"].to_numpy(dtype=float)
    hl2 = (high + low) / 2.0
    atr_arr = atr_series.to_numpy(dtype=float)

    final_upper = np.full(n_bars, np.nan)
    final_lower = np.full(n_bars, np.nan)
    direction = np.zeros(n_bars, dtype=int)  # +1 / -1; 0 = unset

    for i in range(n_bars):
        if not np.isfinite(atr_arr[i]):
            continue
        basic_upper = hl2[i] + mult_used * atr_arr[i]
        basic_lower = hl2[i] - mult_used * atr_arr[i]

        if i == 0 or not np.isfinite(final_upper[i - 1]):
            final_upper[i] = basic_upper
            final_lower[i] = basic_lower
            direction[i] = +1 if close[i] > hl2[i] else -1
            continue

        # Final bands: ratchet logic per spec.
        if close[i - 1] <= final_upper[i - 1]:
            final_upper[i] = min(basic_upper, final_upper[i - 1])
        else:
            final_upper[i] = basic_upper
        if close[i - 1] >= final_lower[i - 1]:
            final_lower[i] = max(basic_lower, final_lower[i - 1])
        else:
            final_lower[i] = basic_lower

        # Direction logic.
        prev_dir = direction[i - 1] if direction[i - 1] != 0 else +1
        if prev_dir == +1:
            direction[i] = -1 if close[i] < final_lower[i] else +1
        else:
            direction[i] = +1 if close[i] > final_upper[i] else -1

    direction_now = int(direction[on_bar]) if direction[on_bar] != 0 else +1

    # Find most recent bullish flip within signal_freshness_bars.
    flip_bar: int | None = None
    earliest = max(1, on_bar - signal_freshness_bars + 1)
    for i in range(on_bar, earliest - 1, -1):
        if direction[i - 1] == -1 and direction[i] == +1:
            flip_bar = i
            break

    qualified = bool(flip_bar is not None and direction_now == +1)
    if direction_now == +1:
        active_band: float | None = float(final_lower[on_bar])
    else:
        active_band = float(final_upper[on_bar])

    result = AdaptiveSuperTrendResult(
        qualified=qualified,
        direction=direction_now,
        active_band=active_band,
        active_cluster=active_cluster,
        mult_used=float(mult_used),
        flip_bar=flip_bar,
        atr_i=float(atr_i),
    )
    if flat_vol:
        result["reason"] = "flat_vol_regime"
    return result
