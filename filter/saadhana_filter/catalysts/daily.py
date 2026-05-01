"""§13 daily-catalyst entry point.

Wires every active catalyst source through the per-symbol aggregator and
returns ``dict[symbol, CatalystSummary]`` ready to thread into both the
research snapshot and the daily scan.

As Sources 2–4 land, each new source's builder gets added to the list
in :func:`build_all_catalysts`. The aggregator's ``merge_sources``
handles deduplication + date-desc sort.

Sources currently active:
  1. BSE/NSE corporate filings  (sources/bse_filings.py)
  5. Sector momentum             (sources/sector_momentum.py — needs
     ``sector_aggregates`` + ``sector_constituents`` injected)

Sources 2/3/4 (shareholding / block deals / insider trades) plug in
identically once their fetcher + classifier modules land.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date

from saadhana_filter.catalysts.aggregator import merge_sources
from saadhana_filter.catalysts.sources.bse_filings import (
    build_filing_catalysts,
    fixture_fetcher as bse_fixture_fetcher,
)
from saadhana_filter.catalysts.sources.sector_momentum import (
    build_sector_momentum_catalysts,
)
from saadhana_filter.catalysts.types import Catalyst, CatalystSummary


def build_all_catalysts(
    *,
    today: date,
    sector_aggregates: Iterable[Mapping] | None = None,
    sector_constituents: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, CatalystSummary]:
    """Run every active source and merge the per-symbol outputs.

    ``sector_aggregates`` / ``sector_constituents`` are optional inputs
    for Source 5 (sector momentum). When omitted (e.g. backtest or unit
    tests), Source 5 contributes nothing and the function returns only
    Source-1 / 2 / 3 / 4 catalysts.
    """
    # Source 1 — BSE/NSE corporate filings
    bse_filings = build_filing_catalysts(
        today=today,
        fetcher=bse_fixture_fetcher(),
    )

    # Source 5 — sector momentum (only when caller provides sector data)
    sector_momentum: dict[str, list[Catalyst]] = {}
    if sector_aggregates is not None and sector_constituents is not None:
        sector_momentum = build_sector_momentum_catalysts(
            today_iso=today.isoformat(),
            sector_aggregates=sector_aggregates,
            sector_constituents=sector_constituents,
        )

    sources: list[dict[str, list[Catalyst]]] = [bse_filings, sector_momentum]

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
