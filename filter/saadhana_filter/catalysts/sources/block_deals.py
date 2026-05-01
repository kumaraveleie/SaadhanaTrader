"""§13.1 source 3: NSE block & bulk deals classifier.

NSE publishes block-deals (single-counterparty trades ≥ ₹50 Cr) and
bulk-deals (single-broker trades ≥ 0.5% of equity) at T+1. Phase D1
ships a fixture-backed fetcher; Phase D2 swaps in the live NSE feed.

Catalyst types:
  - ``block_deal_buy``  — institutional buyer disclosed, deal value ≥ ₹50 Cr
  - ``block_deal_sell`` — institutional seller disclosed, deal value ≥ ₹50 Cr
                          (cautionary; magnitude same scale, tone different)

Filter rules:
  - ``deal_value_cr >= 50`` (skips retail-scale)
  - Counterparty must be classified institutional. We accept the
    fixture's ``counterparty_kind`` field directly (one of
    ``mutual_fund``, ``fii``, ``insurance``, ``aif``, ``pension``).

Freshness:
  FRESH   ≤ 7 days
  RECENT  8..30 days
  STALE   > 30 days  (drop)

Magnitude (deterministic, 0..10)::

    base = min(10, deal_value_cr / 100)
    cluster_boost = 1.5 if same symbol has another in-window deal
                    on the same side, else 1.0
    magnitude = round(base * cluster_boost)
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

DEFAULT_FIXTURE_PATH = Path("data/catalysts/block_deals_fixture.json")
DEFAULT_LOOKBACK_DAYS = 30
MIN_DEAL_VALUE_CR = 50.0
FRESH_DAYS = 7
RECENT_DAYS = 30
INSTITUTIONAL_KINDS = {"mutual_fund", "fii", "insurance", "aif", "pension"}
CLUSTER_BOOST = 1.5

BlockDealsFetcher = Callable[[date], list[dict]]
"""Returns a list of records, each with the fields the classifier needs.

Record shape:
    {
        "symbol": "DIVISLAB",
        "deal_date": "2026-04-25",        # YYYY-MM-DD
        "side": "BUY" | "SELL",
        "counterparty_name": "Nippon Life MF",
        "counterparty_kind": "mutual_fund",  # see INSTITUTIONAL_KINDS
        "deal_value_cr": 450.0,            # crore rupees
        "source_url": "https://...",
    }
"""


def fixture_fetcher(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> BlockDealsFetcher:
    """Default fetcher backed by an on-disk JSON fixture."""
    def fetch(today: date) -> list[dict]:
        if not fixture_path.exists():
            return []
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        return list(raw.get("deals", []))
    return fetch


def _format_detail(record: dict) -> str:
    side_verb = "buys" if record["side"] == "BUY" else "sells"
    return (
        f"{record['counterparty_name']} {side_verb} ₹{record['deal_value_cr']:.0f} Cr "
        f"in {record['symbol']} ({record['deal_date']})"
    )


def build_block_deal_catalysts(
    *,
    today: date,
    fetcher: BlockDealsFetcher,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, list[Catalyst]]:
    """Convert block-deal records to Catalysts. Filters retail-size,
    non-institutional, stale, and forward-dated entries.
    """
    raw = fetcher(today)
    filtered: list[tuple[dict, int]] = []  # (record, days_old)
    for record in raw:
        if not record.get("symbol"):
            continue
        try:
            deal_date = datetime.strptime(record["deal_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        days_old = (today - deal_date).days
        if days_old < 0 or days_old > lookback_days:
            continue
        if float(record.get("deal_value_cr", 0.0)) < MIN_DEAL_VALUE_CR:
            continue
        if record.get("counterparty_kind") not in INSTITUTIONAL_KINDS:
            continue
        if record.get("side") not in {"BUY", "SELL"}:
            continue
        filtered.append((record, days_old))

    # Cluster detection — boost magnitude when a symbol has more than
    # one same-side deal within the same lookback window.
    side_counts: dict[tuple[str, str], int] = {}
    for record, _ in filtered:
        key = (record["symbol"], record["side"])
        side_counts[key] = side_counts.get(key, 0) + 1

    result: dict[str, list[Catalyst]] = {}
    for record, days_old in filtered:
        symbol = record["symbol"]
        side = record["side"]
        ctype: CatalystType = "block_deal_buy" if side == "BUY" else "block_deal_sell"
        deal_value = float(record["deal_value_cr"])
        base = min(10.0, deal_value / 100.0)
        boost = CLUSTER_BOOST if side_counts.get((symbol, side), 0) >= 2 else 1.0
        magnitude = max(0, min(10, round(base * boost)))
        result.setdefault(symbol, []).append(
            Catalyst(
                type=ctype,
                date=record["deal_date"],
                days_old=days_old,
                freshness=freshness_for(
                    days_old,
                    fresh_days=FRESH_DAYS,
                    recent_days=RECENT_DAYS,
                ),
                source_url=record.get("source_url", ""),
                detail=_format_detail(record),
                magnitude_score=magnitude,
            )
        )
    return result
