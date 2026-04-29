"""§15 — daily scan runner.

Reads the Tier 1 fundamentals snapshot, classifies the regime on the
Nifty 50 index, then loops through the universe and emits one
``SignalDecision`` per symbol. The output mirrors §15 exactly so the
Vercel ``scan_results`` table and the public scanner page can read
the JSON unchanged.

Pure compute: no yfinance calls inside the scan path. Tests inject
``ohlcv_provider`` and ``index_df`` so we never hit the network.
``scripts/daily_scan.py`` (the CLI) is the thin wrapper that pulls
data first and then calls into ``run_scan``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import date
from typing import TypedDict

import pandas as pd

from saadhana_filter import __spec_version__
from saadhana_filter.scan.universe import NIFTY_50
from saadhana_filter.signals import (
    Position,
    SignalDecision,
    SignalState,
    classify_signal,
)
from saadhana_filter.signals.regime import Regime, latest_regime
from saadhana_filter.signals.tier1 import tier1_filter

# Symbols held today: the ledger writer (Phase H) populates this dict.
# For Phase C the map is passed in directly so the engine can be
# exercised with synthetic positions.
PositionMap = Mapping[str, Position]
OHLCVProvider = Callable[[str], pd.DataFrame]


class CandidateRow(TypedDict, total=False):
    """Per-symbol entry in the §15 ``candidates`` array.

    BUY rows carry the §5.4 risk levels; HOLD/SELL rows carry the
    sell_reason if any; WAIT rows are dropped from the candidates
    list (they are millions and not displayed per §3 / §15).
    """

    symbol: str
    signal: str
    pro_setup_score: int
    drs: float
    regime: str
    tier1_passed: bool
    failed_conditions: list[str]
    notes: list[str]
    sell_reason: str | None
    entry_price: float
    stop_loss: float
    target_t1: float
    target_t2: float
    risk_pct: float
    reward_pct: float
    rr_ratio: float


def run_scan(
    *,
    scan_date: date,
    universe: tuple[str, ...] = NIFTY_50,
    fundamentals: pd.DataFrame,
    nifty_df: pd.DataFrame,
    ohlcv_provider: OHLCVProvider,
    positions: PositionMap | None = None,
) -> dict:
    """Run a full §15 scan. Returns a JSON-serializable dict.

    Parameters
    ----------
    scan_date
        Wall-clock date of the scan (UTC date is fine — Indian markets
        close at 15:30 IST = 10:00 UTC, so any UTC date after that
        names the same trading session).
    universe
        Tuple of NSE-convention symbols.
    fundamentals
        DataFrame indexed by symbol with the Tier 1 columns from §4.
    nifty_df
        Daily OHLCV for the Nifty 50 index, used to compute §12 regime.
    ohlcv_provider
        Callable ``(symbol) -> DataFrame`` returning that symbol's
        cached daily OHLCV. Phase M wires this to the data loader's
        Parquet cache.
    positions
        Optional ``{symbol: Position}`` map of currently-held names
        (read from the ledger). Held names always evaluate via the
        §8 SELL branch — Tier 1 failures don't force-close positions.
    """
    positions = positions or {}
    regime = latest_regime(nifty_df)
    tier1_pass = tier1_filter(fundamentals)
    tier1_passed_symbols = set(tier1_pass.index.astype(str))

    candidates: list[CandidateRow] = []
    decisions: list[SignalDecision] = []

    for symbol in universe:
        try:
            df = ohlcv_provider(symbol)
        except Exception as exc:  # noqa: BLE001 — scan is best-effort per symbol
            decisions.append(_synthesize_skip(symbol, regime, str(exc)))
            continue

        if df.empty:
            decisions.append(_synthesize_skip(symbol, regime, "empty_ohlcv"))
            continue

        position = positions.get(symbol)
        # Held names with Tier 1 failures still need exit evaluation:
        # close-out is governed by §8, not by §4 fundamentals.
        tier1_passed = symbol in tier1_passed_symbols or position is not None

        decision = classify_signal(
            df,
            symbol=symbol,
            tier1_passed=tier1_passed,
            regime=regime,
            position=position,
        )
        decisions.append(decision)
        if decision.signal != SignalState.WAIT:
            candidates.append(_decision_to_row(decision))

    return {
        "scan_date": scan_date.isoformat(),
        "spec_version": __spec_version__,
        "regime": regime.value,
        "universe_size": len(universe),
        "tier1_passed": len(tier1_passed_symbols),
        "candidates": candidates,
    }


def _decision_to_row(decision: SignalDecision) -> CandidateRow:
    row: CandidateRow = {
        "symbol": decision.symbol,
        "signal": decision.signal.value,
        "pro_setup_score": decision.pro_setup_score,
        "drs": round(decision.drs, 1),
        "regime": decision.regime.value,
        "tier1_passed": decision.tier1_passed,
        "failed_conditions": list(decision.failed_conditions),
        "notes": list(decision.notes),
        "sell_reason": decision.sell_reason.value if decision.sell_reason else None,
    }
    if decision.risk is not None:
        risk_dict = asdict(decision.risk)
        for k in (
            "entry_price",
            "stop_loss",
            "target_t1",
            "target_t2",
            "risk_pct",
            "reward_pct",
            "rr_ratio",
        ):
            row[k] = round(risk_dict[k], 4)  # type: ignore[literal-required]
    return row


def _synthesize_skip(symbol: str, regime: Regime, reason: str) -> SignalDecision:
    """Skipped symbols still get a placeholder decision so forensics can
    distinguish "data missing" from "WAIT because score < 10".
    """
    from saadhana_filter.indicators.conditions import ALL_CONDITIONS

    return SignalDecision(
        symbol=symbol,
        signal=SignalState.WAIT,
        pro_setup_score=0,
        conditions={name: False for name, _ in ALL_CONDITIONS},
        failed_conditions=tuple(name for name, _ in ALL_CONDITIONS),
        sell_reason=None,
        regime=regime,
        tier1_passed=False,
        risk=None,
        drs=0.0,
        notes=(f"skipped:{reason}",),
    )


def scan_to_json(result: dict, *, indent: int = 2) -> str:
    """Serialize the scan result as JSON. Convenience wrapper around
    ``json.dumps`` with ``default=str`` for any stray date objects."""
    return json.dumps(result, indent=indent, default=str)
