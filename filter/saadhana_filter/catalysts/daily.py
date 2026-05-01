"""§13 daily-catalyst entry point.

Wires every active catalyst source through the per-symbol aggregator and
returns ``dict[symbol, CatalystSummary]`` ready to thread into both the
research snapshot and the daily scan.

As Sources 2–5 land, each new source's builder gets added to the list
in :func:`build_all_catalysts`. The aggregator's ``merge_sources``
handles deduplication + date-desc sort.
"""

from __future__ import annotations

from datetime import date

from saadhana_filter.catalysts.aggregator import merge_sources
from saadhana_filter.catalysts.sources.bse_filings import (
    build_filing_catalysts,
    fixture_fetcher as bse_fixture_fetcher,
)
from saadhana_filter.catalysts.types import Catalyst, CatalystSummary


def build_all_catalysts(*, today: date) -> dict[str, CatalystSummary]:
    """Run every active source and merge the per-symbol outputs."""
    # Source 1 — BSE/NSE corporate filings (Phase D commit 1)
    bse_filings = build_filing_catalysts(
        today=today,
        fetcher=bse_fixture_fetcher(),
    )

    # Sources 2–5 land in subsequent commits and append here. Each
    # produces dict[symbol, list[Catalyst]] on the same shape so the
    # merge below stays linear.
    sources: list[dict[str, list[Catalyst]]] = [bse_filings]

    all_symbols: set[str] = set()
    for source in sources:
        all_symbols.update(source.keys())

    summaries: dict[str, CatalystSummary] = {}
    for symbol in all_symbols:
        per_source = [source.get(symbol, []) for source in sources]
        summary = merge_sources(symbol, *per_source)
        if summary.catalysts:
            summaries[symbol] = summary
    return summaries
