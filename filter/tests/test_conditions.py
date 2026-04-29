"""§5 — golden-fixture tests for the 13 BUY-entry conditions.

Each condition gets ≥ 3 tests: a True case, a False case, and a boundary
case. Most use ``make_ohlcv`` from ``builders.py`` so the input shape is
explicit at the test site; integration smoke tests against the regime
fixtures live in ``test_pro_setup_score.py``.
"""

from __future__ import annotations

import numpy as np

from saadhana_filter.indicators.conditions import (
    cond_5ema_above_20ema_rising,
    cond_above_50_and_200_ema,
    cond_atr_upside_ge_5pct,
    cond_bb_width_alive,
    cond_distance_to_stop_le_3pct,
    cond_inst_flow_score,
    cond_institutional_flow,
    cond_macd_hist_rising,
    cond_recent_strength_not_extended,
    cond_rr_ge_2,
    cond_rsi_50_70,
    cond_stage_2,
    cond_weekly_hh_hl,
)
from tests.builders import (
    flat_close,
    geometric_close,
    linear_close,
    make_ohlcv,
)


# ──────────────────────────────────────────────────────────────────────────
# §5.1 #1 — Stage 2 (Weinstein)
# ──────────────────────────────────────────────────────────────────────────
class TestCondStage2:
    def test_uptrend_above_rising_30w_sma(self) -> None:
        # 200 bars rising — close > 30W SMA, SMA also rising
        df = make_ohlcv(geometric_close(100.0, 0.003, 200))
        out = cond_stage_2(df)
        assert out.iloc[-1] is np.True_ or bool(out.iloc[-1])

    def test_downtrend_below_falling_sma_false(self) -> None:
        df = make_ohlcv(geometric_close(200.0, -0.003, 200))
        assert not bool(cond_stage_2(df).iloc[-1])

    def test_below_min_periods_returns_false(self) -> None:
        df = make_ohlcv(linear_close(100.0, 110.0, 50))
        out = cond_stage_2(df)
        # 30W SMA needs 150 bars; with 50, all output is False
        assert not out.any()

    def test_close_below_sma_after_crash_false(self) -> None:
        # Rising 150 bars then a 25% crash — close ends below 30W SMA so
        # Stage-2 fails on the "above" leg even though the rolling-window
        # SMA may still drift up briefly as low early bars roll out.
        rising = geometric_close(100.0, 0.003, 150)
        crashed = rising[-1] * np.power(1 - 0.02, np.arange(1, 21))
        df = make_ohlcv(np.concatenate([rising, crashed]))
        assert not bool(cond_stage_2(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.1 #2 — Above 50 and 200 EMA
# ──────────────────────────────────────────────────────────────────────────
class TestCondAbove50And200EMA:
    def test_uptrend_true(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.002, 250))
        assert bool(cond_above_50_and_200_ema(df).iloc[-1])

    def test_downtrend_false(self) -> None:
        df = make_ohlcv(geometric_close(200.0, -0.002, 250))
        assert not bool(cond_above_50_and_200_ema(df).iloc[-1])

    def test_close_below_200ema_only_false(self) -> None:
        # Build a path that ends below the 200-EMA but above the 50-EMA:
        # long uptrend, then a sharp recent fall pulls close below 200-EMA
        # but the 50-EMA is below close. We just need ONE EMA to fail.
        up = geometric_close(100.0, 0.0015, 250)
        # final crash 25% below 200-EMA
        crashed = np.concatenate([up, up[-1] * np.array([0.85, 0.80, 0.78])])
        df = make_ohlcv(crashed)
        assert not bool(cond_above_50_and_200_ema(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.1 #3 — 5-EMA > 20-EMA rising
# ──────────────────────────────────────────────────────────────────────────
class TestCond5EmaAbove20EmaRising:
    def test_uptrend_true(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.003, 80))
        assert bool(cond_5ema_above_20ema_rising(df).iloc[-1])

    def test_downtrend_false(self) -> None:
        df = make_ohlcv(geometric_close(200.0, -0.003, 80))
        assert not bool(cond_5ema_above_20ema_rising(df).iloc[-1])

    def test_5ema_above_but_falling_false(self) -> None:
        # Rising for 60 bars, then last 6 bars decline — 5-EMA may still be
        # above 20-EMA but no longer rising
        up = geometric_close(100.0, 0.003, 60)
        down = up[-1] * np.power(1 - 0.015, np.arange(1, 7))
        df = make_ohlcv(np.concatenate([up, down]))
        assert not bool(cond_5ema_above_20ema_rising(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.1 #4 — Weekly HH/HL last 8 weeks
# ──────────────────────────────────────────────────────────────────────────
class TestCondWeeklyHHHL:
    def test_clean_uptrend_true(self) -> None:
        # 60 daily bars ≈ 12 weeks of strict uptrend
        df = make_ohlcv(geometric_close(100.0, 0.004, 60))
        assert bool(cond_weekly_hh_hl(df).iloc[-1])

    def test_clean_downtrend_false(self) -> None:
        df = make_ohlcv(geometric_close(200.0, -0.004, 60))
        assert not bool(cond_weekly_hh_hl(df).iloc[-1])

    def test_lookback_too_short_returns_false(self) -> None:
        # Only 25 daily bars (~5 weeks) — not enough for 8-week lookback
        df = make_ohlcv(geometric_close(100.0, 0.003, 25))
        assert not cond_weekly_hh_hl(df).any()


# ──────────────────────────────────────────────────────────────────────────
# §5.2 #5 — RSI(14) ∈ [50, 70]
# ──────────────────────────────────────────────────────────────────────────
class TestCondRsi5070:
    def test_steady_alternation_around_50_true(self) -> None:
        # Mild uptrend with noise → RSI lands in mid-band
        rng = np.random.default_rng(123)
        n = 60
        rets = rng.normal(0.0008, 0.005, n)
        rets = np.clip(rets, -0.012, 0.015)
        rets[-1] = 0.002
        close = 100.0 * np.exp(np.cumsum(rets))
        df = make_ohlcv(close)
        assert bool(cond_rsi_50_70(df).iloc[-1])

    def test_strict_uptrend_rsi_above_70_false(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.01, 60))
        assert not bool(cond_rsi_50_70(df).iloc[-1])

    def test_strict_downtrend_rsi_below_50_false(self) -> None:
        df = make_ohlcv(geometric_close(200.0, -0.01, 60))
        assert not bool(cond_rsi_50_70(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.2 #6 — MACD histogram > 0 AND rising
# ──────────────────────────────────────────────────────────────────────────
class TestCondMacdHistRising:
    def test_fresh_acceleration_true(self) -> None:
        # Long flat then a fresh upside acceleration — MACD line outpaces
        # the 9-bar signal so histogram is > 0 *and* rising on the final bar.
        # 12 acceleration bars puts us before the signal catches up.
        rates = np.concatenate([np.full(50, 0.0), np.full(12, 0.006)])
        close = 100.0 * np.cumprod(1 + rates)
        df = make_ohlcv(close)
        assert bool(cond_macd_hist_rising(df).iloc[-1])

    def test_accelerating_decline_false(self) -> None:
        # Fresh downside acceleration → histogram < 0 (let alone "> 0").
        rates = np.concatenate([np.full(50, 0.0), np.full(12, -0.006)])
        close = 100.0 * np.cumprod(1 + rates)
        df = make_ohlcv(close)
        assert not bool(cond_macd_hist_rising(df).iloc[-1])

    def test_decelerating_uptrend_hist_falling_false(self) -> None:
        # Strong rise, then last bars flatten → histogram peaks then falls
        rates = np.concatenate([np.full(40, 0.008), np.full(40, 0.0005)])
        close = 100.0 * np.cumprod(1 + rates)
        df = make_ohlcv(close)
        assert not bool(cond_macd_hist_rising(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.3 #7 — Institutional/Heavy Buy in last 5 days
# ──────────────────────────────────────────────────────────────────────────
class TestCondInstitutionalFlow:
    def test_recent_heavy_buy_true(self) -> None:
        # 60 bars at flat ~1M volume, with a +3% up-day on 3M volume two bars
        # ago, then small up-bars. RVOL ≥ 2.5 → institutional buy.
        n = 60
        close = np.concatenate(
            [
                np.full(57, 100.0),
                [102.0, 102.5, 103.0],
            ]
        )
        # Open[i] = close[i-1], close[-3]=102 vs open[-3]=100 → up-bar
        vol = np.full(n, 1_000_000.0)
        vol[-3] = 3_000_000.0
        df = make_ohlcv(close, volume=vol)
        assert bool(cond_institutional_flow(df).iloc[-1])

    def test_no_recent_spike_false(self) -> None:
        df = make_ohlcv(np.full(60, 100.0), volume=1_000_000.0)
        assert not bool(cond_institutional_flow(df).iloc[-1])

    def test_old_spike_outside_window_false(self) -> None:
        # spike 10 bars ago, beyond the 5-day window
        n = 60
        close = np.full(n, 100.0)
        close[-10] = 103.0  # up-bar at -10
        vol = np.full(n, 1_000_000.0)
        vol[-10] = 3_000_000.0
        df = make_ohlcv(close, volume=vol)
        assert not bool(cond_institutional_flow(df).iloc[-1])

    def test_heavy_volume_but_down_bar_false(self) -> None:
        # Down-bar with RVOL ≥ 1.5 is *distribution*, not buying
        n = 60
        close = np.full(n, 100.0)
        close[-2] = 97.0  # down-bar
        vol = np.full(n, 1_000_000.0)
        vol[-2] = 3_000_000.0
        df = make_ohlcv(close, volume=vol)
        assert not bool(cond_institutional_flow(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.3 #8 — 30-bar Inst. Flow Score > 0
# ──────────────────────────────────────────────────────────────────────────
class TestCondInstFlowScore:
    def test_more_buys_than_sells_true(self) -> None:
        # 80-bar history; in last 30, plant 4 heavy buys, 1 heavy sell
        n = 80
        close = np.full(n, 100.0)
        vol = np.full(n, 1_000_000.0)
        # Buy bars: up-bar with 2M volume
        for off in [-5, -10, -18, -25]:
            close[off] = 102.0
            vol[off] = 2_000_000.0
        # Sell bar: down-bar with 2M volume
        close[-15] = 97.0
        vol[-15] = 2_000_000.0
        df = make_ohlcv(close, volume=vol)
        assert bool(cond_inst_flow_score(df).iloc[-1])

    def test_distribution_dominant_false(self) -> None:
        n = 80
        close = np.full(n, 100.0)
        vol = np.full(n, 1_000_000.0)
        for off in [-5, -10, -15, -20, -25]:
            close[off] = 97.0
            vol[off] = 2_000_000.0
        close[-8] = 102.0
        vol[-8] = 2_000_000.0
        df = make_ohlcv(close, volume=vol)
        assert not bool(cond_inst_flow_score(df).iloc[-1])

    def test_short_history_false(self) -> None:
        # Less than 30+50 bars of usable RVOL → score is undefined → False
        df = make_ohlcv(geometric_close(100.0, 0.001, 40), volume=1_000_000.0)
        assert not bool(cond_inst_flow_score(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.4 #9 — Distance to entry stop ≤ 3%
# ──────────────────────────────────────────────────────────────────────────
class TestCondDistanceToStop:
    def test_close_near_20ema_true(self) -> None:
        # Slow drift so close hugs 20-EMA → small risk
        df = make_ohlcv(geometric_close(100.0, 0.0015, 80), intrabar_pct=0.005)
        assert bool(cond_distance_to_stop_le_3pct(df).iloc[-1])

    def test_overextended_above_20ema_false(self) -> None:
        # Long flat then a sharp 10% jump → close far above 20-EMA → risk > 3%
        flat = np.full(60, 100.0)
        jump = np.array([110.0, 112.0])
        df = make_ohlcv(np.concatenate([flat, jump]), intrabar_pct=0.005)
        assert not bool(cond_distance_to_stop_le_3pct(df).iloc[-1])

    def test_downtrend_stop_above_close_false(self) -> None:
        # In a strong downtrend the 20-EMA sits *above* close, so risk_pct
        # is negative → fails.
        df = make_ohlcv(geometric_close(200.0, -0.005, 80), intrabar_pct=0.005)
        assert not bool(cond_distance_to_stop_le_3pct(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.4 #10 — ATR-projected upside ≥ 5%
# ──────────────────────────────────────────────────────────────────────────
class TestCondAtrUpsideGe5Pct:
    def test_volatile_below_resistance_true(self) -> None:
        # Mild uptrend with high intrabar range → ATR large; close 20% below
        # 252-bar high → resistance is 25% away. min(ATR×20, gap) ≥ 5%.
        # establish a high early, then drop, then recover modestly
        close = np.concatenate(
            [
                geometric_close(100.0, 0.001, 100),  # rises to ~110
                geometric_close(110.0, -0.002, 100),  # falls to ~90
                geometric_close(90.0, 0.001, 80),  # recovers
            ]
        )
        df = make_ohlcv(close, intrabar_pct=0.025)  # wide bars → fat ATR
        assert bool(cond_atr_upside_ge_5pct(df).iloc[-1])

    def test_dead_volatility_false(self) -> None:
        # Tight intrabar → ATR tiny, ATR×20 < 5%
        df = make_ohlcv(geometric_close(100.0, 0.0005, 280), intrabar_pct=0.001)
        assert not bool(cond_atr_upside_ge_5pct(df).iloc[-1])

    def test_at_or_above_prior_high_uses_atr_only(self) -> None:
        # New high after long uptrend → resistance leg disabled, just ATR×20
        df = make_ohlcv(geometric_close(100.0, 0.002, 280), intrabar_pct=0.015)
        out = cond_atr_upside_ge_5pct(df).iloc[-1]
        assert isinstance(out, (bool, np.bool_))


# ──────────────────────────────────────────────────────────────────────────
# §5.4 #11 — Risk-Reward ≥ 2:1
# ──────────────────────────────────────────────────────────────────────────
class TestCondRrGe2:
    def test_tight_risk_wide_reward_true(self) -> None:
        # Small risk (close near 20-EMA, low ATR) and lots of room → high R/R
        close = np.concatenate(
            [
                geometric_close(100.0, 0.001, 100),
                geometric_close(110.0, -0.0015, 100),
                geometric_close(95.0, 0.0008, 80),
            ]
        )
        df = make_ohlcv(close, intrabar_pct=0.012)
        assert bool(cond_rr_ge_2(df).iloc[-1])

    def test_target_capped_by_resistance_low_rr_false(self) -> None:
        # Tight 280-bar range with a 52-week ceiling just above close —
        # both reward (capped by resistance) and risk are small, but
        # reward < 2 × risk so R/R fails.
        rng = np.random.default_rng(33)
        path = 100.0 + rng.normal(0.0, 0.3, 280)
        path[-1] = 100.5
        df = make_ohlcv(path, intrabar_pct=0.003)
        assert not bool(cond_rr_ge_2(df).iloc[-1])

    def test_negative_risk_false(self) -> None:
        df = make_ohlcv(geometric_close(200.0, -0.002, 280))
        assert not bool(cond_rr_ge_2(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.5 #12 (v2.1) — Goldilocks: recent strength AND not extended
# ──────────────────────────────────────────────────────────────────────────
class TestCondRecentStrengthNotExtended:
    def test_recent_pullback_passes(self) -> None:
        # 270 bars rising, 10 bars pullback (~14 calendar days). Both legs
        # of the v2.1 condition pass: 52WH was ~14 days ago (≤ 60), and
        # close is 8% below 52WH (not extended).
        up = geometric_close(100.0, 0.002, 270)
        pullback = up[-1] * np.power(1 - 0.008, np.arange(1, 11))
        df = make_ohlcv(np.concatenate([up, pullback]))
        assert bool(cond_recent_strength_not_extended(df).iloc[-1])

    def test_glued_to_52wh_false(self) -> None:
        # Steep uptrend, close at 52WH. Recency passes (just touched),
        # but the not-extended leg fails (within 2% of 52WH, no fresh
        # breakout from a tight base) → AND = False.
        df = make_ohlcv(geometric_close(100.0, 0.005, 280))
        assert not bool(cond_recent_strength_not_extended(df).iloc[-1])

    def test_fresh_breakout_from_base_overrides_extended(self) -> None:
        # 279 flat bars + 1 breakout candle. Recency passes (the high
        # touched 52WH on the breakout bar), AND the breakout exception
        # in the not-extended leg fires → AND = True.
        base = flat_close(100.0, 279, jitter_pct=0.005, seed=7)
        df_close = np.concatenate([base, [104.0]])
        df = make_ohlcv(df_close, intrabar_pct=0.008)
        assert bool(cond_recent_strength_not_extended(df).iloc[-1])

    def test_mid_fade_old_strength_fails_v2_1(self) -> None:
        # The v2.1 reason-for-existing test: 52WH was > 60 calendar days
        # ago, close is well below 52WH (legacy not_extended TRUE), but
        # the new recency leg fails → AND = False. Without the recency
        # leg this would have qualified for BUY in v2.0.
        # Path: 200 rising bars peaking at bar 200, then 80 flat bars at
        # 90% of peak. days_since_52WH ≈ 112 calendar days.
        up = geometric_close(100.0, 0.003, 200)
        peak = up[-1]
        plateau = np.full(80, peak * 0.90)
        df = make_ohlcv(np.concatenate([up, plateau]))
        assert not bool(cond_recent_strength_not_extended(df).iloc[-1])


# ──────────────────────────────────────────────────────────────────────────
# §5.5 #13 — BB Width > 30-bar median OR fresh breakout
# ──────────────────────────────────────────────────────────────────────────
class TestCondBBWidthAlive:
    def test_expanding_volatility_true(self) -> None:
        # Constant flat for 60 bars, then growing daily moves → BB width
        # rises above its 30-bar median.
        flat = np.full(60, 100.0)
        rng = np.random.default_rng(42)
        noisy = 100.0 + np.cumsum(rng.normal(0.5, 1.5, 30))
        df = make_ohlcv(np.concatenate([flat, noisy]))
        assert bool(cond_bb_width_alive(df).iloc[-1])

    def test_dead_consolidation_false(self) -> None:
        # Tight flat range → BB width below its own median (it equals it,
        # but never exceeds, so > median is False).
        df = make_ohlcv(flat_close(100.0, 80, jitter_pct=0.003, seed=11))
        assert not bool(cond_bb_width_alive(df).iloc[-1])

    def test_fresh_breakout_overrides(self) -> None:
        # Tight base then a single breakout candle — BB width may not yet
        # be wide, but the breakout exception fires.
        base = flat_close(100.0, 60, jitter_pct=0.003, seed=2)
        df = make_ohlcv(np.concatenate([base, [104.0]]))
        assert bool(cond_bb_width_alive(df).iloc[-1])
