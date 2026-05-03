"""Quality / confirmation modules layered on top of cohort signals.

The Diamond stack (§0.7.5) composes cohort base signals with
discipline filters. This package houses the discipline-side modules:

  - ``confirmation_score`` (Sec.0.7.6, candidate Layer 7 of Diamond):
    5-point post-hoc score combining RSI / ADX / VWAP / MACD / BB-mid
    confirmations on the entry bar. Filters cohort signals to those
    where multiple independent indicators agree on direction.
"""

from saadhana_filter.quality.confirmation_score import (
    ConfirmationScoreResult,
    compute_confirmation_score,
)

__all__ = [
    "ConfirmationScoreResult",
    "compute_confirmation_score",
]
