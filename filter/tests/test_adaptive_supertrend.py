"""Tests for Sec.5.8 — Adaptive SuperTrend (faithful AlgoAlpha port).

Covers spec golden-fixture cases. Fixtures are synthesised
deterministically inside the tests (no I/O, no fragile RNG seeds —
the K-means is fully deterministic given linear-interpolation seeds).

Note on minimum-history budget: ATR(10) + training_data_period(100)
means we need 109 bars before K-means can run on the last bar.
Most fixtures are 180+ bars long.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from saadhana_filter.indicators.adaptive_supertrend import (
    compute_adaptive_supertrend,
)


def _ohlcv_from_close(
    close: np.ndarray, *, true_range_pct: float = 0.005
) -> pd.DataFrame:
    """Wrap a close path with proportional ±true_range_pct high/low
    offsets so the ATR computation has a non-zero true range."""
    high = close * (1.0 + true_range_pct)
    low = close * (1.0 - true_range_pct)
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
        }
    )


def _build_calm_then_volatile() -> pd.DataFrame:
    """200 bars calm (σ ≈ 0.3), then 200 bars volatile (σ ≈ 3.0)."""
    rng = np.random.default_rng(20260503)
    calm = 100.0 + rng.normal(0, 0.3, size=200)
    vol_steps = rng.normal(0, 3.0, size=200)
    volatile = calm[-1] + np.cumsum(vol_steps)
    close = np.concatenate([calm, volatile])
    high = close + np.abs(rng.normal(0, 1.0, size=len(close)))
    low = close - np.abs(rng.normal(0, 1.0, size=len(close)))
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
        }
    )


# ───────────────────────────────────────────────────────────────────
# 1. Insufficient history
# ───────────────────────────────────────────────────────────────────
def test_insufficient_history_returns_reason() -> None:
    df = _ohlcv_from_close(np.linspace(100.0, 130.0, 80))  # < 109
    result = compute_adaptive_supertrend(df, on_bar=79)
    assert result["qualified"] is False
    assert result["reason"] == "insufficient_history"
    assert result["active_cluster"] == "init"


# ───────────────────────────────────────────────────────────────────
# 2. Calm-then-volatile cluster migrates (assigned centroid grows)
# ───────────────────────────────────────────────────────────────────
def test_calm_then_volatile_assigned_centroid_migrates() -> None:
    df = _build_calm_then_volatile()

    # Late in the calm phase, assigned centroid should be small;
    # late in the volatile phase, it should be much larger.
    calm_result = compute_adaptive_supertrend(df, on_bar=199)
    vol_result = compute_adaptive_supertrend(df, on_bar=399)

    assert calm_result["active_cluster"] in ("low", "mid", "high")
    assert vol_result["active_cluster"] in ("low", "mid", "high")
    # The volatility regime is what drives the centroid magnitude.
    assert vol_result["atr_value"] > calm_result["atr_value"]
    assert vol_result["assigned_centroid"] > calm_result["assigned_centroid"]


# ───────────────────────────────────────────────────────────────────
# 3. Uptrend onset produces a bullish flip
#    (down → flat → up gives a real bear→bull transition observable
#    after the K-means starts at bar 108)
# ───────────────────────────────────────────────────────────────────
def test_uptrend_onset_produces_bullish_flip() -> None:
    down = np.linspace(110.0, 95.0, 80)
    flat = np.full(40, 95.0)
    up = np.linspace(95.0, 130.0, 60)
    close = np.concatenate([down, flat, up])  # 180 bars
    df = _ohlcv_from_close(close)

    saw_flip = False
    for bar in range(109, len(df)):
        result = compute_adaptive_supertrend(
            df, on_bar=bar, signal_freshness_bars=5, confirm_signals=False
        )
        if result["qualified"] and result["direction"] == +1:
            saw_flip = True
            break
    assert saw_flip, "expected at least one bullish flip in down→flat→up sequence"


# ───────────────────────────────────────────────────────────────────
# 4. Downtrend mirror — never produces qualified=True
# ───────────────────────────────────────────────────────────────────
def test_downtrend_does_not_qualify() -> None:
    up = np.linspace(95.0, 110.0, 80)
    flat = np.full(40, 110.0)
    down = np.linspace(110.0, 80.0, 60)
    close = np.concatenate([up, flat, down])  # 180 bars
    df = _ohlcv_from_close(close)

    qualified_count = 0
    for bar in range(109, len(df)):
        result = compute_adaptive_supertrend(
            df, on_bar=bar, signal_freshness_bars=5, confirm_signals=False
        )
        if result["qualified"]:
            qualified_count += 1
    assert qualified_count == 0


# ───────────────────────────────────────────────────────────────────
# 5. confirm_signals=True lags the flip by exactly one bar
# ───────────────────────────────────────────────────────────────────
def test_confirm_signals_lags_one_bar() -> None:
    """Pine non-repainting convention: with confirm_signals=True,
    a bullish flip detected at bar j is reported as qualified only
    on bar j+1 (the next confirmed close)."""
    down = np.linspace(110.0, 95.0, 80)
    flat = np.full(40, 95.0)
    up = np.linspace(95.0, 130.0, 100)
    close = np.concatenate([down, flat, up])  # 220 bars
    df = _ohlcv_from_close(close)

    # Find the first bar where confirm=False reports qualified.
    flip_at = None
    for bar in range(109, len(df)):
        r = compute_adaptive_supertrend(
            df, on_bar=bar, signal_freshness_bars=1, confirm_signals=False
        )
        if r["qualified"]:
            flip_at = bar
            break
    assert flip_at is not None, "fixture must produce at least one flip"

    # On the same bar with confirm=True + freshness=1, qualified should
    # be False — the flip happened at flip_at itself, but confirm mode
    # only sees flips at flip_at - 1 (with freshness=1).
    r_confirm_at_flip = compute_adaptive_supertrend(
        df, on_bar=flip_at, signal_freshness_bars=1, confirm_signals=True
    )
    assert r_confirm_at_flip["qualified"] is False

    # On flip_at + 1 with confirm=True + freshness=2, qualified should
    # be True — the flip at flip_at is now within the confirmation
    # window (bar j = flip_at + 1 confirms the flip at j-1 = flip_at).
    r_confirm_after = compute_adaptive_supertrend(
        df, on_bar=flip_at + 1, signal_freshness_bars=2, confirm_signals=True
    )
    assert r_confirm_after["qualified"] is True
    assert r_confirm_after["flip_bar"] == flip_at


# ───────────────────────────────────────────────────────────────────
# 6. Determinism — no RNG, no seed needed
# ───────────────────────────────────────────────────────────────────
def test_determinism_no_seed() -> None:
    df = _build_calm_then_volatile()
    a = compute_adaptive_supertrend(df, on_bar=399)
    b = compute_adaptive_supertrend(df, on_bar=399)
    assert a == b, "linear-interp seeds + Lloyd's iteration must be deterministic"


# ───────────────────────────────────────────────────────────────────
# 7. factor parameter does not affect the K-means centroid
#    (centroid math is independent of the SuperTrend factor)
# ───────────────────────────────────────────────────────────────────
def test_factor_does_not_affect_centroid() -> None:
    close = np.concatenate(
        [np.full(80, 100.0), np.linspace(100.0, 130.0, 100)]
    )  # 180 bars
    df = _ohlcv_from_close(close)
    r1 = compute_adaptive_supertrend(df, on_bar=179, factor=3.0)
    r2 = compute_adaptive_supertrend(df, on_bar=179, factor=6.0)
    assert r1["assigned_centroid"] == r2["assigned_centroid"]
    # And the cluster label is also factor-independent.
    assert r1["active_cluster"] == r2["active_cluster"]


# ───────────────────────────────────────────────────────────────────
# Extras — direction sign convention + linear-interp seeds smoke test
# ───────────────────────────────────────────────────────────────────
def test_direction_uses_plus_one_for_uptrend() -> None:
    """Sanity-check the sign-convention inversion: a sustained
    uptrend should produce direction == +1, NOT -1 (the Pine sign)."""
    close = np.concatenate(
        [np.full(120, 100.0), np.linspace(100.0, 140.0, 80)]
    )  # 200 bars
    df = _ohlcv_from_close(close)
    # Walk forward; once price has cleared the upper band, direction
    # must be +1 in our convention.
    for bar in range(180, len(df)):
        r = compute_adaptive_supertrend(df, on_bar=bar, confirm_signals=False)
        if r["direction"] == +1:
            return  # found
    raise AssertionError("expected direction == +1 somewhere in the rising tail")


def test_linear_interp_seeds_produce_sorted_centroids() -> None:
    """The internal _kmeans_3_linear_seeds always returns centroids
    sorted ascending — caller relies on this for the (low, mid, high)
    label mapping."""
    from saadhana_filter.indicators.adaptive_supertrend import (
        _kmeans_3_linear_seeds,
    )

    rng = np.random.default_rng(20260503)
    window = np.abs(rng.normal(0, 1.0, size=100)) + 0.01  # all positive
    centroids = _kmeans_3_linear_seeds(window)
    assert centroids.shape == (3,)
    assert centroids[0] <= centroids[1] <= centroids[2]
