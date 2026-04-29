"""§15 — daily scan entrypoint tests (no network, synthetic OHLCV)."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

from saadhana_filter.scan.daily import run_scan, scan_to_json
from saadhana_filter.scan.universe import (
    NIFTY_50,
    UniverseScope,
    get_universe,
)
from saadhana_filter.signals.regime import Regime
from saadhana_filter.signals.state import SignalState
from tests.builders import flat_close, geometric_close, make_ohlcv


# ──────────────────────────────────────────────────────────────────────────
# Universe
# ──────────────────────────────────────────────────────────────────────────
class TestUniverse:
    def test_nifty_50_has_50_symbols(self) -> None:
        assert len(NIFTY_50) == 50

    def test_no_duplicates(self) -> None:
        assert len(set(NIFTY_50)) == len(NIFTY_50)

    def test_get_universe_default(self) -> None:
        assert get_universe() == NIFTY_50

    def test_get_universe_500_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            get_universe(UniverseScope.NIFTY_500)


# ──────────────────────────────────────────────────────────────────────────
# Scan integration
# ──────────────────────────────────────────────────────────────────────────
PASSING_FUNDAMENTALS = {
    "market_cap_cr": 100_000.0,
    "eps_yoy": 12.0,
    "revenue_yoy": 8.0,
    "promoter_holding_pct": 50.0,
    "promoter_pledge_pct": 0.0,
    "debt_to_equity": 0.5,
    "sector": "PHARMA",
    "fno_banned": False,
    "sebi_surveillance": False,
    "gnpa": 0.0,
    "car": 0.0,
}


def _fund_frame(symbols: list[str], **per_symbol_overrides) -> pd.DataFrame:
    rows = []
    for s in symbols:
        row = {"symbol": s, **PASSING_FUNDAMENTALS}
        if s in per_symbol_overrides:
            row.update(per_symbol_overrides[s])
        rows.append(row)
    return pd.DataFrame(rows).set_index("symbol")


def _provider_factory(per_symbol: dict[str, pd.DataFrame]) -> callable:
    def _provider(symbol: str) -> pd.DataFrame:
        return per_symbol[symbol]

    return _provider


@pytest.fixture
def nifty_risk_on_df() -> pd.DataFrame:
    return make_ohlcv(geometric_close(15_000.0, 0.001, 280))


@pytest.fixture
def nifty_risk_off_df() -> pd.DataFrame:
    return make_ohlcv(geometric_close(20_000.0, -0.001, 280))


def test_scan_returns_spec_15_shape(nifty_risk_on_df: pd.DataFrame) -> None:
    universe = ("AAA", "BBB")
    fundamentals = _fund_frame(list(universe))
    provider = _provider_factory(
        {
            "AAA": make_ohlcv(geometric_close(100.0, 0.0015, 280)),
            "BBB": make_ohlcv(flat_close(100.0, 280, jitter_pct=0.002, seed=1)),
        }
    )
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=universe,
        fundamentals=fundamentals,
        nifty_df=nifty_risk_on_df,
        ohlcv_provider=provider,
    )
    assert result["scan_date"] == "2026-04-29"
    assert result["regime"] == Regime.RISK_ON.value
    assert result["universe_size"] == 2
    assert result["tier1_passed"] == 2
    assert "candidates" in result


def test_scan_skips_symbols_failing_tier1_for_unheld_names(
    nifty_risk_on_df: pd.DataFrame,
) -> None:
    universe = ("AAA", "BAD")
    fundamentals = _fund_frame(list(universe), BAD={"market_cap_cr": 1_000.0})
    provider = _provider_factory(
        {
            "AAA": make_ohlcv(geometric_close(100.0, 0.0015, 280)),
            "BAD": make_ohlcv(geometric_close(100.0, 0.0015, 280)),
        }
    )
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=universe,
        fundamentals=fundamentals,
        nifty_df=nifty_risk_on_df,
        ohlcv_provider=provider,
    )
    assert result["tier1_passed"] == 1
    bad_rows = [c for c in result["candidates"] if c["symbol"] == "BAD"]
    # BAD failed Tier 1 and isn't held, so the engine resolves WAIT and
    # it should be omitted from the candidates list.
    assert bad_rows == []


def test_scan_propagates_risk_off_regime(nifty_risk_off_df: pd.DataFrame) -> None:
    universe = ("AAA",)
    fundamentals = _fund_frame(list(universe))
    provider = _provider_factory({"AAA": make_ohlcv(geometric_close(100.0, 0.0015, 280))})
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=universe,
        fundamentals=fundamentals,
        nifty_df=nifty_risk_off_df,
        ohlcv_provider=provider,
    )
    assert result["regime"] == Regime.RISK_OFF.value
    # No BUY in Risk_Off — only WAIT (suppressed) or held-name HOLD/SELL
    buys = [c for c in result["candidates"] if c["signal"] == SignalState.BUY.value]
    assert buys == []


def test_scan_handles_missing_ohlcv_gracefully(
    nifty_risk_on_df: pd.DataFrame,
) -> None:
    def broken_provider(symbol: str) -> pd.DataFrame:
        raise FileNotFoundError(f"no cache for {symbol}")

    fundamentals = _fund_frame(["AAA"])
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=("AAA",),
        fundamentals=fundamentals,
        nifty_df=nifty_risk_on_df,
        ohlcv_provider=broken_provider,
    )
    # Skipped symbols don't appear in candidates (signal stays WAIT)
    assert result["candidates"] == []


def test_scan_to_json_is_valid_json(nifty_risk_on_df: pd.DataFrame) -> None:
    universe = ("AAA",)
    fundamentals = _fund_frame(list(universe))
    provider = _provider_factory({"AAA": make_ohlcv(geometric_close(100.0, 0.0015, 280))})
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=universe,
        fundamentals=fundamentals,
        nifty_df=nifty_risk_on_df,
        ohlcv_provider=provider,
    )
    blob = scan_to_json(result)
    parsed = json.loads(blob)
    assert parsed["scan_date"] == "2026-04-29"


def test_scan_handles_empty_ohlcv_gracefully(nifty_risk_on_df: pd.DataFrame) -> None:
    """Empty DataFrame from the provider triggers the ``empty_ohlcv``
    skip branch, distinct from the exception branch covered above."""
    fundamentals = _fund_frame(["AAA"])
    provider = _provider_factory({"AAA": pd.DataFrame()})
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=("AAA",),
        fundamentals=fundamentals,
        nifty_df=nifty_risk_on_df,
        ohlcv_provider=provider,
    )
    assert result["candidates"] == []


def test_held_position_produces_hold_candidate_row(
    nifty_risk_on_df: pd.DataFrame,
) -> None:
    """Held names always evaluate via the §8 SELL branch and produce a
    candidate row even when score < 13. Validates that the daily runner
    threads ``positions`` through and emits a HOLD row in §15 shape."""
    from datetime import date as _date

    from saadhana_filter.signals.sell import Position

    universe = ("HELD",)
    fundamentals = _fund_frame(list(universe))
    # Flat path so no T1/STOP/STAGE_SHIFT triggers — engine returns HOLD.
    provider = _provider_factory({"HELD": make_ohlcv(geometric_close(100.0, 0.0001, 280))})
    pos = Position(
        symbol="HELD",
        entry_date=_date(2026, 1, 1),
        entry_price=100.0,
        initial_stop=70.0,
        current_stop=70.0,
    )
    result = run_scan(
        scan_date=date(2026, 4, 29),
        universe=universe,
        fundamentals=fundamentals,
        nifty_df=nifty_risk_on_df,
        ohlcv_provider=provider,
        positions={"HELD": pos},
    )
    assert len(result["candidates"]) == 1
    row = result["candidates"][0]
    assert row["signal"] == SignalState.HOLD.value
    assert row["sell_reason"] is None
    assert "entry_price" not in row  # HOLD has no fresh risk levels


def test_decision_to_row_emits_buy_risk_levels() -> None:
    """Direct unit test of ``_decision_to_row``: synthesize a BUY decision
    (hard to engineer end-to-end on synthetic data) and verify the row
    carries every §15 risk-level field rounded to 4 decimals.
    """
    from saadhana_filter.indicators.conditions import ALL_CONDITIONS
    from saadhana_filter.scan.daily import _decision_to_row
    from saadhana_filter.signals.engine import SignalDecision
    from saadhana_filter.signals.regime import Regime
    from saadhana_filter.signals.risk import RiskLevels
    from saadhana_filter.signals.state import SignalState

    decision = SignalDecision(
        symbol="DIVISLAB",
        signal=SignalState.BUY,
        pro_setup_score=13,
        conditions={name: True for name, _ in ALL_CONDITIONS},
        failed_conditions=(),
        sell_reason=None,
        regime=Regime.RISK_ON,
        tier1_passed=True,
        risk=RiskLevels(
            entry_price=6234.50,
            stop_loss=6075.00,
            target_t1=6546.225,
            target_t2=6857.95,
            risk_pct=0.02560,
            reward_pct=0.05000,
            rr_ratio=1.953,
        ),
        drs=78.4,
        notes=(),
    )
    row = _decision_to_row(decision)
    assert row["symbol"] == "DIVISLAB"
    assert row["signal"] == "BUY"
    assert row["entry_price"] == 6234.5
    assert row["stop_loss"] == 6075.0
    assert row["target_t1"] == 6546.225
    assert row["target_t2"] == 6857.95
    assert row["risk_pct"] == 0.0256
    assert row["reward_pct"] == 0.05
    assert row["rr_ratio"] == 1.953
    assert row["drs"] == 78.4


def test_decision_to_row_skips_risk_levels_for_sell() -> None:
    """SELL rows carry sell_reason but never risk levels — the entry
    happened on a prior scan day, not today."""
    from saadhana_filter.indicators.conditions import ALL_CONDITIONS
    from saadhana_filter.scan.daily import _decision_to_row
    from saadhana_filter.signals.engine import SignalDecision
    from saadhana_filter.signals.regime import Regime
    from saadhana_filter.signals.sell import SellReason
    from saadhana_filter.signals.state import SignalState

    decision = SignalDecision(
        symbol="X",
        signal=SignalState.SELL,
        pro_setup_score=4,
        conditions={name: False for name, _ in ALL_CONDITIONS},
        failed_conditions=tuple(name for name, _ in ALL_CONDITIONS),
        sell_reason=SellReason.STOP_HIT,
        regime=Regime.RISK_ON,
        tier1_passed=True,
        risk=None,
        drs=12.0,
        notes=("sell_trigger:STOP_HIT",),
    )
    row = _decision_to_row(decision)
    assert row["sell_reason"] == "STOP_HIT"
    assert "entry_price" not in row
