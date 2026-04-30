"""Tests for the §13 per-symbol catalyst aggregator."""

from __future__ import annotations

from saadhana_filter.catalysts.aggregator import (
    HIGH_CONVICTION_MAGNITUDE,
    build_summary,
    merge_sources,
)
from saadhana_filter.catalysts.types import Catalyst


def _make(
    *,
    type="earnings_beat",
    date="2026-04-25",
    days_old=5,
    freshness="FRESH",
    magnitude=6,
):
    return Catalyst(
        type=type,
        date=date,
        days_old=days_old,
        freshness=freshness,
        source_url=f"https://example.com/{date}",
        detail="...",
        magnitude_score=magnitude,
    )


class TestBuildSummary:
    def test_empty_catalysts_yield_zero_counts(self):
        s = build_summary("ACME", [])
        assert s.symbol == "ACME"
        assert s.catalyst_count_fresh == 0
        assert s.catalyst_count_recent == 0
        assert s.has_high_conviction_catalyst is False

    def test_counts_freshness_buckets(self):
        catalysts = [
            _make(freshness="FRESH"),
            _make(freshness="FRESH"),
            _make(freshness="RECENT"),
            _make(freshness="STALE"),
        ]
        s = build_summary("ACME", catalysts)
        assert s.catalyst_count_fresh == 2
        assert s.catalyst_count_recent == 1
        # STALE is not counted in either bucket — informational only

    def test_high_conviction_requires_fresh_and_high_magnitude(self):
        # FRESH + magnitude == HIGH_CONVICTION_MAGNITUDE → flagged
        s = build_summary(
            "ACME",
            [_make(freshness="FRESH", magnitude=HIGH_CONVICTION_MAGNITUDE)],
        )
        assert s.has_high_conviction_catalyst is True

    def test_high_magnitude_but_recent_not_flagged(self):
        # Magnitude high but freshness RECENT → NOT high conviction
        s = build_summary(
            "ACME",
            [_make(freshness="RECENT", magnitude=10)],
        )
        assert s.has_high_conviction_catalyst is False

    def test_fresh_but_low_magnitude_not_flagged(self):
        s = build_summary(
            "ACME",
            [_make(freshness="FRESH", magnitude=HIGH_CONVICTION_MAGNITUDE - 1)],
        )
        assert s.has_high_conviction_catalyst is False


class TestMergeSources:
    def test_combines_and_sorts_desc_by_date(self):
        source_a = [_make(date="2026-04-25")]
        source_b = [
            _make(date="2026-04-22", type="buyback"),
            _make(date="2026-04-28", type="m_and_a"),
        ]
        s = merge_sources("ACME", source_a, source_b)
        dates = [c.date for c in s.catalysts]
        assert dates == ["2026-04-28", "2026-04-25", "2026-04-22"]
        types = [c.type for c in s.catalysts]
        assert types == ["m_and_a", "earnings_beat", "buyback"]

    def test_empty_sources_yield_empty_summary(self):
        s = merge_sources("ACME", [], [])
        assert s.catalysts == []
        assert s.has_high_conviction_catalyst is False
