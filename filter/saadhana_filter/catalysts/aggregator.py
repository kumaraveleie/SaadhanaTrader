"""§13 per-symbol catalyst aggregator.

Receives lists of ``Catalyst`` records from each source module and
collapses them into a ``CatalystSummary`` per symbol — what /scanner
cards, /stock pages, and the sector drill-down "Triggers" panel
ultimately read.

The aggregator is intentionally dumb: it sorts by date desc, computes
the freshness counts, and flags the high-conviction bit. Anything
fancier (deduping near-identical catalysts across sources, weighting
by source reliability, etc.) belongs to Phase F's conviction tier.
"""

from __future__ import annotations

from saadhana_filter.catalysts.types import (
    Catalyst,
    CatalystSummary,
)

HIGH_CONVICTION_MAGNITUDE = 7
"""Magnitude threshold (when paired with FRESH freshness) for the
``has_high_conviction_catalyst`` flag — drives §14 conviction-tier
input in Phase F."""


def build_summary(symbol: str, catalysts: list[Catalyst]) -> CatalystSummary:
    """Build a CatalystSummary from an already-merged catalyst list."""
    fresh = sum(1 for c in catalysts if c.freshness == "FRESH")
    recent = sum(1 for c in catalysts if c.freshness == "RECENT")
    has_high = any(
        c.freshness == "FRESH" and c.magnitude_score >= HIGH_CONVICTION_MAGNITUDE
        for c in catalysts
    )
    return CatalystSummary(
        symbol=symbol,
        catalysts=catalysts,
        catalyst_count_fresh=fresh,
        catalyst_count_recent=recent,
        has_high_conviction_catalyst=has_high,
    )


def merge_sources(symbol: str, *source_outputs: list[Catalyst]) -> CatalystSummary:
    """Combine catalysts from multiple sources for a single symbol.

    Sorts by date descending (most recent first) so the UI can render
    a "what just happened" feed without further sorting. Each source
    output is already a list of ``Catalyst`` records.
    """
    merged: list[Catalyst] = sorted(
        [c for source in source_outputs for c in source],
        key=lambda c: c.date,
        reverse=True,
    )
    return build_summary(symbol, merged)
