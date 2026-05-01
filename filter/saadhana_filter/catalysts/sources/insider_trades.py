"""§13.1 source 4: SEBI insider trading disclosure classifier.

SEBI / BSE Reg 7(2) requires disclosure of insider trades within 2
trading days. Phase D1 ships fixture-backed; Phase D2 swaps in the
live SEBI scraper.

Roles classified (insider names normalised):
  - ``promoter``       — strongest signal when buying
  - ``director``       — board director (non-promoter)
  - ``kmp``            — Key Managerial Personnel (CFO, CS, etc.)
  - ``employee``       — designated employees (weakest signal)

Catalyst types (existing taxonomy + Source-3 extensions):
  - ``promoter_buying``  (promoter open-market buy)
  - ``promoter_selling`` (promoter sell — cautionary)
  - ``insider_buying``   (director / KMP / employee buy)

Director / KMP / employee SELL trades drop — frequent ESOP exit
pattern is noise; only promoter_selling cautionary signal surfaces.

Filter rules:
  - ``value_cr >= 1`` (skip tiny grants, cancellations)
  - role classified to one of the four above
  - For sell-side, only ``promoter`` role surfaces; others drop

Freshness: FRESH ≤ 14d, RECENT 15..60d, STALE >60d (drop).

Magnitude (deterministic, 0..10)::

    role_weight = {promoter: 10, director: 6, kmp: 4, employee: 2}[role]
    base = min(10, value_cr * 2)
    cluster_boost = 1.5 if symbol has ≥ 2 in-window net-buy
                         disclosures (any role), else 1.0
    magnitude = round(base * (role_weight / 10) * cluster_boost)
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from saadhana_filter.catalysts.types import (
    Catalyst,
    CatalystType,
    freshness_for,
)

DEFAULT_FIXTURE_PATH = Path("data/catalysts/insider_trades_fixture.json")
DEFAULT_LOOKBACK_DAYS = 60
MIN_VALUE_CR = 1.0
FRESH_DAYS = 14
RECENT_DAYS = 60
CLUSTER_BOOST = 1.5

ROLE_WEIGHTS: dict[str, int] = {
    "promoter": 10,
    "director": 6,
    "kmp": 4,
    "employee": 2,
}

InsiderTradesFetcher = Callable[[date], list[dict]]
"""Returns a list of records, each with the fields the classifier needs.

Record shape:
    {
        "symbol": "JSWENERGY",
        "trade_date": "2026-04-23",       # YYYY-MM-DD
        "insider_name": "Sajjan Jindal",
        "role": "promoter",                # promoter / director / kmp / employee
        "action": "BUY" | "SELL",
        "value_cr": 12.0,                  # crore rupees, NET (excludes ESOP exercises)
        "is_esop_exercise": false,         # true → drop
        "source_url": "https://...",
    }
"""


def fixture_fetcher(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> InsiderTradesFetcher:
    def fetch(today: date) -> list[dict]:
        if not fixture_path.exists():
            return []
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        return list(raw.get("disclosures", []))
    return fetch


def _format_detail(record: dict, days_old: int) -> str:
    role_label = record["role"].title()
    verb = "buys" if record["action"] == "BUY" else "sells"
    return (
        f"{role_label} {record['insider_name']} {verb} "
        f"₹{record['value_cr']:.1f} Cr in {record['symbol']} "
        f"({days_old} days ago)"
    )


def _classify_type(role: str, action: str) -> CatalystType | None:
    if role == "promoter":
        return "promoter_buying" if action == "BUY" else "promoter_selling"
    if action == "BUY" and role in {"director", "kmp", "employee"}:
        return "insider_buying"
    # director/kmp/employee SELL = ESOP exit noise → drop
    return None


def build_insider_trade_catalysts(
    *,
    today: date,
    fetcher: InsiderTradesFetcher,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, list[Catalyst]]:
    """Convert insider-trade records to Catalysts."""
    raw = fetcher(today)
    filtered: list[tuple[dict, int, CatalystType]] = []
    for record in raw:
        if not record.get("symbol"):
            continue
        try:
            trade_date = datetime.strptime(record["trade_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        days_old = (today - trade_date).days
        if days_old < 0 or days_old > lookback_days:
            continue
        if record.get("is_esop_exercise"):
            continue
        if float(record.get("value_cr", 0.0)) < MIN_VALUE_CR:
            continue
        role = record.get("role", "").lower()
        if role not in ROLE_WEIGHTS:
            continue
        action = record.get("action")
        if action not in {"BUY", "SELL"}:
            continue
        ctype = _classify_type(role, action)
        if ctype is None:
            continue
        filtered.append((record, days_old, ctype))

    # Cluster detection — same symbol with ≥ 2 net-buy disclosures
    # (any role) within window gets the boost.
    buy_counts: dict[str, int] = {}
    for record, _, ctype in filtered:
        if ctype in {"promoter_buying", "insider_buying"}:
            buy_counts[record["symbol"]] = buy_counts.get(record["symbol"], 0) + 1

    result: dict[str, list[Catalyst]] = {}
    for record, days_old, ctype in filtered:
        symbol = record["symbol"]
        role = record["role"].lower()
        value = float(record["value_cr"])
        role_weight = ROLE_WEIGHTS[role]
        base = min(10.0, value * 2)
        boost = (
            CLUSTER_BOOST
            if ctype in {"promoter_buying", "insider_buying"}
            and buy_counts.get(symbol, 0) >= 2
            else 1.0
        )
        magnitude = max(0, min(10, round(base * (role_weight / 10) * boost)))
        result.setdefault(symbol, []).append(
            Catalyst(
                type=ctype,
                date=record["trade_date"],
                days_old=days_old,
                freshness=freshness_for(
                    days_old,
                    fresh_days=FRESH_DAYS,
                    recent_days=RECENT_DAYS,
                ),
                source_url=record.get("source_url", ""),
                detail=_format_detail(record, days_old),
                magnitude_score=magnitude,
            )
        )
    return result
