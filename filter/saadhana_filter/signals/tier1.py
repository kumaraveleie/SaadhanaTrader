"""§4 — Tier 1 fundamental gate.

Refreshed once per quarter (90 days). A symbol must pass **all** gates
to enter the daily technical scan; failures cause the symbol to be
skipped entirely no matter how strong the chart looks. The gate also
forms the §17 ledger snapshot's fundamentals block.

Banks, NBFCs and financial-services issuers swap the D/E gate for
balance-sheet-quality gates (GNPA / CAR) per §4.1.

Input contract — a ``pd.DataFrame`` with at least these columns:

| Column                | Type   | Notes                                |
|-----------------------|--------|--------------------------------------|
| symbol                | str    | NSE convention; used as the index    |
| market_cap_cr         | float  | crores INR                           |
| eps_yoy               | float  | percent change YoY (e.g. 12.4)       |
| revenue_yoy           | float  | percent change YoY                   |
| promoter_holding_pct  | float  | 0..100                               |
| promoter_pledge_pct   | float  | 0..100                               |
| debt_to_equity        | float  | unitless                             |
| sector                | str    | uppercase, e.g. ``PHARMA``, ``BANK`` |
| fno_banned            | bool   | F&O ban list on scan date            |
| sebi_surveillance     | bool   | T-group / GSM 3+ / suspended / ASM   |
| gnpa                  | float  | percent (banks/NBFCs only)           |
| car                   | float  | percent (banks/NBFCs only)           |
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# ──────────────────────────────────────────────────────────────────────────
# Spec constants (§4)
# ──────────────────────────────────────────────────────────────────────────
MIN_MARKET_CAP_CR = 5_000.0
MIN_PROMOTER_HOLDING_PCT = 30.0
MAX_PROMOTER_PLEDGE_PCT = 25.0
MAX_DEBT_TO_EQUITY = 1.5
MAX_GNPA_PCT = 4.0
MIN_CAR_PCT = 12.0

BANK_NBFC_SECTORS: frozenset[str] = frozenset({"BANK", "NBFC", "FINANCIAL_SERVICES"})


@dataclass(frozen=True)
class Tier1Result:
    """Result of the Tier 1 gate evaluation for a single symbol.

    ``failed_gates`` carries the canonical gate identifiers that failed,
    so forensics can later cluster which fundamental gate disqualifies
    candidates most often.
    """

    symbol: str
    passed: bool
    failed_gates: tuple[str, ...]


def is_bank_or_nbfc(sector: str) -> bool:
    """Return True if the sector falls under §4.1's alternate gate."""
    return sector.upper() in BANK_NBFC_SECTORS


def tier1_gate(row: pd.Series) -> Tier1Result:
    """§4 — apply the fundamental gates to one symbol's row.

    Returns a ``Tier1Result`` carrying ``passed`` plus the names of any
    failed gates. Order of evaluation is the spec order so the ``most
    significant first`` failure shows up at index 0.
    """
    failed: list[str] = []
    symbol = str(row["symbol"]) if "symbol" in row.index else str(row.name)

    if row["market_cap_cr"] < MIN_MARKET_CAP_CR:
        failed.append("market_cap_lt_5000_cr")

    if not (row["eps_yoy"] > 0.0 or row["revenue_yoy"] > 0.0):
        failed.append("earnings_shrinkage")

    if row["promoter_holding_pct"] < MIN_PROMOTER_HOLDING_PCT:
        failed.append("promoter_holding_lt_30pct")

    if row["promoter_pledge_pct"] >= MAX_PROMOTER_PLEDGE_PCT:
        failed.append("promoter_pledge_ge_25pct")

    if is_bank_or_nbfc(str(row["sector"])):
        # §4.1 alternate gate: replace D/E with GNPA + CAR
        if row["gnpa"] >= MAX_GNPA_PCT:
            failed.append("gnpa_ge_4pct")
        if row["car"] < MIN_CAR_PCT:
            failed.append("car_lt_12pct")
    else:
        if row["debt_to_equity"] > MAX_DEBT_TO_EQUITY:
            failed.append("debt_to_equity_gt_1_5")

    if bool(row["fno_banned"]):
        failed.append("fno_banned")

    if bool(row["sebi_surveillance"]):
        failed.append("sebi_surveillance")

    return Tier1Result(symbol=symbol, passed=len(failed) == 0, failed_gates=tuple(failed))


def tier1_filter(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Apply the Tier 1 gate to every row, return only the passing rows.

    The input frame is **not** mutated; a copy of the surviving rows is
    returned with the same column set so downstream code can read both
    fundamentals and the symbol identity.
    """
    if fundamentals.empty:
        return fundamentals.copy()

    if "symbol" in fundamentals.columns:
        results = [tier1_gate(row) for _, row in fundamentals.iterrows()]
    else:
        # Symbol comes from the index
        results = [tier1_gate(row) for _, row in fundamentals.iterrows()]

    mask = pd.Series(
        [r.passed for r in results],
        index=fundamentals.index,
        dtype=bool,
    )
    return fundamentals.loc[mask].copy()
