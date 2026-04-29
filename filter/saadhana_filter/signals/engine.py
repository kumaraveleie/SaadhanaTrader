"""§3/§5/§9 — orchestrator that turns all the pieces into one decision.

Inputs:
- ``df``           per-symbol daily OHLCV (≥ 252 bars for full lookback)
- ``tier1_passed`` whether the §4 fundamentals gate cleared this quarter
- ``regime``       §12 market regime on the current scan date
- ``position``     §17 ledger position snapshot (or ``None`` if not held)

Output: a ``SignalDecision`` carrying the §3 state, the per-condition
verdicts, the §6 Downside Resistance Score and (for BUY/HOLD) the
§5.4 / §7 risk-level levels.

Decision tree (held vs not-held branches are kept independent so the
ledger writer in Phase H can audit which leaf fired):
::

    held? ──yes──► evaluate_sell                         §8
              │      hit?  ─yes─► SELL  (sell_reason)
              │      no       ► HOLD
              └─no──► tier1_passed AND regime ≠ RISK_OFF?
                        │
                        no  ──► WAIT (failed_gates explains why)
                        yes ──► score == 13          → BUY  + risk_levels
                                score 10..12         → WATCH
                                score < 10           → WAIT
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from saadhana_filter.indicators.conditions import ALL_CONDITIONS, pro_setup_score
from saadhana_filter.signals.regime import Regime
from saadhana_filter.signals.risk import (
    RiskLevels,
    downside_resistance_score,
    risk_levels,
)
from saadhana_filter.signals.sell import Position, SellReason, evaluate_sell
from saadhana_filter.signals.state import SignalState

# Score thresholds per §5
BUY_SCORE = 13
WATCH_MIN_SCORE = 10
CAUTION_MIN_SCORE = 13  # §12 — Caution regime requires perfect score


@dataclass(frozen=True)
class SignalDecision:
    """Full per-symbol decision emitted on a given scan date."""

    symbol: str
    signal: SignalState
    pro_setup_score: int
    conditions: dict[str, bool]
    failed_conditions: tuple[str, ...]
    sell_reason: SellReason | None
    regime: Regime
    tier1_passed: bool
    risk: RiskLevels | None
    drs: float
    notes: tuple[str, ...] = field(default_factory=tuple)


def classify_signal(
    df: pd.DataFrame,
    *,
    symbol: str,
    tier1_passed: bool,
    regime: Regime,
    position: Position | None = None,
) -> SignalDecision:
    """Run the full §3/§5/§8/§9/§12 decision tree on one symbol.

    The function is deterministic: same inputs → same output. It does
    not write to disk and does not call yfinance. The scan entrypoint
    (Phase C, ``scan/daily.py``) loops this over the universe.
    """
    score_df = pro_setup_score(df)
    last = score_df.iloc[-1]
    score = int(last["score"])
    cond_map = {name: bool(last[name]) for name, _ in ALL_CONDITIONS}
    failed = tuple(name for name, met in cond_map.items() if not met)

    drs = downside_resistance_score(df)

    # ────────────── held positions branch (§8 / §9) ──────────────
    if position is not None:
        sell_reason = evaluate_sell(df, position)
        if sell_reason is not None:
            return SignalDecision(
                symbol=symbol,
                signal=SignalState.SELL,
                pro_setup_score=score,
                conditions=cond_map,
                failed_conditions=failed,
                sell_reason=sell_reason,
                regime=regime,
                tier1_passed=tier1_passed,
                risk=None,
                drs=drs,
                notes=(f"sell_trigger:{sell_reason.value}",),
            )
        return SignalDecision(
            symbol=symbol,
            signal=SignalState.HOLD,
            pro_setup_score=score,
            conditions=cond_map,
            failed_conditions=failed,
            sell_reason=None,
            regime=regime,
            tier1_passed=tier1_passed,
            risk=None,
            drs=drs,
        )

    # ────────────── unheld branch (§3 entry decision) ──────────────
    notes: list[str] = []
    if not tier1_passed:
        notes.append("tier1_failed")
    if regime == Regime.RISK_OFF:
        notes.append("regime_risk_off")

    can_buy = tier1_passed and regime != Regime.RISK_OFF
    # §12 Caution regime — only Score 13 + HIGH conviction qualifies.
    # HIGH conviction is §14 (Phase F); for Phase C, Caution allows BUY
    # at score == 13 and surfaces a note so Phase F can tighten it.
    min_score_for_buy = CAUTION_MIN_SCORE if regime == Regime.CAUTION else BUY_SCORE

    risk: RiskLevels | None = None
    state: SignalState
    if can_buy and score >= min_score_for_buy:
        state = SignalState.BUY
        risk = risk_levels(df)
        if regime == Regime.CAUTION:
            notes.append("caution_regime_buy_pending_§14_conviction_check")
    elif can_buy and WATCH_MIN_SCORE <= score < BUY_SCORE:
        state = SignalState.WATCH
    else:
        state = SignalState.WAIT

    return SignalDecision(
        symbol=symbol,
        signal=state,
        pro_setup_score=score,
        conditions=cond_map,
        failed_conditions=failed,
        sell_reason=None,
        regime=regime,
        tier1_passed=tier1_passed,
        risk=risk,
        drs=drs,
        notes=tuple(notes),
    )
