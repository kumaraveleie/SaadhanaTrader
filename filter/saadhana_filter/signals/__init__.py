"""§3/§5/§8/§9/§12 — signal engine: BUY/HOLD/SELL/WAIT/WATCH.

Modules:
- ``tier1``               §4 fundamental gate (quarterly)
- ``regime``              §12 market regime classifier (Nifty 50)
- ``sell``                §8 exit triggers for held positions
- ``risk``                §5.4 + §6 + §7 risk levels and Downside Resistance Score
- ``engine``              §3/§5/§9 orchestration: combines everything into a decision
- ``state``               enums and dataclasses shared across modules
- ``triple_confluence``   §5.10 cohort candidate function
"""

from saadhana_filter.signals.engine import SignalDecision, classify_signal
from saadhana_filter.signals.regime import Regime, market_regime
from saadhana_filter.signals.risk import (
    RiskLevels,
    downside_resistance_score,
    risk_levels,
)
from saadhana_filter.signals.sell import Position, SellReason, evaluate_sell
from saadhana_filter.signals.state import SignalState
from saadhana_filter.signals.tier1 import (
    Tier1Result,
    is_bank_or_nbfc,
    tier1_filter,
    tier1_gate,
)
from saadhana_filter.signals.triple_confluence import (
    TripleConfluenceResult,
    candidate_triple_confluence,
)

__all__ = [
    "Position",
    "Regime",
    "RiskLevels",
    "SellReason",
    "SignalDecision",
    "SignalState",
    "Tier1Result",
    "TripleConfluenceResult",
    "candidate_triple_confluence",
    "classify_signal",
    "downside_resistance_score",
    "evaluate_sell",
    "is_bank_or_nbfc",
    "market_regime",
    "risk_levels",
    "tier1_filter",
    "tier1_gate",
]
