"""Tests for §13 Phase D catalyst dataclasses + freshness windows."""

from __future__ import annotations

import pytest

from saadhana_filter.catalysts.types import (
    FRESH_DAYS,
    RECENT_DAYS,
    Catalyst,
    CatalystSummary,
    catalyst_to_dict,
    freshness_for,
    summary_to_dict,
)


class TestFreshnessFor:
    def test_today_is_fresh(self):
        assert freshness_for(0) == "FRESH"

    def test_just_inside_fresh_window(self):
        assert freshness_for(FRESH_DAYS - 1) == "FRESH"

    def test_just_outside_fresh_window_is_recent(self):
        assert freshness_for(FRESH_DAYS) == "RECENT"

    def test_just_inside_recent_window(self):
        assert freshness_for(RECENT_DAYS - 1) == "RECENT"

    def test_recent_window_boundary_is_stale(self):
        assert freshness_for(RECENT_DAYS) == "STALE"

    def test_far_past_is_stale(self):
        assert freshness_for(365) == "STALE"

    def test_negative_days_old_raises(self):
        with pytest.raises(ValueError, match=">= 0"):
            freshness_for(-1)


class TestCatalystToDict:
    def test_round_trip_preserves_fields(self):
        c = Catalyst(
            type="earnings_beat",
            date="2026-04-25",
            days_old=5,
            freshness="FRESH",
            source_url="https://example.com",
            detail="Q4 EPS up 18% YoY beat estimates by 12%",
            magnitude_score=8,
        )
        d = catalyst_to_dict(c)
        assert d == {
            "type": "earnings_beat",
            "date": "2026-04-25",
            "days_old": 5,
            "freshness": "FRESH",
            "source_url": "https://example.com",
            "detail": "Q4 EPS up 18% YoY beat estimates by 12%",
            "magnitude_score": 8,
        }


class TestSummaryToDict:
    def test_empty_summary_emits_zero_counts(self):
        s = CatalystSummary(symbol="ATUL")
        d = summary_to_dict(s)
        assert d["symbol"] == "ATUL"
        assert d["catalysts"] == []
        assert d["catalyst_count_fresh"] == 0
        assert d["catalyst_count_recent"] == 0
        assert d["has_high_conviction_catalyst"] is False
