"""§4 — Tier 1 fundamental gate tests."""

from __future__ import annotations

import pandas as pd

from saadhana_filter.signals.tier1 import (
    BANK_NBFC_SECTORS,
    is_bank_or_nbfc,
    tier1_filter,
    tier1_gate,
)

# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
PASSING_ROW = {
    "symbol": "DIVISLAB",
    "market_cap_cr": 150_000.0,
    "eps_yoy": 12.0,
    "revenue_yoy": 8.0,
    "promoter_holding_pct": 51.2,
    "promoter_pledge_pct": 0.0,
    "debt_to_equity": 0.12,
    "sector": "PHARMA",
    "fno_banned": False,
    "sebi_surveillance": False,
    "gnpa": 0.0,
    "car": 0.0,
}


def _row(**overrides) -> pd.Series:
    return pd.Series({**PASSING_ROW, **overrides})


# ──────────────────────────────────────────────────────────────────────────
# Sector helper
# ──────────────────────────────────────────────────────────────────────────
def test_is_bank_or_nbfc_recognizes_canonical_sectors() -> None:
    for sector in BANK_NBFC_SECTORS:
        assert is_bank_or_nbfc(sector)
    assert not is_bank_or_nbfc("PHARMA")
    assert not is_bank_or_nbfc("IT")


def test_is_bank_or_nbfc_case_insensitive() -> None:
    assert is_bank_or_nbfc("bank")
    assert is_bank_or_nbfc("Nbfc")


# ──────────────────────────────────────────────────────────────────────────
# tier1_gate — happy path
# ──────────────────────────────────────────────────────────────────────────
class TestTier1GatePassing:
    def test_passing_row_returns_passed(self) -> None:
        res = tier1_gate(_row())
        assert res.passed
        assert res.failed_gates == ()
        assert res.symbol == "DIVISLAB"

    def test_revenue_yoy_alone_satisfies_earnings_gate(self) -> None:
        res = tier1_gate(_row(eps_yoy=-5.0, revenue_yoy=4.0))
        assert res.passed

    def test_eps_yoy_alone_satisfies_earnings_gate(self) -> None:
        res = tier1_gate(_row(eps_yoy=8.0, revenue_yoy=-2.0))
        assert res.passed


# ──────────────────────────────────────────────────────────────────────────
# tier1_gate — individual failure modes
# ──────────────────────────────────────────────────────────────────────────
class TestTier1GateFailures:
    def test_low_market_cap_fails(self) -> None:
        res = tier1_gate(_row(market_cap_cr=2_500.0))
        assert not res.passed
        assert "market_cap_lt_5000_cr" in res.failed_gates

    def test_earnings_shrinkage_fails(self) -> None:
        res = tier1_gate(_row(eps_yoy=-3.0, revenue_yoy=-1.5))
        assert not res.passed
        assert "earnings_shrinkage" in res.failed_gates

    def test_low_promoter_holding_fails(self) -> None:
        res = tier1_gate(_row(promoter_holding_pct=22.0))
        assert "promoter_holding_lt_30pct" in res.failed_gates

    def test_high_pledge_fails(self) -> None:
        res = tier1_gate(_row(promoter_pledge_pct=30.0))
        assert "promoter_pledge_ge_25pct" in res.failed_gates

    def test_high_debt_to_equity_fails_for_non_bank(self) -> None:
        res = tier1_gate(_row(debt_to_equity=2.0))
        assert "debt_to_equity_gt_1_5" in res.failed_gates

    def test_fno_ban_fails(self) -> None:
        res = tier1_gate(_row(fno_banned=True))
        assert "fno_banned" in res.failed_gates

    def test_sebi_surveillance_fails(self) -> None:
        res = tier1_gate(_row(sebi_surveillance=True))
        assert "sebi_surveillance" in res.failed_gates

    def test_market_cap_threshold_inclusive_at_5000(self) -> None:
        # Spec: "≥ 5,000 Cr" — exact boundary should pass
        res = tier1_gate(_row(market_cap_cr=5_000.0))
        assert res.passed

    def test_promoter_holding_threshold_inclusive_at_30(self) -> None:
        res = tier1_gate(_row(promoter_holding_pct=30.0))
        assert res.passed


# ──────────────────────────────────────────────────────────────────────────
# Bank / NBFC alternate gate (§4.1)
# ──────────────────────────────────────────────────────────────────────────
class TestBankNbfcAlternateGate:
    def test_bank_with_clean_metrics_passes(self) -> None:
        res = tier1_gate(
            _row(
                sector="BANK",
                debt_to_equity=10.0,  # banks always have huge D/E — should be ignored
                gnpa=2.0,
                car=14.0,
            )
        )
        assert res.passed

    def test_bank_high_gnpa_fails(self) -> None:
        res = tier1_gate(_row(sector="BANK", gnpa=5.5, car=15.0))
        assert "gnpa_ge_4pct" in res.failed_gates
        assert "debt_to_equity_gt_1_5" not in res.failed_gates  # gate not applied

    def test_bank_low_car_fails(self) -> None:
        res = tier1_gate(_row(sector="NBFC", gnpa=1.0, car=10.0))
        assert "car_lt_12pct" in res.failed_gates

    def test_nonbank_keeps_de_gate(self) -> None:
        res = tier1_gate(_row(sector="PHARMA", debt_to_equity=2.0, gnpa=99.0, car=0.0))
        # GNPA / CAR ignored for non-banks; D/E gate applies
        assert "debt_to_equity_gt_1_5" in res.failed_gates
        assert "gnpa_ge_4pct" not in res.failed_gates


# ──────────────────────────────────────────────────────────────────────────
# tier1_filter (DataFrame application)
# ──────────────────────────────────────────────────────────────────────────
class TestTier1Filter:
    def _frame(self, *rows: dict) -> pd.DataFrame:
        return pd.DataFrame(rows).set_index("symbol")

    def test_filters_out_failures(self) -> None:
        df = self._frame(
            PASSING_ROW,
            {**PASSING_ROW, "symbol": "BAD_MCAP", "market_cap_cr": 1_000.0},
            {**PASSING_ROW, "symbol": "BAD_DE", "debt_to_equity": 3.0},
        )
        out = tier1_filter(df)
        assert "DIVISLAB" in out.index
        assert "BAD_MCAP" not in out.index
        assert "BAD_DE" not in out.index

    def test_empty_frame_returns_empty(self) -> None:
        out = tier1_filter(pd.DataFrame())
        assert out.empty

    def test_does_not_mutate_input(self) -> None:
        df = self._frame(PASSING_ROW)
        before = df.copy()
        tier1_filter(df)
        pd.testing.assert_frame_equal(df, before)
