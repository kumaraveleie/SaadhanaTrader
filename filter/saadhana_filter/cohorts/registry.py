"""§14a Scanner cohort registry — v1 ships 2 of 10 cohorts.

The registry is intentionally NOT a DB table (see §14a + §17.3). It
stays as Python source so changes route through spec → code → §19
review, never through a runtime toggle.

Adding a cohort: append a ``CohortSpec`` to :data:`COHORTS`, ensure
the ``cohort_id`` is unique, and confirm ``candidate_fn`` resolves at
import time. The module-level uniqueness check fires on import — a
duplicate ``cohort_id`` raises immediately, so the daily scan will
refuse to start (per §14a edge case).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Literal

CohortStatus = Literal[
    "spec", "deferred", "validation", "shadow", "paper", "live", "retired", "paused"
]
PositionSizeTier = Literal["STANDARD", "HIGH", "dynamic"]
ValidationGate = Literal["G1", "G2", "F", "paper", "live"]
Instrument = Literal["equity", "etf", "index_future"]
Horizon = Literal["intraday", "swing", "position"]
Timeframe = Literal["5min", "15min", "60min", "daily", "weekly"]


@dataclass(frozen=True)
class CohortSpec:
    """A single row in the §14a cohort registry. Frozen — mutation
    requires a new dataclass instance, mirroring the spec→code→review
    discipline."""

    cohort_id: str
    display_name: str
    description: str
    instrument: Instrument
    horizon: Horizon
    source: str
    candidate_fn: str
    entry_logic: str
    exit_logic: str
    timeframes_supported: tuple[Timeframe, ...] = ("daily",)
    sector_exclusions: tuple[str, ...] = field(default_factory=tuple)
    position_size_tier: PositionSizeTier = "STANDARD"
    validation_gate: ValidationGate = "G1"
    status: CohortStatus = "deferred"
    diamond_eligible: bool = False
    g1_baseline_ref: str | None = None


COHORTS: tuple[CohortSpec, ...] = (
    CohortSpec(
        cohort_id="pro_setup_13",
        display_name="Pro-setup 13/13",
        description=(
            "Strict-AND of 13 BUY conditions per §5; sector_exclusions "
            "migrate from the v2.1 §0.5 amendment."
        ),
        instrument="equity",
        horizon="swing",
        timeframes_supported=("daily",),
        source="Sec.5",
        candidate_fn="saadhana_filter.signals.candidate_pro_setup_13",
        entry_logic="all 13 BUY conditions True",
        exit_logic="§25 Tier 1 (hard stop / target ladder / score collapse)",
        sector_exclusions=("FINANCIAL_SERVICES", "NBFC", "BANK"),
        position_size_tier="STANDARD",
        validation_gate="G1",
        status="live",
        diamond_eligible=False,
        g1_baseline_ref="spec/samples/backtest_report_g1_investquest_universe.md",
    ),
    CohortSpec(
        cohort_id="triple_confluence",
        display_name="Triple confluence",
        description=(
            "2-of-3 / 3-of-3 agreement across MA crossover, Adaptive "
            "SuperTrend, Deviation Trend (Sec.5.10)."
        ),
        instrument="equity",
        horizon="position",
        timeframes_supported=("daily",),
        source="Sec.5.10",
        candidate_fn="saadhana_filter.signals.candidate_triple_confluence",
        entry_logic="≥ 2 components qualified bullish on same scan bar",
        exit_logic="§25 Tier 2 (component decay watchlist; 0-of-3 = exit)",
        sector_exclusions=(),
        position_size_tier="dynamic",
        validation_gate="paper",
        status="validation",
        diamond_eligible=True,
        g1_baseline_ref=None,
    ),
    CohortSpec(
        cohort_id="nifty_intraday_algo",
        display_name="Nifty intraday algo (5-min, futures)",
        description=(
            "Externally-sourced 5-minute Nifty futures algo. Placeholder "
            "registered to fix the cohort_id and lock the schema; "
            "status='spec' means no candidate_fn yet. Activation sequence: "
            "(1) 5-min futures data infrastructure (Wave X), (2) cohort "
            "implementation, (3) walk-forward parameter optimisation, "
            "(4) real-data backtest validation, (5) shadow → paper → live. "
            "Not promoted on simulated-data reports alone. See §14a "
            "deferred-cohorts table for evidence."
        ),
        instrument="index_future",
        horizon="intraday",
        timeframes_supported=("5min",),
        source="external",
        candidate_fn="(deferred — no implementation yet)",
        entry_logic="(deferred)",
        exit_logic="(deferred — daily circuit breaker per §10.5)",
        sector_exclusions=(),
        position_size_tier="STANDARD",
        validation_gate="G1",
        status="spec",
        diamond_eligible=False,
        g1_baseline_ref=None,
    ),
)


def _enforce_unique_ids(cohorts: tuple[CohortSpec, ...]) -> None:
    seen: set[str] = set()
    for c in cohorts:
        if c.cohort_id in seen:
            raise ValueError(
                f"duplicate cohort_id in §14a registry: {c.cohort_id!r} — "
                "daily scan refuses to start until resolved"
            )
        seen.add(c.cohort_id)


def _enforce_timeframes_declared(cohorts: tuple[CohortSpec, ...]) -> None:
    """Reject empty ``timeframes_supported`` at import time per §14a.4.

    A cohort with no declared timeframes has no validated bar
    resolution to run on; signals it would emit have never been
    backtested. Treat it the same as a duplicate cohort_id — daily
    scan refuses to start.
    """
    for c in cohorts:
        if not c.timeframes_supported:
            raise ValueError(
                f"cohort {c.cohort_id!r}: timeframes_supported is empty — "
                "§14a.4 requires at least one declared bar resolution"
            )


_enforce_unique_ids(COHORTS)
_enforce_timeframes_declared(COHORTS)


def get_cohort(cohort_id: str) -> CohortSpec:
    """Return the registered cohort spec for ``cohort_id``.

    Raises ``KeyError`` if not registered — callers should treat this
    as a programming error (signals are emitted only by registered
    cohorts).
    """
    for c in COHORTS:
        if c.cohort_id == cohort_id:
            return c
    raise KeyError(f"unknown cohort_id: {cohort_id!r}")


def iter_live_cohorts() -> Iterator[CohortSpec]:
    """Yield only cohorts currently in ``live`` or ``shadow`` status —
    the daily scan filters on this so paused/retired cohorts emit no
    new signals (existing positions continue under §25 Position Monitor).
    """
    for c in COHORTS:
        if c.status in ("live", "shadow"):
            yield c
