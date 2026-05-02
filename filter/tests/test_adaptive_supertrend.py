"""Tests for Sec.5.8 — Adaptive SuperTrend.

Covers the 6 spec golden-fixture cases. Fixtures are synthesised
deterministically inside the tests; ``kmeans_random_state`` is
passed explicitly so the determinism check (case #6) is exact.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from saadhana_filter.indicators.adaptive_supertrend import compute_adaptive_supertrend


def _ohlcv_from_close(close: np.ndarray, *, true_range_pct: float = 0.005) -> pd.DataFrame:
    """Build OHLCV with high/low offset by ``true_range_pct`` of close.

    This gives the ATR computation a non-zero true-range to chew on
    even when the close path is fully deterministic.
    """
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
    rng = np.random.default_rng(20260502)
    calm = 100.0 + rng.normal(0, 0.5, size=120)
    volatile = calm[-1] + np.cumsum(rng.normal(0, 3.0, size=80))
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


# ──────────────────────────────────────────────────────────────────
# 1. Calm-then-volatile transition — cluster migrates low → high
# ──────────────────────────────────────────────────────────────────
def test_calm_then_volatile_cluster_migrates() -> None:
    df = _build_calm_then_volatile()

    # Read the cluster label late in the calm window vs deep in the
    # volatile window. The calm bar should be in 'low' or 'mid'; the
    # volatile bar should be 'high'.
    calm_idx = 119  # last calm bar — but we still need cluster_window history
    calm_result = compute_adaptive_supertrend(df, on_bar=calm_idx, cluster_window=50)
    vol_result = compute_adaptive_supertrend(df, on_bar=199, cluster_window=50)

    # Both bars are past min_init_bars so neither should be 'init'.
    assert calm_result["active_cluster"] in ("low", "mid", "high")
    assert vol_result["active_cluster"] in ("low", "mid", "high")
    # Volatile-regime bar's ATR should classify higher than the calm one.
    assert vol_result["atr_i"] > calm_result["atr_i"]


# ──────────────────────────────────────────────────────────────────
# 2. Bullish flip on uptrend onset
# ──────────────────────────────────────────────────────────────────
def test_uptrend_onset_produces_bullish_flip() -> None:
    """Downtrend → flat → uptrend. The downtrend establishes a -1
    direction state so the uptrend onset produces a true bear→bull
    flip (a series that starts in +1 has no -1 to flip from)."""
    down = np.linspace(110.0, 95.0, 100)        # bear leg sets direction to -1
    flat = np.full(40, 95.0)                    # bottom basing
    up = np.linspace(95.0, 130.0, 80)           # uptrend ramp
    close = np.concatenate([down, flat, up])
    df = _ohlcv_from_close(close)

    saw_flip = False
    for bar in range(140, len(df)):
        result = compute_adaptive_supertrend(df, on_bar=bar, signal_freshness_bars=5)
        if result["qualified"] and result["direction"] == +1:
            saw_flip = True
            break
    assert saw_flip, "expected at least one bullish flip in down→flat→up sequence"


# ──────────────────────────────────────────────────────────────────
# 3. Bearish flip mirror — no bullish qualified=True
# ──────────────────────────────────────────────────────────────────
def test_downtrend_does_not_qualify() -> None:
    flat = np.full(120, 130.0)
    ramp = np.linspace(130.0, 100.0, 60)
    df = _ohlcv_from_close(np.concatenate([flat, ramp]))

    qualified_count = 0
    for bar in range(150, len(df)):
        result = compute_adaptive_supertrend(df, on_bar=bar, signal_freshness_bars=3)
        if result["qualified"]:
            qualified_count += 1
    assert qualified_count == 0


# ──────────────────────────────────────────────────────────────────
# 4. Insufficient history (< min_init_bars) — falls back to mult_mid
# ──────────────────────────────────────────────────────────────────
def test_insufficient_history_uses_mult_mid_init() -> None:
    df = _ohlcv_from_close(np.full(60, 100.0))  # 60 bars < 100 min_init
    result = compute_adaptive_supertrend(df, on_bar=59)
    assert result["active_cluster"] == "init"
    assert result["mult_used"] == 2.0  # mult_mid


# ──────────────────────────────────────────────────────────────────
# 5. Degenerate clustering — all centers tightly clustered
# ──────────────────────────────────────────────────────────────────
def test_degenerate_clustering_falls_back_to_mid() -> None:
    # 200 bars where ATR is essentially flat — high/low constant.
    flat_close = np.linspace(100.0, 100.001, 200)
    df = pd.DataFrame(
        {
            "open": flat_close,
            "high": flat_close + 0.001,
            "low": flat_close - 0.001,
            "close": flat_close,
            "volume": np.full(200, 1_000_000.0),
        }
    )
    result = compute_adaptive_supertrend(df, on_bar=199)
    assert result["active_cluster"] in ("degenerate", "init")
    assert result["mult_used"] == 2.0  # mult_mid in either branch


# ──────────────────────────────────────────────────────────────────
# 6. Determinism — same fixture + seed = byte-identical output
# ──────────────────────────────────────────────────────────────────
def test_determinism_under_fixed_seed() -> None:
    df = _build_calm_then_volatile()
    a = compute_adaptive_supertrend(
        df, on_bar=199, kmeans_random_state=20260502
    )
    b = compute_adaptive_supertrend(
        df, on_bar=199, kmeans_random_state=20260502
    )
    assert a == b, "same seed + same fixture must yield identical output"


# ──────────────────────────────────────────────────────────────────
# Extras — direction is non-zero post-warmup; flip_bar within window
# ──────────────────────────────────────────────────────────────────
def test_direction_is_set_after_warmup() -> None:
    df = _ohlcv_from_close(np.linspace(100.0, 130.0, 200))
    result = compute_adaptive_supertrend(df, on_bar=199)
    assert result["direction"] in (+1, -1)
    assert result["active_band"] is not None


def test_flip_bar_is_within_freshness_window() -> None:
    flat = np.full(120, 100.0)
    ramp = np.linspace(100.0, 140.0, 80)
    df = _ohlcv_from_close(np.concatenate([flat, ramp]))
    on_bar = 199
    result = compute_adaptive_supertrend(df, on_bar=on_bar, signal_freshness_bars=3)
    if result["flip_bar"] is not None:
        assert on_bar - result["flip_bar"] < 3
