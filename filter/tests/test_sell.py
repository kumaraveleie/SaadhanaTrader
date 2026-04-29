"""§8 — SELL exit trigger tests."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from saadhana_filter.signals.sell import (
    Position,
    SellReason,
    evaluate_sell,
)
from tests.builders import flat_close, geometric_close, make_ohlcv


def _position(entry_price: float, current_stop: float, **kw) -> Position:
    return Position(
        symbol="TEST",
        entry_date=date(2026, 1, 1),
        entry_price=entry_price,
        initial_stop=current_stop,
        current_stop=current_stop,
        **kw,
    )


# ──────────────────────────────────────────────────────────────────────────
# §8.1 hard stops
# ──────────────────────────────────────────────────────────────────────────
class TestHardStops:
    def test_close_at_or_below_stop_fires_stop_hit(self) -> None:
        # Long flat, last bar drops below stop
        n = 220
        close = np.concatenate([np.full(n - 1, 100.0), [94.0]])
        df = make_ohlcv(close)
        pos = _position(entry_price=100.0, current_stop=95.0)
        assert evaluate_sell(df, pos) == SellReason.STOP_HIT

    def test_catastrophic_break_fires(self) -> None:
        # Strong uptrend, then a sharp -10% close on heavy volume
        n = 250
        up = geometric_close(80.0, 0.003, n - 1)
        crashed = np.append(up, up[-1] * 0.88)
        vol = np.full(n, 1_000_000.0)
        vol[-1] = 3_000_000.0
        df = make_ohlcv(crashed, volume=vol)
        # Stop is well below the crash level so STOP_HIT does not pre-empt
        pos = _position(entry_price=up[-1], current_stop=up[-1] * 0.7)
        assert evaluate_sell(df, pos) == SellReason.CATASTROPHIC_BREAK


# ──────────────────────────────────────────────────────────────────────────
# §8.2 profit ladder
# ──────────────────────────────────────────────────────────────────────────
class TestProfitLadder:
    def test_t1_hit_fires_first(self) -> None:
        n = 220
        close = np.concatenate([np.full(n - 1, 100.0), [105.5]])
        df = make_ohlcv(close)
        pos = _position(entry_price=100.0, current_stop=95.0)
        assert evaluate_sell(df, pos) == SellReason.T1_HIT

    def test_t2_hit_when_already_t1(self) -> None:
        n = 220
        close = np.concatenate([np.full(n - 1, 100.0), [110.5]])
        df = make_ohlcv(close)
        pos = _position(entry_price=100.0, current_stop=100.0, t1_hit=True)
        # T2 takes precedence over T1 in this branch ordering
        assert evaluate_sell(df, pos) == SellReason.T2_HIT

    def test_t3_trail_break_after_t2(self) -> None:
        # Long uptrend then a small dip below 20-EMA — final 33% exits
        n = 220
        up = geometric_close(100.0, 0.003, n - 1)
        # last bar dips below 20-EMA
        last = up[-1] * 0.95
        df = make_ohlcv(np.append(up, last))
        pos = _position(
            entry_price=up[0],
            current_stop=up[0] * 0.95,
            t1_hit=True,
            t2_hit=True,
        )
        assert evaluate_sell(df, pos) == SellReason.T3_TRAIL_BREAK


# ──────────────────────────────────────────────────────────────────────────
# §8.3 trend deterioration
# ──────────────────────────────────────────────────────────────────────────
class TestTrendDeterioration:
    def test_stage_shift_fires(self) -> None:
        # 30W SMA flat or falling AND close below it — stage shift
        n = 280
        rising = geometric_close(100.0, 0.0015, n - 80)
        falling = rising[-1] * np.power(1 - 0.005, np.arange(1, 81))
        df = make_ohlcv(np.concatenate([rising, falling]))
        pos = _position(entry_price=rising[0], current_stop=rising[0] * 0.5)
        assert evaluate_sell(df, pos) == SellReason.STAGE_SHIFT_EXIT

    def test_score_collapse_fires(self) -> None:
        # 200 rising bars then 80 flat — keeps Stage 2 alive (SMA still
        # rising, close above SMA) so STAGE_SHIFT does NOT pre-empt, but
        # the 5/20 EMA stack stops rising, momentum dies, and most §5
        # conditions fail → score ≤ 5 for the last 2 bars.
        # Entry at 200 keeps T1/T2/STOP all out of the way; the 25%
        # drawdown vs entry also pushes the path well outside the ±2%
        # TIME_EXIT band so SCORE_COLLAPSE wins cleanly.
        rising = geometric_close(100.0, 0.002, 200)
        flat = np.full(80, rising[-1])
        df = make_ohlcv(np.concatenate([rising, flat]))
        pos = _position(entry_price=200.0, current_stop=100.0)
        assert evaluate_sell(df, pos) == SellReason.SCORE_COLLAPSE_EXIT


# ──────────────────────────────────────────────────────────────────────────
# §8 — no trigger fires
# ──────────────────────────────────────────────────────────────────────────
class TestNoTriggerFires:
    def test_clean_uptrend_no_sell(self) -> None:
        # Flat path so score stays mid-range (no SCORE_COLLAPSE), no T1
        # hit (gain < 5%), no stop hit (stop = 70 vs close ≈ 100), no
        # stage shift (SMA still essentially flat), and no inst sells.
        df = make_ohlcv(geometric_close(100.0, 0.0001, 220))
        pos = _position(entry_price=100.0, current_stop=70.0)
        assert evaluate_sell(df, pos) is None


# ──────────────────────────────────────────────────────────────────────────
# §8 — defensive guards (NaN, short history, helper edge cases)
# ──────────────────────────────────────────────────────────────────────────
class TestDefensiveGuards:
    def test_inst_sell_exit_fires_with_distribution_volume(self) -> None:
        # Two heavy-volume DOWN days in last 5 on a clean Stage-2 path.
        # Entry well above current price keeps T2/T1 from pre-empting.
        n = 220
        up = geometric_close(100.0, 0.001, n - 1)
        close = np.append(up, up[-1] * 0.99)
        vol = np.full(n, 1_000_000.0)
        vol[-1] = 2_500_000.0
        close[-3] = close[-3] * 0.985
        vol[-3] = 2_500_000.0
        df = make_ohlcv(close, volume=vol)
        # Entry sits 2× current close so T1/T2/STOP cannot fire before §8.3
        last_close = float(close[-1])
        pos = _position(entry_price=last_close * 2.0, current_stop=last_close * 0.5)
        assert evaluate_sell(df, pos) == SellReason.INST_SELL_EXIT

    def test_short_history_no_stage_shift_pre_empts(self) -> None:
        # < 150 bars → 30W SMA undefined → STAGE_SHIFT branch is skipped.
        # Path is built so SCORE_COLLAPSE catches it instead. STOP_HIT
        # avoided by setting stop far below close.
        df = make_ohlcv(flat_close(100.0, 100, jitter_pct=0.001, seed=1))
        pos = _position(entry_price=100.0, current_stop=50.0)
        # Result must be SOMETHING other than STAGE_SHIFT (which depends
        # on the SMA being defined). Validates the line-128 NaN branch.
        result = evaluate_sell(df, pos)
        assert result != SellReason.STAGE_SHIFT_EXIT

    def test_close_below_sma_but_sma_rising_no_stage_shift(self) -> None:
        # 200 rising bars then a small dip below 30W SMA. SMA is still
        # rising on the last bar, so STAGE_SHIFT (which requires SMA
        # flat or falling) does not fire. Validates the 134->139 branch.
        rising = geometric_close(100.0, 0.001, 250)
        dipped = np.append(rising, rising[-1] * 0.95)
        df = make_ohlcv(dipped)
        pos = _position(entry_price=rising[0], current_stop=rising[0] * 0.5)
        # Either SCORE_COLLAPSE or T2_HIT or none of the §8.3 exits — but
        # crucially not STAGE_SHIFT.
        assert evaluate_sell(df, pos) != SellReason.STAGE_SHIFT_EXIT


# ──────────────────────────────────────────────────────────────────────────
# §8 — RSI divergence helper edge cases
# ──────────────────────────────────────────────────────────────────────────
class TestRsiDivergence:
    def test_rsi_below_threshold_no_divergence(self) -> None:
        # Mild uptrend → RSI ~60, well under 80 → divergence path skipped
        df = make_ohlcv(geometric_close(100.0, 0.0008, 220))
        pos = _position(entry_price=100.0, current_stop=70.0)
        result = evaluate_sell(df, pos)
        assert result != SellReason.RSI_DIVERGENCE_EXIT

    def test_short_df_no_divergence(self) -> None:
        # < 14 bars → divergence helper returns False on length guard.
        df = make_ohlcv(geometric_close(100.0, 0.005, 12))
        pos = _position(entry_price=100.0, current_stop=70.0)
        result = evaluate_sell(df, pos)
        assert result != SellReason.RSI_DIVERGENCE_EXIT


# ──────────────────────────────────────────────────────────────────────────
# §8.4 — TIME_EXIT specifics
# ──────────────────────────────────────────────────────────────────────────
class TestTimeExit:
    def test_time_exit_helper_fires_directly(self) -> None:
        # Test the §8.4 helper in isolation so we can hit lines 188-192
        # without fighting the spec-order priority of §8.1-§8.3 triggers.
        from saadhana_filter.signals.sell import _time_exit

        df = make_ohlcv(flat_close(100.0, 280, jitter_pct=0.002, seed=4))
        pos = _position(entry_price=100.0, current_stop=70.0)
        # Synthesize a strictly-declining score series so polyfit slope < 0
        score = pd.Series(
            np.linspace(13, 0, len(df)).astype(int),
            index=df.index,
            dtype="int64",
        )
        assert _time_exit(df, pos, score) is True

    def test_time_exit_helper_returns_false_when_score_rising(self) -> None:
        from saadhana_filter.signals.sell import _time_exit

        df = make_ohlcv(flat_close(100.0, 280, jitter_pct=0.002, seed=4))
        pos = _position(entry_price=100.0, current_stop=70.0)
        score = pd.Series(
            np.linspace(0, 13, len(df)).astype(int),
            index=df.index,
            dtype="int64",
        )
        assert _time_exit(df, pos, score) is False

    def test_time_exit_helper_returns_false_when_out_of_band(self) -> None:
        from saadhana_filter.signals.sell import _time_exit

        df = make_ohlcv(geometric_close(100.0, 0.0008, 280))  # drifts way off entry
        pos = _position(entry_price=100.0, current_stop=70.0)
        score = pd.Series(
            np.linspace(13, 0, len(df)).astype(int),
            index=df.index,
            dtype="int64",
        )
        assert _time_exit(df, pos, score) is False

    def test_time_exit_helper_returns_false_with_short_score_series(self) -> None:
        from saadhana_filter.signals.sell import _time_exit

        df = make_ohlcv(flat_close(100.0, 35, jitter_pct=0.002, seed=4))
        pos = _position(entry_price=100.0, current_stop=70.0)
        score = pd.Series(
            np.zeros(20, dtype="int64"),
            index=df.index[-20:],
        )
        # score has < 30 values → guard returns False (line 188)
        assert _time_exit(df, pos, score) is False

    def test_recent_entry_blocks_time_exit(self) -> None:
        # entry_date set to *yesterday* — days_since_entry < 30
        df = make_ohlcv(flat_close(100.0, 220, jitter_pct=0.001, seed=2))
        pos = Position(
            symbol="TEST",
            entry_date=df.index[-2].date(),
            entry_price=100.0,
            initial_stop=70.0,
            current_stop=70.0,
        )
        result = evaluate_sell(df, pos)
        assert result != SellReason.TIME_EXIT


# ──────────────────────────────────────────────────────────────────────────
# Helpers — _is_partial classifier
# ──────────────────────────────────────────────────────────────────────────
class TestIsPartial:
    def test_partial_reasons(self) -> None:
        from saadhana_filter.signals.sell import _is_partial

        for reason in (SellReason.T1_HIT, SellReason.T2_HIT, SellReason.T3_TRAIL_BREAK):
            assert _is_partial(reason)

    def test_full_close_reasons(self) -> None:
        from saadhana_filter.signals.sell import _is_partial

        for reason in (
            SellReason.STOP_HIT,
            SellReason.CATASTROPHIC_BREAK,
            SellReason.STAGE_SHIFT_EXIT,
            SellReason.SCORE_COLLAPSE_EXIT,
            SellReason.INST_SELL_EXIT,
            SellReason.RSI_DIVERGENCE_EXIT,
            SellReason.TIME_EXIT,
        ):
            assert not _is_partial(reason)
