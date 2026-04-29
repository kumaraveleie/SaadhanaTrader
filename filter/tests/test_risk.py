"""§5.4 + §6 + §7 — risk levels and Downside Resistance Score tests."""

from __future__ import annotations

import pytest

from saadhana_filter.signals.risk import (
    DRS_WEIGHTS,
    PROFIT_T1_PCT,
    PROFIT_T2_PCT,
    downside_resistance_score,
    risk_levels,
)
from tests.builders import geometric_close, make_ohlcv


# ──────────────────────────────────────────────────────────────────────────
# risk_levels
# ──────────────────────────────────────────────────────────────────────────
class TestRiskLevels:
    def test_targets_are_5_and_10_percent_of_entry(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 100))
        r = risk_levels(df)
        assert r.target_t1 == pytest.approx(r.entry_price * (1 + PROFIT_T1_PCT))
        assert r.target_t2 == pytest.approx(r.entry_price * (1 + PROFIT_T2_PCT))

    def test_stop_is_below_entry_in_uptrend(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 100))
        r = risk_levels(df)
        assert r.stop_loss < r.entry_price
        assert r.risk_pct > 0

    def test_rr_ratio_matches_reward_over_risk(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 100))
        r = risk_levels(df)
        assert r.rr_ratio == pytest.approx(r.reward_pct / r.risk_pct)


# ──────────────────────────────────────────────────────────────────────────
# Downside Resistance Score (§6)
# ──────────────────────────────────────────────────────────────────────────
class TestDownsideResistanceScore:
    def test_drs_in_zero_to_hundred_range(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        score = downside_resistance_score(df)
        assert 0.0 <= score <= 100.0

    def test_uptrend_outscores_downtrend(self) -> None:
        up = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        down = make_ohlcv(geometric_close(200.0, -0.0015, 280))
        assert downside_resistance_score(up) > downside_resistance_score(down)

    def test_short_history_returns_zero_or_low(self) -> None:
        # Insufficient lookback for the 90-bar inst flow + 200-EMA components
        df = make_ohlcv(geometric_close(100.0, 0.0015, 30))
        score = downside_resistance_score(df)
        assert score < 60.0

    def test_weights_sum_to_100(self) -> None:
        assert sum(DRS_WEIGHTS.values()) == 100
