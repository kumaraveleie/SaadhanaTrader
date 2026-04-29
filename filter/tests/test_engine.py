"""§3/§5/§9/§12 — signal engine orchestration tests."""

from __future__ import annotations

from datetime import date

import numpy as np

from saadhana_filter.indicators.conditions import ALL_CONDITIONS
from saadhana_filter.signals.engine import classify_signal
from saadhana_filter.signals.regime import Regime
from saadhana_filter.signals.sell import Position, SellReason
from saadhana_filter.signals.state import SignalState
from tests.builders import flat_close, geometric_close, make_ohlcv


def _pos(entry: float, stop: float, **kw) -> Position:
    return Position(
        symbol="TEST",
        entry_date=date(2026, 1, 1),
        entry_price=entry,
        initial_stop=stop,
        current_stop=stop,
        **kw,
    )


# ──────────────────────────────────────────────────────────────────────────
# Unheld branch — Tier 1 + regime gating
# ──────────────────────────────────────────────────────────────────────────
class TestUnheldBranch:
    def test_tier1_failed_yields_wait(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        d = classify_signal(df, symbol="X", tier1_passed=False, regime=Regime.RISK_ON)
        assert d.signal == SignalState.WAIT
        assert "tier1_failed" in d.notes

    def test_risk_off_regime_yields_wait_even_with_perfect_score(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.RISK_OFF)
        assert d.signal == SignalState.WAIT
        assert "regime_risk_off" in d.notes

    def test_low_score_yields_wait(self) -> None:
        # Sideways → score will be far from 13
        df = make_ohlcv(flat_close(100.0, 280, jitter_pct=0.002, seed=3))
        d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.RISK_ON)
        assert d.signal == SignalState.WAIT
        assert d.pro_setup_score < 10

    def test_caution_regime_never_emits_buy(self) -> None:
        """Until §14 conviction-tier logic lands (Phase F), Caution-regime
        decisions can never resolve BUY — they downgrade to WATCH and
        carry the explanatory note for the ledger. Validated by patching
        ``pro_setup_score`` to force a perfect 13/13 score frame."""
        from unittest.mock import patch

        import pandas as pd

        from saadhana_filter.indicators.conditions import ALL_CONDITIONS

        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        cond_cols = {name: True for name, _ in ALL_CONDITIONS}
        synthetic = pd.DataFrame({**cond_cols, "score": 13}, index=df.index)
        synthetic["score"] = synthetic["score"].astype("int64")
        with patch(
            "saadhana_filter.signals.engine.pro_setup_score",
            return_value=synthetic,
        ):
            d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.CAUTION)
        assert d.signal == SignalState.WATCH
        assert d.pro_setup_score == 13
        assert "caution_regime_buy_downgraded_pending_§14" in d.notes
        # The downgrade does not emit risk levels — that's a BUY-only payload.
        assert d.risk is None

    def test_caution_regime_low_score_still_wait(self) -> None:
        """Caution regime + low score still resolves WAIT (the downgrade
        only applies when score reaches the BUY threshold)."""
        df = make_ohlcv(flat_close(100.0, 280, jitter_pct=0.002, seed=3))
        d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.CAUTION)
        assert d.signal == SignalState.WAIT
        assert "caution_regime_buy_downgraded_pending_§14" not in d.notes

    def test_risk_on_score_13_emits_buy(self) -> None:
        """Sanity check the other branch: Risk_On + score 13 still BUYs."""
        from unittest.mock import patch

        import pandas as pd

        from saadhana_filter.indicators.conditions import ALL_CONDITIONS

        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        cond_cols = {name: True for name, _ in ALL_CONDITIONS}
        synthetic = pd.DataFrame({**cond_cols, "score": 13}, index=df.index)
        synthetic["score"] = synthetic["score"].astype("int64")
        with patch(
            "saadhana_filter.signals.engine.pro_setup_score",
            return_value=synthetic,
        ):
            d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.RISK_ON)
        assert d.signal == SignalState.BUY
        assert d.risk is not None


# ──────────────────────────────────────────────────────────────────────────
# Held branch — SELL takes priority over HOLD
# ──────────────────────────────────────────────────────────────────────────
class TestHeldBranch:
    def test_open_position_no_trigger_yields_hold(self) -> None:
        # Flat path → no T1/T2 hit, no stop hit, no catastrophic break
        df = make_ohlcv(geometric_close(100.0, 0.0001, 280))
        pos = _pos(entry=100.0, stop=70.0)
        d = classify_signal(
            df,
            symbol="TEST",
            tier1_passed=True,
            regime=Regime.RISK_ON,
            position=pos,
        )
        assert d.signal == SignalState.HOLD
        assert d.sell_reason is None

    def test_stop_hit_yields_sell(self) -> None:
        n = 220
        close = np.concatenate([np.full(n - 1, 100.0), [90.0]])
        df = make_ohlcv(close)
        pos = _pos(entry=100.0, stop=95.0)
        d = classify_signal(
            df,
            symbol="TEST",
            tier1_passed=True,
            regime=Regime.RISK_ON,
            position=pos,
        )
        assert d.signal == SignalState.SELL
        assert d.sell_reason == SellReason.STOP_HIT
        # Held names with SELL trigger never carry risk_levels (paired
        # entry has already happened at signal time).
        assert d.risk is None

    def test_held_position_ignores_tier1_failure(self) -> None:
        # A Tier 1 failure does not force-close an already-open position;
        # only §8 triggers can. Here Tier 1 fails but the engine should
        # still HOLD because no §8 trigger fires.
        df = make_ohlcv(geometric_close(100.0, 0.0001, 280))
        pos = _pos(entry=100.0, stop=70.0)
        d = classify_signal(
            df,
            symbol="TEST",
            tier1_passed=False,
            regime=Regime.RISK_ON,
            position=pos,
        )
        assert d.signal == SignalState.HOLD


# ──────────────────────────────────────────────────────────────────────────
# Decision payload shape
# ──────────────────────────────────────────────────────────────────────────
class TestDecisionShape:
    def test_conditions_keys_match_canonical(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.RISK_ON)
        expected = {name for name, _ in ALL_CONDITIONS}
        assert set(d.conditions.keys()) == expected

    def test_failed_conditions_complement_met_set(self) -> None:
        df = make_ohlcv(flat_close(100.0, 280, jitter_pct=0.002, seed=3))
        d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.RISK_ON)
        for name in d.failed_conditions:
            assert d.conditions[name] is False

    def test_drs_within_range(self) -> None:
        df = make_ohlcv(geometric_close(100.0, 0.0015, 280))
        d = classify_signal(df, symbol="X", tier1_passed=True, regime=Regime.RISK_ON)
        assert 0.0 <= d.drs <= 100.0
