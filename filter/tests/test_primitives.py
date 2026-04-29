"""Tests for shared indicator primitives (saadhana_filter.indicators.primitives)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from saadhana_filter.indicators.primitives import (
    atr,
    bollinger_bandwidth,
    ema,
    entry_stop,
    macd,
    rsi,
    rvol,
    sma,
    weekly_resample,
)
from tests.builders import flat_close, geometric_close, linear_close, make_ohlcv


# ──────────────────────────────────────────────────────────────────────────
# EMA / SMA
# ──────────────────────────────────────────────────────────────────────────
class TestEMA:
    def test_constant_series_converges_to_constant(self) -> None:
        s = pd.Series([100.0] * 50)
        out = ema(s, 5)
        assert out.iloc[-1] == pytest.approx(100.0, abs=1e-9)

    def test_responds_to_step_change(self) -> None:
        s = pd.Series([100.0] * 30 + [110.0] * 30)
        out = ema(s, 5)
        # five bars after the step the EMA should have moved most of the way
        assert out.iloc[34] > 105.0

    def test_min_periods_returns_nan_at_start(self) -> None:
        s = pd.Series([100.0, 101.0, 102.0])
        out = ema(s, 5)
        assert out.iloc[:4].isna().all()


class TestSMA:
    def test_simple_average(self) -> None:
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        out = sma(s, 5)
        assert out.iloc[-1] == pytest.approx(3.0)

    def test_min_periods_nan(self) -> None:
        s = pd.Series([1.0, 2.0, 3.0])
        out = sma(s, 5)
        assert out.isna().all()

    def test_rolling_window_recomputes(self) -> None:
        s = pd.Series([10.0] * 5 + [20.0] * 5)
        out = sma(s, 5)
        assert out.iloc[4] == pytest.approx(10.0)
        assert out.iloc[-1] == pytest.approx(20.0)


# ──────────────────────────────────────────────────────────────────────────
# RSI
# ──────────────────────────────────────────────────────────────────────────
class TestRSI:
    def test_all_gains_pegs_at_100(self) -> None:
        s = pd.Series(np.arange(1.0, 101.0))  # strictly increasing
        out = rsi(s, 14)
        assert out.iloc[-1] == pytest.approx(100.0, abs=1e-6)

    def test_all_losses_pegs_at_zero(self) -> None:
        s = pd.Series(np.arange(100.0, 0.0, -1.0))
        out = rsi(s, 14)
        assert out.iloc[-1] == pytest.approx(0.0, abs=1e-6)

    def test_steady_state_around_50(self) -> None:
        # alternating +1 / -1 → average gain == average loss → RSI = 50
        s = pd.Series([100.0 + (-1) ** i for i in range(60)])
        out = rsi(s, 14)
        assert 45.0 < out.iloc[-1] < 55.0


# ──────────────────────────────────────────────────────────────────────────
# MACD
# ──────────────────────────────────────────────────────────────────────────
class TestMACD:
    def test_uptrend_histogram_positive(self) -> None:
        close = pd.Series(geometric_close(100.0, 0.005, 80))
        m = macd(close)
        assert m["hist"].iloc[-1] > 0

    def test_accelerating_decline_histogram_negative(self) -> None:
        # In a *steady* decline MACD and signal both stabilise and the
        # histogram converges to ~0. We need a fresh acceleration so the
        # MACD line outpaces the signal in the negative direction.
        rates = np.concatenate([np.full(40, 0.001), np.full(40, -0.006)])
        close = pd.Series(100.0 * np.cumprod(1 + rates))
        m = macd(close)
        assert m["hist"].iloc[-1] < 0

    def test_columns_present(self) -> None:
        close = pd.Series(np.linspace(100.0, 110.0, 80))
        m = macd(close)
        assert set(m.columns) == {"macd", "signal", "hist"}


# ──────────────────────────────────────────────────────────────────────────
# ATR
# ──────────────────────────────────────────────────────────────────────────
class TestATR:
    def test_constant_bars_atr_decays_to_zero(self) -> None:
        # The day-0 open is set to ``close * 0.999`` to give the first bar a
        # real range; with Wilder smoothing the ATR fades but never reaches
        # exactly zero. After 50 bars it should be deep into the noise.
        df = make_ohlcv([100.0] * 50, intrabar_pct=0.0)
        a = atr(df, 14)
        assert a.iloc[-1] < 1e-2

    def test_widening_range_grows_atr(self) -> None:
        # progressively wider intrabar range → ATR rises monotonically late
        n = 60
        widths = np.linspace(0.005, 0.05, n)
        df = make_ohlcv(np.full(n, 100.0), intrabar_pct=widths)
        a = atr(df, 14)
        assert a.iloc[-1] > a.iloc[20]

    def test_min_periods(self) -> None:
        df = make_ohlcv([100.0, 101.0, 102.0], intrabar_pct=0.01)
        a = atr(df, 14)
        assert a.isna().all()


# ──────────────────────────────────────────────────────────────────────────
# Bollinger Bandwidth
# ──────────────────────────────────────────────────────────────────────────
class TestBollingerBandwidth:
    def test_flat_series_zero_width(self) -> None:
        s = pd.Series([100.0] * 40)
        bbw = bollinger_bandwidth(s, 20, 2.0)
        assert bbw.iloc[-1] == pytest.approx(0.0, abs=1e-9)

    def test_high_variance_higher_width(self) -> None:
        flat = pd.Series([100.0] * 40)
        noisy = pd.Series(flat_close(100.0, 40, jitter_pct=0.02, seed=1))
        assert bollinger_bandwidth(noisy, 20).iloc[-1] > bollinger_bandwidth(flat, 20).iloc[-1]

    def test_min_periods_nan(self) -> None:
        s = pd.Series([100.0] * 5)
        assert bollinger_bandwidth(s, 20).isna().all()


# ──────────────────────────────────────────────────────────────────────────
# RVOL
# ──────────────────────────────────────────────────────────────────────────
class TestRVOL:
    def test_constant_volume_rvol_one(self) -> None:
        v = pd.Series([1_000_000] * 60)
        r = rvol(v, 50)
        assert r.iloc[-1] == pytest.approx(1.0, abs=1e-9)

    def test_spike_doubles_rvol(self) -> None:
        v = np.array([1_000_000] * 55 + [3_000_000])
        r = rvol(pd.Series(v), 50)
        assert r.iloc[-1] == pytest.approx(3.0, abs=1e-6)

    def test_excludes_today_from_baseline(self) -> None:
        # Last bar's spike should not contaminate its own denominator.
        v = pd.Series([1_000_000] * 50 + [10_000_000])
        r = rvol(v, 50)
        assert r.iloc[-1] == pytest.approx(10.0, abs=1e-6)


# ──────────────────────────────────────────────────────────────────────────
# Weekly resample
# ──────────────────────────────────────────────────────────────────────────
class TestWeeklyResample:
    def test_aggregations_correct(self) -> None:
        df = make_ohlcv(linear_close(100.0, 110.0, 25), intrabar_pct=0.01)
        weekly = weekly_resample(df)
        # last weekly close == last daily close
        assert weekly["close"].iloc[-1] == pytest.approx(df["close"].iloc[-1])
        # weekly volume sums daily volumes within each week
        first_week_days = df.loc[df.index <= weekly.index[0]]
        assert weekly["volume"].iloc[0] == pytest.approx(first_week_days["volume"].sum())

    def test_weekly_index_is_friday(self) -> None:
        df = make_ohlcv(linear_close(100.0, 110.0, 25))
        weekly = weekly_resample(df)
        assert all(weekly.index.dayofweek == 4)  # Friday


# ──────────────────────────────────────────────────────────────────────────
# Entry stop
# ──────────────────────────────────────────────────────────────────────────
class TestEntryStop:
    def test_uses_higher_of_ema20_or_atr_floor(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.002, 60), intrabar_pct=0.005)
        a = atr(df, 14)
        ema20 = ema(df["close"], 20)
        five_bar_low = df["low"].shift(1).rolling(5).min()
        stop = entry_stop(df, atr_series=a)
        # stop should equal the larger of the two legs at the last bar
        expected = max(ema20.iloc[-1], (five_bar_low.iloc[-1] - 0.5 * a.iloc[-1]))
        assert stop.iloc[-1] == pytest.approx(expected, abs=1e-9)

    def test_below_close_in_uptrend(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.002, 60), intrabar_pct=0.005)
        stop = entry_stop(df)
        assert stop.iloc[-1] < df["close"].iloc[-1]
