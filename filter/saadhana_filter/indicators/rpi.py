"""Sec.5.5a Relative Price Index (RPI) calculator — Track 2 W1.2.

Mansfield-style relative-strength measure: stock cumulative return /
benchmark cumulative return over a lookback window. Per Sec.0.7.5,
this is a class-4 momentum signal — orthogonal to the class-1 trend
signals that Triple confluence is built from.

NOT to be confused with RSI (Relative Strength Index, a self-
referential momentum oscillator). RPI is cross-symbol; RSI is on the
symbol's own price.

Default lookback = 63 bars (~3 calendar months on daily). Mansfield-
normalised variant returns the percentage outperformance over
benchmark, easier to read at a glance:
    mansfield_rpi = ((stock_ratio / benchmark_ratio) - 1) * 100

Cross-references:
- Sec.5.5b builds spurt + crossover signals on top of RPI
- Sec.14a row ``rpi_spurt`` is the cohort that consumes both
- Benchmark fallback path mirrors scripts/bull_month_replay.py — when
  ``^NSEI`` isn't available, use a universe-mean proxy
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_LOOKBACK = 63  # ~3 months on daily bars
DEFAULT_MIN_INIT_BARS = 100


def compute_rpi(
    stock: pd.Series,
    benchmark: pd.Series,
    *,
    lookback: int = DEFAULT_LOOKBACK,
    mansfield: bool = False,
    min_init_bars: int = DEFAULT_MIN_INIT_BARS,
) -> pd.Series:
    """Return per-bar RPI series indexed on the stock's date index.

    Formula:
        ratio_t = stock_t / stock_{t-lookback}
        ratio_b = benchmark_t / benchmark_{t-lookback}
        rpi_t   = ratio_t / ratio_b
        mansfield_rpi_t = (rpi_t - 1) * 100   # if mansfield=True

    NaN for warm-up bars (until ``min_init_bars`` accumulated and the
    benchmark reference value is finite + non-zero).

    The benchmark series is forward-aligned to the stock's index so
    the calculation handles slight calendar mismatches (e.g.,
    benchmark missing one trading day) by carrying the previous
    value. Stock dates with no benchmark reading anywhere in the
    forward-fill window resolve to NaN.
    """
    if lookback <= 0:
        raise ValueError(f"lookback must be positive, got {lookback}")
    if len(stock) < min_init_bars:
        return pd.Series(np.nan, index=stock.index, dtype=float)

    # Align benchmark to stock dates with forward-fill (last known
    # benchmark close on or before each stock date).
    bench = benchmark.reindex(stock.index, method="ffill")

    stock_ratio = stock / stock.shift(lookback)
    bench_ratio = bench / bench.shift(lookback)

    # Suppress divide warnings — degenerate cells become NaN.
    with np.errstate(divide="ignore", invalid="ignore"):
        rpi = stock_ratio / bench_ratio.replace(0.0, np.nan)

    if mansfield:
        rpi = (rpi - 1.0) * 100.0
    rpi.name = "rpi"
    return rpi


def latest_rpi(
    stock: pd.Series,
    benchmark: pd.Series,
    *,
    lookback: int = DEFAULT_LOOKBACK,
    mansfield: bool = False,
    min_init_bars: int = DEFAULT_MIN_INIT_BARS,
) -> float | None:
    """Return RPI at the last bar of ``stock``, or ``None`` if not
    yet defined (warm-up or missing benchmark reading)."""
    series = compute_rpi(
        stock,
        benchmark,
        lookback=lookback,
        mansfield=mansfield,
        min_init_bars=min_init_bars,
    )
    if series.empty:
        return None
    val = series.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


__all__ = [
    "DEFAULT_LOOKBACK",
    "DEFAULT_MIN_INIT_BARS",
    "compute_rpi",
    "latest_rpi",
]
