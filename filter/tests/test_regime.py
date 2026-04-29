"""§12 — market regime tests."""

from __future__ import annotations

import numpy as np

from saadhana_filter.signals.regime import Regime, latest_regime, market_regime
from tests.builders import geometric_close, make_ohlcv


def test_clean_uptrend_is_risk_on() -> None:
    df = make_ohlcv(geometric_close(15_000.0, 0.001, 280))
    assert latest_regime(df) == Regime.RISK_ON


def test_clean_downtrend_is_risk_off() -> None:
    df = make_ohlcv(geometric_close(20_000.0, -0.001, 280))
    assert latest_regime(df) == Regime.RISK_OFF


def test_chop_between_dmas_is_caution() -> None:
    # Long uptrend so close stays above the 200-DMA, then 80 flat bars so
    # the 50-DMA stops rising. Result: close > 200-DMA (not Risk_Off),
    # but 50-DMA-rising leg fails so it isn't Risk_On either.
    n = 280
    up = geometric_close(15_000.0, 0.0015, n - 80)
    flat = np.full(80, up[-1])
    df = make_ohlcv(np.concatenate([up, flat]))
    assert latest_regime(df) == Regime.CAUTION


def test_50dma_falling_is_not_risk_on() -> None:
    # Decelerating uptrend so the 50-DMA flattens / falls on the last bar
    n = 280
    rates = np.concatenate([np.full(n - 60, 0.0015), np.full(60, -0.0008)])
    close = 15_000.0 * np.cumprod(1 + rates)
    df = make_ohlcv(close)
    # close is still > 200-DMA and may or may not be > 50-DMA, but the
    # 50-DMA-rising leg fails — so it cannot be RISK_ON.
    assert latest_regime(df) != Regime.RISK_ON


def test_short_history_falls_back_to_caution() -> None:
    # < 200 bars → 200-DMA undefined → conservative default
    df = make_ohlcv(geometric_close(15_000.0, 0.001, 50))
    states = market_regime(df)
    # Bars without 200-DMA must not resolve RISK_ON or RISK_OFF
    assert (states == Regime.CAUTION).all()


def test_regime_series_aligned_to_index() -> None:
    df = make_ohlcv(geometric_close(15_000.0, 0.001, 280))
    states = market_regime(df)
    assert len(states) == len(df)
    assert (states.index == df.index).all()
