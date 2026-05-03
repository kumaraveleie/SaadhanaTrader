"""Tests for Sec.5.5a RPI calculator.

Mansfield-style relative strength: ratio of stock cumulative return
to benchmark cumulative return over a lookback window. Per Sec.0.7.5
this is a class-4 momentum signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from saadhana_filter.indicators.rpi import (
    DEFAULT_LOOKBACK,
    compute_rpi,
    latest_rpi,
)


def _series(values, start="2024-01-01"):
    return pd.Series(
        values,
        index=pd.date_range(start, periods=len(values), freq="B"),
        dtype=float,
    )


# ──────────────────────────────────────────────────────────────────
# Formula correctness
# ──────────────────────────────────────────────────────────────────
def test_rpi_equal_returns_yields_one():
    """Stock and benchmark with identical % returns → RPI = 1.0."""
    stock = _series(np.linspace(100.0, 120.0, 200))
    bench = _series(np.linspace(50.0, 60.0, 200))  # both rise 20%
    rpi = compute_rpi(stock, bench, lookback=63)
    last = float(rpi.iloc[-1])
    assert abs(last - 1.0) < 1e-9


def test_rpi_stock_outperforming_yields_above_one():
    """Stock rises 30%, benchmark rises 10% — over a 63-bar lookback
    window of the linear ramp, stock_ratio ≈ 130/120.5 = 1.079 and
    bench_ratio ≈ 110/106.83 = 1.030, so RPI ≈ 1.048."""
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench = _series(np.linspace(100.0, 110.0, 200))
    rpi = compute_rpi(stock, bench, lookback=63)
    last = float(rpi.iloc[-1])
    assert last > 1.0  # stock IS outperforming
    assert last < 1.10  # bounded above by the analytic ~1.048
    assert abs(last - 1.048) < 0.01  # tight check on expected value


def test_rpi_stock_underperforming_yields_below_one():
    """Stock flat, benchmark rises → RPI < 1."""
    stock = _series(np.full(200, 100.0))
    bench = _series(np.linspace(100.0, 130.0, 200))
    rpi = compute_rpi(stock, bench, lookback=63)
    last = float(rpi.iloc[-1])
    assert last < 1.0


def test_mansfield_normalisation():
    """mansfield=True returns (rpi-1)*100 — outperformance %."""
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench = _series(np.linspace(100.0, 110.0, 200))
    rpi_norm = compute_rpi(stock, bench, lookback=63, mansfield=False)
    rpi_man = compute_rpi(stock, bench, lookback=63, mansfield=True)
    last_norm = float(rpi_norm.iloc[-1])
    last_man = float(rpi_man.iloc[-1])
    assert abs(last_man - (last_norm - 1.0) * 100.0) < 1e-9


# ──────────────────────────────────────────────────────────────────
# Warm-up + min_init_bars
# ──────────────────────────────────────────────────────────────────
def test_warmup_bars_are_nan():
    """First ``lookback`` bars of the result are NaN — no reference
    bar yet."""
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench = _series(np.linspace(100.0, 110.0, 200))
    rpi = compute_rpi(stock, bench, lookback=63)
    # Bars 0 through 62 should be NaN.
    assert rpi.iloc[:63].isna().all()
    # Bar 63 should be the first finite value.
    assert not pd.isna(rpi.iloc[63])


def test_short_history_returns_all_nan():
    """Series shorter than ``min_init_bars`` returns all-NaN."""
    stock = _series(np.linspace(100.0, 110.0, 50))
    bench = _series(np.linspace(100.0, 105.0, 50))
    rpi = compute_rpi(stock, bench, lookback=63, min_init_bars=100)
    assert rpi.isna().all()


# ──────────────────────────────────────────────────────────────────
# Benchmark alignment
# ──────────────────────────────────────────────────────────────────
def test_benchmark_with_calendar_gaps_forward_fills():
    """When the benchmark misses a trading day, the alignment uses
    the most recent prior benchmark value. Test by dropping every 7th
    bar from bench (offset by 1 so bench[0] is preserved — otherwise
    the lookback would shift to the second-bar reference and produce
    a one-bar NaN at the first RPI bar)."""
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench_full = _series(np.linspace(100.0, 110.0, 200))
    # Drop bars at indices 1, 8, 15, … keep bench[0] intact.
    drop_idx = np.arange(1, 200, 7)
    bench = bench_full.drop(bench_full.index[drop_idx])
    rpi = compute_rpi(stock, bench, lookback=63)
    # Forward-filled alignment → no NaN values in the post-warmup range.
    assert not rpi.iloc[63:].isna().any()


def test_zero_benchmark_returns_nan():
    """If benchmark crosses through zero, the corresponding RPI bar
    is NaN (division by zero)."""
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench = pd.Series(
        [100.0] * 60 + [0.0] * 80 + [100.0] * 60,
        index=pd.date_range("2024-01-01", periods=200, freq="B"),
        dtype=float,
    )
    rpi = compute_rpi(stock, bench, lookback=63)
    # At least some bars should be NaN where bench=0.
    assert rpi.isna().any()


# ──────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────
def test_negative_lookback_raises():
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench = _series(np.linspace(100.0, 110.0, 200))
    with pytest.raises(ValueError, match="lookback must be positive"):
        compute_rpi(stock, bench, lookback=0)


def test_default_lookback_constant():
    """Default lookback is 63 bars (~3 months)."""
    assert DEFAULT_LOOKBACK == 63


def test_latest_rpi_returns_none_for_warmup():
    """latest_rpi() returns None when the last bar is in warm-up."""
    stock = _series(np.linspace(100.0, 110.0, 50))  # < min_init_bars
    bench = _series(np.linspace(100.0, 105.0, 50))
    assert latest_rpi(stock, bench, lookback=63) is None


def test_latest_rpi_returns_float_when_defined():
    stock = _series(np.linspace(100.0, 130.0, 200))
    bench = _series(np.linspace(100.0, 110.0, 200))
    val = latest_rpi(stock, bench, lookback=63)
    assert val is not None
    assert isinstance(val, float)
    assert val > 1.0  # stock outperforming
