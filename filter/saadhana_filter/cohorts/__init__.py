"""§14a Scanner cohort registry — Python is the single source of truth.

Per §14a + the S1.7 lock decision, cohort definitions live as
checked-in source code, NOT as runtime DB rows. Changes go through
spec → code → §19 candidate-rule review.
"""

from saadhana_filter.cohorts.registry import (
    COHORTS,
    CohortSpec,
    CohortStatus,
    PositionSizeTier,
    ValidationGate,
    get_cohort,
    iter_live_cohorts,
)

__all__ = [
    "COHORTS",
    "CohortSpec",
    "CohortStatus",
    "PositionSizeTier",
    "ValidationGate",
    "get_cohort",
    "iter_live_cohorts",
]
