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
from saadhana_filter.cohorts.registry import (
    _enforce_timeframes_declared,
    _enforce_unique_ids,
)


def test_v1_registry_ships_two_cohorts() -> None:
    """Per §14a v1 registry: pro_setup_13 (live) + triple_confluence
    (validation). Plus nifty_intraday_algo placeholder (status='spec',
    no candidate_fn — registered to lock the slot per §14a Wave 8+ note).
    The 'shipping' cohorts are the two with concrete candidate_fns; the
    placeholder doesn't ship signals.
    """
    ids = {c.cohort_id for c in COHORTS}
    assert ids == {"pro_setup_13", "triple_confluence", "nifty_intraday_algo"}
    shipping = {
        c.cohort_id for c in COHORTS if c.status not in ("spec", "deferred", "retired")
    }
    assert shipping == {"pro_setup_13", "triple_confluence"}


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


# ──────────────────────────────────────────────────────────────────
# §14a.4 timeframe suitability + §0.7.5 Diamond eligibility
# ──────────────────────────────────────────────────────────────────
def test_v1_cohorts_declare_daily_timeframe() -> None:
    """v1 SHIPPING cohorts declare ``['daily']`` per §14a.4. The
    ``nifty_intraday_algo`` placeholder declares ``['5min']`` because
    its eventual cohort runs on intraday futures bars; that's allowed
    because its status is 'spec' (no signals emitted yet)."""
    for c in COHORTS:
        if c.status == "spec":
            continue  # placeholder; doesn't emit signals
        assert c.timeframes_supported == ("daily",), (
            f"{c.cohort_id} timeframes_supported drifted from v1 lock"
        )


def test_diamond_eligibility_matches_spec_v1_lock() -> None:
    """Per §0.7.5, only Triple confluence is diamond_eligible in v1 —
    its 3-of-3 state naturally maps to the recipe's component-1.
    Pro-setup 13/13 needs a per-cohort Diamond mapping spec'd before
    flipping its flag."""
    assert get_cohort("pro_setup_13").diamond_eligible is False
    assert get_cohort("triple_confluence").diamond_eligible is True


def test_empty_timeframes_supported_raises_at_import() -> None:
    """Per §14a.4, an empty ``timeframes_supported`` list is rejected
    at import time so the daily scan refuses to start."""
    pro = get_cohort("pro_setup_13")
    bad = CohortSpec(
        cohort_id="pro_setup_13_no_tf",
        display_name="(test)",
        description="(test)",
        instrument=pro.instrument,
        horizon=pro.horizon,
        timeframes_supported=(),
        source=pro.source,
        candidate_fn=pro.candidate_fn,
        entry_logic=pro.entry_logic,
        exit_logic=pro.exit_logic,
    )
    with pytest.raises(ValueError, match="timeframes_supported is empty"):
        _enforce_timeframes_declared((bad,))
