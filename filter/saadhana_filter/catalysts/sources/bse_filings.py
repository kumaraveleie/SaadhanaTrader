"""§13.1 source: BSE/NSE corporate filings (earnings, board resolutions,
material disclosures).

The runtime fetcher swaps via the ``FilingFetcher`` protocol. Phase D1
(this checkpoint) ships a fixture-backed default that reads a curated
JSON file under ``data/catalysts/``; Phase D2 replaces it with a live
BSE/NSE scraper without changing the classifier, aggregator, or any
downstream consumer. Both produce the same ``dict[symbol,
list[Catalyst]]`` output.

Per filing record the fetcher must emit:
    {
        "symbol": "RPGLIFE",
        "date": "2026-04-25",          # YYYY-MM-DD
        "title": "...",                 # filing title / subject line
        "body": "...",                  # filing body / abstract
        "source_url": "https://...",    # link to the canonical PDF / page
    }
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from saadhana_filter.catalysts.classifier import classify_filing, magnitude_score
from saadhana_filter.catalysts.types import Catalyst, freshness_for

# Repo-root-relative default fixture path (Phase D1).
DEFAULT_FIXTURE_PATH = Path("data/catalysts/bse_filings_fixture.json")
DEFAULT_LOOKBACK_DAYS = 90

FilingFetcher = Callable[[date], dict[str, list[dict]]]
"""Protocol: takes ``today``, returns ``{symbol: [filing_record, ...]}``."""


def fixture_fetcher(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> FilingFetcher:
    """Default fetcher backed by an on-disk JSON fixture.

    Used until Phase D2 wires up the live BSE/NSE feeds. The fixture is
    committed to the repo so smoke runs reproduce identically across
    machines and CI.
    """
    def fetch(today: date) -> dict[str, list[dict]]:
        if not fixture_path.exists():
            return {}
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        out: dict[str, list[dict]] = {}
        for entry in raw.get("filings", []):
            sym = entry.get("symbol")
            if not sym:
                continue
            out.setdefault(sym, []).append(entry)
        return out
    return fetch


def build_filing_catalysts(
    *,
    today: date,
    fetcher: FilingFetcher,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, list[Catalyst]]:
    """Convert filings to classified Catalyst records keyed by symbol.

    - Drops filings outside ``[today - lookback_days, today]`` (forward-
      dated filings are also dropped; if a fixture has them it's a
      data-quality bug, not a real catalyst).
    - Drops filings the classifier returns ``None`` for (uninformative
      announcements like AGM notices, routine disclosures).
    """
    raw_by_symbol = fetcher(today)
    result: dict[str, list[Catalyst]] = {}
    for symbol, filings in raw_by_symbol.items():
        catalysts: list[Catalyst] = []
        for f in filings:
            try:
                filing_date = datetime.strptime(f["date"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue
            days_old = (today - filing_date).days
            if days_old < 0 or days_old > lookback_days:
                continue
            title = f.get("title", "")
            body = f.get("body", "")
            ctype = classify_filing(title, body)
            if ctype is None:
                continue
            catalysts.append(
                Catalyst(
                    type=ctype,
                    date=f["date"],
                    days_old=days_old,
                    freshness=freshness_for(days_old),
                    source_url=f.get("source_url", ""),
                    detail=body[:200],
                    magnitude_score=magnitude_score(f"{title} {body}", ctype),
                )
            )
        if catalysts:
            result[symbol] = catalysts
    return result
