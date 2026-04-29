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
