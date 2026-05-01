"""§13.1 source 2: NSE shareholding-pattern QoQ delta classifier.

Quarterly shareholding disclosures land 21 days after each fiscal
quarter-end. The fixture entries below describe the most recent
QoQ delta per category (FII / DII / promoter) per symbol; the
classifier emits one catalyst per category whose abs(delta) ≥ 0.5pp.

Catalyst types (existing taxonomy):
  - ``fii_increase``    — FII stake up QoQ ≥ +0.5pp
  - ``dii_increase``    — DII stake up QoQ ≥ +0.5pp
  - ``promoter_buying`` — promoter stake up QoQ ≥ +0.5pp

Freshness windows:
  FRESH   ≤ 30 days from filing date
  RECENT  31..90 days
  STALE   > 90 days  (drop)

Magnitude (deterministic, 0..10)::

    magnitude = round(min(10, abs(delta_pp) * 2))

Examples:
  FII +1.4pp → magnitude 3
  Promoter +2.5pp → magnitude 5

Phase D2 swaps the fixture-backed fetcher for a live NSE shareholding
scraper without changing the classifier or downstream consumers.
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

DEFAULT_FIXTURE_PATH = Path("data/catalysts/shareholding_fixture.json")
DEFAULT_LOOKBACK_DAYS = 90  # >90 days old = STALE → dropped
THRESHOLD_PP = 0.5
# Source-specific freshness windows (override the canonical 7/30 because
# shareholding disclosures are quarterly).
FRESH_DAYS = 30
RECENT_DAYS = 90

ShareholdingFetcher = Callable[[date], list[dict]]
"""Returns a list of records, each with the fields the classifier needs.

Record shape:
    {
        "symbol": "DIVISLAB",
        "filing_date": "2026-04-21",
        "quarter": "Q4 FY26",
        "category": "FII" | "DII" | "PROMOTER",
        "delta_pp": 1.4,        # signed percentage points
        "new_pct": 24.8,        # post-disclosure stake %
        "source_url": "https://...",
    }
"""


CATEGORY_TO_TYPE: dict[str, CatalystType] = {
    "FII": "fii_increase",
    "DII": "dii_increase",
    "PROMOTER": "promoter_buying",
}


def fixture_fetcher(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> ShareholdingFetcher:
    """Default fetcher backed by an on-disk JSON fixture."""
    def fetch(today: date) -> list[dict]:
        if not fixture_path.exists():
            return []
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        return list(raw.get("disclosures", []))
    return fetch


def _format_detail(record: dict) -> str:
    delta = record["delta_pp"]
    sign = "+" if delta >= 0 else "-"
    return (
        f"{record['category']} {sign}{abs(delta):.1f}pp QoQ to "
        f"{record['new_pct']:.1f}% ({record['quarter']})"
    )


def build_shareholding_catalysts(
    *,
    today: date,
    fetcher: ShareholdingFetcher,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, list[Catalyst]]:
    """Convert shareholding disclosures to classified Catalyst records."""
    raw = fetcher(today)
    result: dict[str, list[Catalyst]] = {}
    for record in raw:
        symbol = record.get("symbol")
        if not symbol:
            continue
        try:
            filing_date = datetime.strptime(record["filing_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        days_old = (today - filing_date).days
        if days_old < 0 or days_old > lookback_days:
            continue
        category = record.get("category")
        ctype = CATEGORY_TO_TYPE.get(category)
        if ctype is None:
            continue
        delta = float(record.get("delta_pp", 0.0))
        # Only emit "increase" catalysts; small deltas drop as noise.
        if delta < THRESHOLD_PP:
            continue
        magnitude = max(0, min(10, round(abs(delta) * 2)))
        result.setdefault(symbol, []).append(
            Catalyst(
                type=ctype,
                date=record["filing_date"],
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
