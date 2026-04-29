"""Shared fixtures for §5 condition tests.

Each fixture returns a deterministic OHLCV ``DataFrame`` (index = business
days, columns = ``open, high, low, close, volume``). Fixed numpy seeds make
every byte reproducible across machines so golden-fixture tests stay green.

Four base fixtures cover the canonical regimes:

- ``uptrend_fixture`` — smooth Stage-2 uptrend; engineered so all 13
  §5 conditions resolve **True** on the last closed bar
- ``downtrend_fixture`` — Stage 4 decline; conditions resolve **False**
- ``sideways_fixture`` — flat range, BB compression
- ``breakout_fixture`` — multi-month base then a fresh-breakout candle
  in the last 3 bars (drives the OR-clauses in §5.5)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# 320 trading days ≈ 64 weeks — enough for 30W SMA, 200-EMA, 52w lookbacks
N_BARS = 320
START = "2024-01-02"


def _bdays(n: int = N_BARS, start: str = START) -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def _ohlcv_from_close(
    close: np.ndarray,
    *,
    intrabar_pct: np.ndarray,
    volume: np.ndarray,
    index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Build a plausible OHLCV frame from a close path.

    ``intrabar_pct`` (per-bar fractional range, e.g. 0.012 → 1.2% range) is
    split symmetrically around the midpoint between today's open and close.
    Open is yesterday's close (gapless); the very first open is set to
    today's close − a small drift so day 0 has a real range.
    """
    n = len(close)
    open_ = np.empty(n)
    open_[0] = close[0] * 0.999
    open_[1:] = close[:-1]
    half = (intrabar_pct * close) / 2.0
    high = np.maximum(open_, close) + half
    low = np.minimum(open_, close) - half
    # ensure invariants
    high = np.maximum.reduce([high, open_, close])
    low = np.minimum.reduce([low, open_, close])
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume.astype("int64"),
        },
        index=index,
    )


# ──────────────────────────────────────────────────────────────────────────
# Uptrend — designed to satisfy all 13 §5 conditions on the last bar
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def uptrend_fixture() -> pd.DataFrame:
    rng = np.random.default_rng(seed=20260429)
    idx = _bdays()
    n = len(idx)

    # Steady drift ≈ 0.18% per bar with Gaussian noise; clipped so we never
    # have a single explosive bar that contaminates BB / RVOL averages.
    log_rets = rng.normal(loc=0.0018, scale=0.0085, size=n)
    log_rets = np.clip(log_rets, -0.025, 0.030)

    # Last 8 weekly groups (~40 daily bars) lean positive to enforce HH/HL.
    log_rets[-40:] = np.clip(log_rets[-40:] + 0.0015, -0.020, 0.030)

    # Final bar: small up-day with mild volume spike so RSI stays in 50–70
    # and the bar is an up-bar without exploding the 5-EMA past the rest.
    log_rets[-1] = 0.006

    close = 1000.0 * np.exp(np.cumsum(log_rets))

    # Volume baseline 1.0M with regular spikes; planted institutional buy
    # bars in the last 5 sessions (RVOL ≥ 2.5x on an up-day).
    base_vol = rng.normal(loc=1_000_000, scale=120_000, size=n).clip(min=300_000)
    # Sprinkle ~6 institutional buy bars across the last 30 sessions so
    # inst_flow_30d > 0 with margin.
    inst_buy_offsets = [-3, -7, -12, -16, -22, -28]
    for off in inst_buy_offsets:
        base_vol[off] *= 2.7
    # And one heavy-buy bar inside the last-5-day window.
    base_vol[-2] *= 1.8

    intrabar = np.full(n, 0.012)
    df = _ohlcv_from_close(close, intrabar_pct=intrabar, volume=base_vol, index=idx)
    return df


# ──────────────────────────────────────────────────────────────────────────
# Downtrend — Stage 4 / falling 30W SMA / momentum negative
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def downtrend_fixture() -> pd.DataFrame:
    rng = np.random.default_rng(seed=20260430)
    idx = _bdays()
    n = len(idx)
    log_rets = rng.normal(loc=-0.0018, scale=0.0090, size=n)
    log_rets = np.clip(log_rets, -0.030, 0.025)
    log_rets[-1] = -0.008  # last bar down
    close = 1500.0 * np.exp(np.cumsum(log_rets))
    base_vol = rng.normal(loc=900_000, scale=100_000, size=n).clip(min=300_000)
    # Plant institutional SELL bars in the last 30 sessions.
    for off in [-2, -8, -15, -21, -27]:
        base_vol[off] *= 2.6  # high-volume down bars → distribution
    intrabar = np.full(n, 0.014)
    return _ohlcv_from_close(close, intrabar_pct=intrabar, volume=base_vol, index=idx)


# ──────────────────────────────────────────────────────────────────────────
# Sideways — flat, BB compression, conditions mostly false
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def sideways_fixture() -> pd.DataFrame:
    rng = np.random.default_rng(seed=20260501)
    idx = _bdays()
    n = len(idx)
    # Mean-reverting around 1200 with very low vol → tight BB
    log_rets = rng.normal(loc=0.0, scale=0.0035, size=n)
    log_rets = np.clip(log_rets, -0.010, 0.010)
    close = 1200.0 * np.exp(np.cumsum(log_rets))
    # Pull back toward 1200 to keep range tight
    close = 1200.0 + (close - 1200.0) * 0.4
    base_vol = rng.normal(loc=700_000, scale=60_000, size=n).clip(min=200_000)
    intrabar = np.full(n, 0.008)
    return _ohlcv_from_close(close, intrabar_pct=intrabar, volume=base_vol, index=idx)


# ──────────────────────────────────────────────────────────────────────────
# Breakout — long base, then a fresh breakout in the last 3 bars
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def breakout_fixture() -> pd.DataFrame:
    rng = np.random.default_rng(seed=20260502)
    idx = _bdays()
    n = len(idx)

    # First (n-3) bars: tight range around 800; last 3: aggressive breakout
    base_n = n - 3
    base_rets = rng.normal(loc=0.0, scale=0.0040, size=base_n)
    base_rets = np.clip(base_rets, -0.012, 0.012)
    base_close = 800.0 * np.exp(np.cumsum(base_rets))
    base_close = 800.0 + (base_close - 800.0) * 0.3  # tighten

    # Breakout pop on heavy volume; each of last 3 bars +3% to +4%
    pop = base_close[-1] * np.array([1.034, 1.072, 1.110])
    close = np.concatenate([base_close, pop])

    base_vol = rng.normal(loc=600_000, scale=70_000, size=n).clip(min=200_000)
    base_vol[-3:] *= 3.2  # institutional breakout volume

    intrabar = np.concatenate([np.full(base_n, 0.008), np.full(3, 0.022)])
    return _ohlcv_from_close(close, intrabar_pct=intrabar, volume=base_vol, index=idx)
