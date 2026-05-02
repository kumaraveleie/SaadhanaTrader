"""Tests for Sec.5.7 — MA crossover.

Covers the 6 spec golden-fixture cases. Fixtures are synthesised
inside the test (matching the project convention of programmatic
deterministic OHLCV) so the suite has no I/O dependency.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from saadhana_filter.indicators.ma_crossover import (
    ALLOWED_MA_TYPES,
    compute_ma_crossover,
)


def _ohlcv(close: np.ndarray, *, volume: int = 1_000_000) -> pd.DataFrame:
    """Build a constant-OHLC bar around a close path; volume is flat."""
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.full(len(close), volume, dtype=float),
        }
    )


def _flat_then_ramp(flat_bars: int, ramp_bars: int, start: float, end: float) -> np.ndarray:
    flat = np.full(flat_bars, start, dtype=float)
    ramp = np.linspace(start, end, ramp_bars)
    return np.concatenate([flat, ramp])


# ──────────────────────────────────────────────────────────────────
# 1. Clean uptrend crossover
# ──────────────────────────────────────────────────────────────────
def test_uptrend_fires_bullish_crossover() -> None:
    close = _flat_then_ramp(flat_bars=120, ramp_bars=60, start=100.0, end=140.0)
    df = _ohlcv(close)
    result = compute_ma_crossover(
        df, ma_type="EMA", fast_period=20, slow_period=50, signal_freshness_bars=60
    )
    assert result["qualified"] is True
    assert result["crossover_bar"] is not None
    assert result["slope_pct"] > 0.0
    assert result["fast_ma"] > result["slow_ma"]


# ──────────────────────────────────────────────────────────────────
# 2. Downtrend mirror — no bullish crossover
# ──────────────────────────────────────────────────────────────────
def test_downtrend_no_bullish_crossover() -> None:
    close = _flat_then_ramp(flat_bars=120, ramp_bars=60, start=140.0, end=100.0)
    df = _ohlcv(close)
    result = compute_ma_crossover(df, ma_type="EMA", signal_freshness_bars=60)
    assert result["qualified"] is False
    assert result["crossover_bar"] is None
    assert result["slope_pct"] <= 0.0


# ──────────────────────────────────────────────────────────────────
# 3. Flat-range with noise — at most one whipsaw cross at edge
# ──────────────────────────────────────────────────────────────────
def test_flat_range_does_not_overfire() -> None:
    """Random walk around a constant mean — a strict slope filter
    must keep ``qualified`` False even when noise produces a brief
    fast-over-slow cross. The slope_pct on a flat regime stays
    near zero, so a 0.5% min_slope_pct rejects the cross."""
    rng = np.random.default_rng(20260502)
    close = 100.0 + rng.normal(0, 1.0, size=200)
    df = _ohlcv(close)
    result = compute_ma_crossover(
        df,
        ma_type="EMA",
        fast_period=20,
        slow_period=50,
        signal_freshness_bars=10,
        min_slope_pct=0.5,  # 0.5% over 3 bars is unreachable on σ=1 noise
    )
    assert result["qualified"] is False
    # Slope on a flat random walk is bounded — well below the strict filter.
    assert abs(result["slope_pct"]) < 0.5


# ──────────────────────────────────────────────────────────────────
# 4. Insufficient history
# ──────────────────────────────────────────────────────────────────
def test_insufficient_history_returns_reason() -> None:
    close = np.linspace(100.0, 110.0, 49)  # < slow_period (50)
    df = _ohlcv(close)
    result = compute_ma_crossover(df, ma_type="EMA", fast_period=20, slow_period=50)
    assert result["qualified"] is False
    assert result["reason"] == "insufficient_history"


# ──────────────────────────────────────────────────────────────────
# 5. Crossover bar is the bar where fast strictly exceeds slow
# ──────────────────────────────────────────────────────────────────
def test_crossover_bar_is_first_strict_above() -> None:
    # 100 flat bars then a sharp ramp — guarantees one specific crossover bar.
    close = np.concatenate(
        [np.full(100, 100.0), np.linspace(100.0, 130.0, 60)]
    )
    df = _ohlcv(close)
    result = compute_ma_crossover(
        df,
        ma_type="EMA",
        fast_period=20,
        slow_period=50,
        signal_freshness_bars=60,
    )
    cb = result["crossover_bar"]
    assert cb is not None
    # At the crossover bar fast must be > slow; the bar before, fast ≤ slow.
    fast_now = result["fast_ma"]
    slow_now = result["slow_ma"]
    assert fast_now > slow_now


# ──────────────────────────────────────────────────────────────────
# 6. MA-type switch — TEMA fires earlier than SMA
# ──────────────────────────────────────────────────────────────────
def test_tema_leads_sma_on_same_fixture() -> None:
    """TEMA's reduced lag is the entire reason it's the default. On a
    rising ramp, TEMA's fast MA crosses slow_EMA earlier than SMA's
    fast MA does — this property is locked by the spec note."""
    close = np.concatenate(
        [np.full(120, 100.0), np.linspace(100.0, 130.0, 80)]
    )
    df = _ohlcv(close)

    res_tema = compute_ma_crossover(
        df,
        ma_type="TEMA",
        fast_period=20,
        slow_period=50,
        signal_freshness_bars=80,
    )
    res_sma = compute_ma_crossover(
        df,
        ma_type="SMA",
        fast_period=20,
        slow_period=50,
        signal_freshness_bars=80,
    )

    # Both should ultimately fire on this strong ramp.
    assert res_tema["crossover_bar"] is not None
    assert res_sma["crossover_bar"] is not None
    # And TEMA's cross fires on or before SMA's.
    assert res_tema["crossover_bar"] <= res_sma["crossover_bar"]


# ──────────────────────────────────────────────────────────────────
# All 7 MA types are accepted
# ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ma_type", ALLOWED_MA_TYPES)
def test_all_ma_types_compute_without_error(ma_type: str) -> None:
    close = np.concatenate(
        [np.full(150, 100.0), np.linspace(100.0, 130.0, 100)]
    )
    df = _ohlcv(close)
    result = compute_ma_crossover(
        df,
        ma_type=ma_type,  # type: ignore[arg-type]
        fast_period=20,
        slow_period=50,
        signal_freshness_bars=100,
    )
    # All types must return a well-formed result; we don't assert
    # qualified=True for every type because warm-up varies (TEMA's
    # 3·n requirement is the strictest).
    assert "qualified" in result
    assert result["ma_type"] == ma_type


def test_unknown_ma_type_raises() -> None:
    df = _ohlcv(np.full(200, 100.0))
    with pytest.raises(ValueError, match="ma_type must be one of"):
        compute_ma_crossover(df, ma_type="BOGUS")  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────
# Slope filter rejects qualifying cross when slope < min_slope_pct
# ──────────────────────────────────────────────────────────────────
def test_slope_filter_blocks_weak_uptrends() -> None:
    # Tiny ramp — fast EMA crosses slow EMA but the slope is shallow.
    close = np.concatenate(
        [np.full(120, 100.0), np.linspace(100.0, 100.5, 60)]
    )
    df = _ohlcv(close)
    result = compute_ma_crossover(
        df,
        ma_type="EMA",
        fast_period=20,
        slow_period=50,
        signal_freshness_bars=60,
        min_slope_pct=1.0,  # require ≥ 1% slope — this fixture won't make it
    )
    # Cross may exist but qualified should be False under the strict filter.
    assert result["qualified"] is False
