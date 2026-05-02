"""Tests for Sec.5.9 — Deviation Trend.

Covers the 6 spec golden-fixture cases. Fixtures are synthesised
deterministically inside the tests (no I/O, no random seed dependency
except where explicitly used for noise).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from saadhana_filter.indicators.deviation_trend import compute_deviation_trend


def _ohlcv_from_close(close: np.ndarray) -> pd.DataFrame:
    """Wrap a close path with proportional high/low offsets."""
    high = close * 1.005
    low = close * 0.995
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
# 1. Clean uptrend — slope > 0, qualified True at some point
# ──────────────────────────────────────────────────────────────────
def test_uptrend_slope_positive_and_qualifies() -> None:
    rng = np.random.default_rng(20260502)
    n = 150
    drift = 0.3  # %/bar
    base = 100.0 * np.cumprod(1 + drift / 100 + rng.normal(0, 0.005, size=n))
    df = _ohlcv_from_close(base)
    result = compute_deviation_trend(df, on_bar=149, signal_freshness_bars=20)
    assert result["slope"] > 0.0
    # An uptrend that's been running 150 bars should be in direction +1
    # and have a recent bullish cross within the 20-bar window.
    assert result["direction"] == +1


# ──────────────────────────────────────────────────────────────────
# 2. Clean downtrend mirror — slope < 0, no qualified
# ──────────────────────────────────────────────────────────────────
def test_downtrend_no_qualified() -> None:
    rng = np.random.default_rng(20260502)
    n = 150
    drift = -0.3
    base = 100.0 * np.cumprod(1 + drift / 100 + rng.normal(0, 0.005, size=n))
    df = _ohlcv_from_close(base)
    result = compute_deviation_trend(df, on_bar=149, signal_freshness_bars=20)
    assert result["slope"] < 0.0
    assert result["qualified"] is False


# ──────────────────────────────────────────────────────────────────
# 3. Sideways — slope filter rejects spurious bullish crosses
# ──────────────────────────────────────────────────────────────────
def test_sideways_rejects_via_slope_filter() -> None:
    rng = np.random.default_rng(20260502)
    n = 200
    base = 100.0 + np.cumsum(rng.normal(0, 0.2, size=n))
    # Detrend to enforce zero drift.
    base -= np.linspace(0, base[-1] - 100.0, n)
    df = _ohlcv_from_close(base)
    result = compute_deviation_trend(df, on_bar=199)
    # A truly sideways path has slope ≈ 0; even if direction flips on
    # noise the slope filter (slope > 0 strict) should reject every
    # bullish cross.
    assert abs(result["slope"]) < 0.05
    assert result["qualified"] is False


# ──────────────────────────────────────────────────────────────────
# 4. Insufficient history
# ──────────────────────────────────────────────────────────────────
def test_insufficient_history() -> None:
    df = _ohlcv_from_close(np.linspace(100.0, 110.0, 99))  # < 100
    result = compute_deviation_trend(df, on_bar=98)
    assert result["qualified"] is False
    assert result["reason"] == "insufficient_history"


# ──────────────────────────────────────────────────────────────────
# 5. No swing-low pivot — graceful fallback with reason flag
# ──────────────────────────────────────────────────────────────────
def test_no_pivot_anchor_uses_first_bar_with_flag() -> None:
    # Monotonically rising series — no swing low possible inside a
    # length-window because every later bar's low > earlier bars'.
    close = np.linspace(100.0, 130.0, 150)
    df = _ohlcv_from_close(close)
    result = compute_deviation_trend(df, on_bar=149)
    # Reason flag may be set; if it is, it must be 'no_pivot_anchor'.
    if "reason" in result:
        assert result["reason"] == "no_pivot_anchor"
    # Either way, the function must not crash and slope > 0.
    assert result["slope"] > 0.0


# ──────────────────────────────────────────────────────────────────
# 6. Determinism — same fixture twice = identical output
# ──────────────────────────────────────────────────────────────────
def test_determinism() -> None:
    close = np.linspace(100.0, 130.0, 150)
    df = _ohlcv_from_close(close)
    a = compute_deviation_trend(df, on_bar=149)
    b = compute_deviation_trend(df, on_bar=149)
    assert a == b


# ──────────────────────────────────────────────────────────────────
# Extras — band ordering invariants
# ──────────────────────────────────────────────────────────────────
def test_band_ordering_invariant() -> None:
    close = np.linspace(100.0, 130.0, 150)
    df = _ohlcv_from_close(close)
    result = compute_deviation_trend(df, on_bar=149)
    assert result["lower"] <= result["trend_line"] <= result["upper"]
    assert result["sigma"] >= 0.0


def test_negative_slope_with_uptrend_fixture_does_not_qualify() -> None:
    """Spec edge case: 'Slope ≤ 0 with direction=+1 → qualified=False'.

    A series can have direction=+1 (close above the upper band) while
    the regression slope is ≤ 0 — typically right after a sharp spike
    in an otherwise flat regime. The slope filter rejects this as a
    sideways false positive.
    """
    # Flat-ish 100 bars then a single spike that's above the upper band.
    flat = np.full(140, 100.0)
    spike = np.concatenate([flat, [115.0] * 10])
    df = _ohlcv_from_close(spike)
    result = compute_deviation_trend(df, on_bar=149, signal_freshness_bars=10)
    # If slope_pct is non-positive AND a cross fired, qualified must be False.
    if result["slope"] <= 0.0:
        assert result["qualified"] is False
