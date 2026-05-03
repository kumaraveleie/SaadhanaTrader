"""Tests for Sec.6.4 Tier 2 Quality Score (Diamond Layer 3).

v0 covers the 5 buildable checks against the Tier 1 columns; canonical
covers the §14.1 6-check version (when data lands). Both are tested
here so the module is correct under both variants."""

from __future__ import annotations

import pandas as pd
import pytest

from saadhana_filter.quality.tier2 import (
    compute_tier2_score,
    tier2_filter,
)


# ──────────────────────────────────────────────────────────────────
# v0 fixtures — 5-check variant against current fundamentals columns
# ──────────────────────────────────────────────────────────────────
def _v0_row(**overrides) -> pd.Series:
    """Build a Tier 1-shape fundamentals row that PASSES all 5 v0
    checks unless overridden. Sector defaults to non-bank so D/E gate
    is the active 5th check."""
    base = {
        "sector": "Healthcare",
        "eps_yoy": 12.0,
        "revenue_yoy": 8.0,
        "promoter_holding_pct": 55.0,
        "promoter_pledge_pct": 0.0,
        "debt_to_equity": 0.4,
    }
    base.update(overrides)
    return pd.Series(base)


def test_v0_all_five_pass_returns_5():
    row = _v0_row()
    assert compute_tier2_score(row, version="v0") == 5


def test_v0_eps_yoy_zero_fails():
    row = _v0_row(eps_yoy=0.0)
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_negative_revenue_fails():
    row = _v0_row(revenue_yoy=-5.0)
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_promoter_holding_below_40_fails():
    row = _v0_row(promoter_holding_pct=39.0)
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_promoter_pledge_above_zero_fails():
    """Tier 2 v0 requires zero pledge — strictly tighter than Tier 1."""
    row = _v0_row(promoter_pledge_pct=0.5)
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_debt_equity_above_one_fails():
    """Tier 2 v0 D/E threshold = 1.0; Tier 1's was 1.5."""
    row = _v0_row(debt_to_equity=1.2)
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_minimum_score_zero():
    row = _v0_row(
        eps_yoy=-1.0,
        revenue_yoy=-1.0,
        promoter_holding_pct=10.0,
        promoter_pledge_pct=15.0,
        debt_to_equity=2.0,
    )
    assert compute_tier2_score(row, version="v0") == 0


# ──────────────────────────────────────────────────────────────────
# Bank/NBFC §4.1 swap — D/E check replaced by GNPA + CAR pair
# ──────────────────────────────────────────────────────────────────
def test_v0_bank_uses_gnpa_car_swap_passing():
    """Banks pass the 5th check when GNPA ≤ 4 AND CAR ≥ 12."""
    row = _v0_row(
        sector="BANK",
        debt_to_equity=8.0,  # absurdly high — would fail D/E for non-bank
        gnpa=2.0,
        car=15.0,
    )
    assert compute_tier2_score(row, version="v0") == 5


def test_v0_bank_high_gnpa_fails_5th_check():
    row = _v0_row(
        sector="NBFC",
        debt_to_equity=8.0,
        gnpa=5.0,  # > 4% threshold
        car=15.0,
    )
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_bank_low_car_fails_5th_check():
    row = _v0_row(
        sector="FINANCIAL_SERVICES",
        debt_to_equity=8.0,
        gnpa=2.0,
        car=10.0,  # < 12% threshold
    )
    assert compute_tier2_score(row, version="v0") == 4


# ──────────────────────────────────────────────────────────────────
# tier2_filter — DataFrame-level filter
# ──────────────────────────────────────────────────────────────────
def test_tier2_filter_default_threshold_keeps_score_4_and_above():
    df = pd.DataFrame([
        _v0_row().to_dict(),                       # score 5
        _v0_row(eps_yoy=0).to_dict(),              # score 4
        _v0_row(eps_yoy=0, revenue_yoy=-1).to_dict(),  # score 3
    ])
    out = tier2_filter(df, threshold=4, version="v0")
    assert len(out) == 2


def test_tier2_filter_strict_threshold_keeps_only_perfect():
    df = pd.DataFrame([
        _v0_row().to_dict(),
        _v0_row(eps_yoy=0).to_dict(),
        _v0_row(eps_yoy=0, revenue_yoy=-1).to_dict(),
    ])
    out = tier2_filter(df, threshold=5, version="v0")
    assert len(out) == 1


# ──────────────────────────────────────────────────────────────────
# Canonical — §14.1 6-check version (when data lands)
# ──────────────────────────────────────────────────────────────────
def _canonical_row(**overrides) -> pd.Series:
    """Build a row that PASSES all 6 canonical checks unless overridden."""
    base = {
        "roe_3y_avg": 18.0,
        "roce_3y_avg": 22.0,
        "earnings_cagr_3y": 20.0,
        "fcf_4q_positive": True,
        "promoter_buying_6m": True,
        "fii_dii_qoq_rising": True,
    }
    base.update(overrides)
    return pd.Series(base)


def test_canonical_all_six_pass_returns_6():
    row = _canonical_row()
    assert compute_tier2_score(row, version="canonical") == 6


def test_canonical_low_roe_fails():
    row = _canonical_row(roe_3y_avg=14.0)  # ≤ 15% threshold
    assert compute_tier2_score(row, version="canonical") == 5


def test_canonical_negative_fcf_fails():
    row = _canonical_row(fcf_4q_positive=False)
    assert compute_tier2_score(row, version="canonical") == 5


def test_canonical_minimum_score_zero():
    row = _canonical_row(
        roe_3y_avg=0,
        roce_3y_avg=0,
        earnings_cagr_3y=0,
        fcf_4q_positive=False,
        promoter_buying_6m=False,
        fii_dii_qoq_rising=False,
    )
    assert compute_tier2_score(row, version="canonical") == 0


# ──────────────────────────────────────────────────────────────────
# Auto version selection — picks canonical when columns present
# ──────────────────────────────────────────────────────────────────
def test_auto_picks_canonical_when_all_columns_present():
    row = _canonical_row()
    assert compute_tier2_score(row, version="auto") == 6


def test_auto_falls_back_to_v0_when_canonical_columns_missing():
    row = _v0_row()  # no canonical columns
    assert compute_tier2_score(row, version="auto") == 5


# ──────────────────────────────────────────────────────────────────
# Edge — NaN columns are treated as failed checks
# ──────────────────────────────────────────────────────────────────
def test_v0_nan_column_fails_check():
    row = _v0_row(eps_yoy=float("nan"))
    assert compute_tier2_score(row, version="v0") == 4


def test_v0_missing_column_fails_check():
    """Pandas .get() returns None for missing keys — that should be
    treated as a failed check (no upgrade)."""
    row = pd.Series({
        "sector": "Healthcare",
        "eps_yoy": 5.0,
        "revenue_yoy": 5.0,
        "promoter_holding_pct": 50.0,
        "promoter_pledge_pct": 0.0,
        # debt_to_equity intentionally absent
    })
    score = compute_tier2_score(row, version="v0")
    assert score == 4
