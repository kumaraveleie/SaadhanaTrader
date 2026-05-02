"""Tests for §14a Scanner cohort registry — Python source of truth.

Per the S1.7 lock decision, the registry is intentionally NOT in
Postgres. These tests assert the in-process invariants the daily
scan relies on (uniqueness, status semantics, lookup correctness).
"""

from __future__ import annotations

import pytest

from saadhana_filter.cohorts import (
    COHORTS,
    CohortSpec,
    get_cohort,
    iter_live_cohorts,
)
from saadhana_filter.cohorts.registry import _enforce_unique_ids


def test_v1_registry_ships_two_cohorts() -> None:
    """Per §14a v1 registry: pro_setup_13 (live) + triple_confluence (validation)."""
    ids = {c.cohort_id for c in COHORTS}
    assert ids == {"pro_setup_13", "triple_confluence"}


def test_pro_setup_inherits_v21_section_05_exclusions() -> None:
    pro = get_cohort("pro_setup_13")
    assert pro.status == "live"
    assert pro.position_size_tier == "STANDARD"
    assert pro.sector_exclusions == ("FINANCIAL_SERVICES", "NBFC", "BANK")


def test_triple_confluence_is_sector_agnostic_pending_s23() -> None:
    """v1 registers triple_confluence with empty sector_exclusions —
    S2.3 backtest decides whether financials need post-hoc exclusion."""
    tc = get_cohort("triple_confluence")
    assert tc.status == "validation"
    assert tc.position_size_tier == "dynamic"
    assert tc.sector_exclusions == ()
    assert tc.g1_baseline_ref is None  # S2.3 will populate


def test_iter_live_cohorts_yields_only_live_or_shadow() -> None:
    """The daily scan iterates only over live + shadow cohorts —
    deferred / validation / paper / retired emit no new signals."""
    live = list(iter_live_cohorts())
    assert [c.cohort_id for c in live] == ["pro_setup_13"]


def test_get_cohort_raises_on_unknown_id() -> None:
    with pytest.raises(KeyError, match="unknown cohort_id"):
        get_cohort("does_not_exist")


def test_duplicate_cohort_id_raises_at_registration() -> None:
    """The §14a edge case 'two registry rows share cohort_id' must
    fail at module import time, not silently allow drift."""
    pro = get_cohort("pro_setup_13")
    duplicate: tuple[CohortSpec, ...] = (pro, pro)
    with pytest.raises(ValueError, match="duplicate cohort_id"):
        _enforce_unique_ids(duplicate)
