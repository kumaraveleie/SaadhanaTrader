"""Phase D catalyst engine v1 (deterministic sources only).

Per ``spec/filter_spec_v2_1.md`` §13. Each source emits a normalised list
of ``Catalyst`` records keyed by symbol; the aggregator merges across
sources into a per-symbol ``CatalystSummary`` consumed by the daily scan
and the /research sector drill-down "Triggers" panel.

Source modules live under :mod:`saadhana_filter.catalysts.sources`. They
are interchangeable: each exposes a callable matching the source-specific
fetcher protocol so the live scraper can swap in for the fixture-backed
default without touching the aggregator.

Phase D2 (post-checkpoint) replaces fixture fetchers with live BSE/NSE/
SEBI integrations; Phase E adds the LLM news-classification source on
top.
"""

from saadhana_filter.catalysts.aggregator import (
    HIGH_CONVICTION_MAGNITUDE,
    build_summary,
    merge_sources,
)
from saadhana_filter.catalysts.classifier import classify_filing, magnitude_score
from saadhana_filter.catalysts.types import (
    FRESH_DAYS,
    RECENT_DAYS,
    Catalyst,
    CatalystSummary,
    CatalystType,
    FreshnessTag,
    freshness_for,
)

__all__ = [
    "Catalyst",
    "CatalystSummary",
    "CatalystType",
    "FreshnessTag",
    "FRESH_DAYS",
    "HIGH_CONVICTION_MAGNITUDE",
    "RECENT_DAYS",
    "build_summary",
    "classify_filing",
    "freshness_for",
    "magnitude_score",
    "merge_sources",
]
