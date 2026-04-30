"""Tests for the §13.1 BSE/NSE corporate-filings source."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from saadhana_filter.catalysts.sources.bse_filings import (
    build_filing_catalysts,
    fixture_fetcher,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SMALL_FIXTURE = FIXTURES_DIR / "small_filings.json"

# Repo-root-resolved path to the runtime fixture so the smoke test
# works regardless of where pytest is invoked from.
RUNTIME_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "catalysts"
    / "bse_filings_fixture.json"
)

# Pin "today" to the same scan date the runtime fixture targets so the
# runtime smoke test is deterministic.
TODAY = date(2026, 4, 30)


class TestFixtureFetcher:
    def test_groups_filings_by_symbol(self):
        fetch = fixture_fetcher(SMALL_FIXTURE)
        out = fetch(TODAY)
        assert sorted(out.keys()) == ["ACME", "BCD"]
        assert len(out["ACME"]) == 2
        assert len(out["BCD"]) == 1

    def test_missing_fixture_returns_empty(self):
        fetch = fixture_fetcher(Path("nonexistent/path/fixture.json"))
        assert fetch(TODAY) == {}


class TestBuildFilingCatalysts:
    def test_classifies_earnings_drops_agm_drops_old(self):
        catalysts_by_symbol = build_filing_catalysts(
            today=TODAY,
            fetcher=fixture_fetcher(SMALL_FIXTURE),
        )
        # ACME has 2 filings: one classified earnings_beat, one dropped AGM
        assert "ACME" in catalysts_by_symbol
        assert len(catalysts_by_symbol["ACME"]) == 1
        c = catalysts_by_symbol["ACME"][0]
        assert c.type == "earnings_beat"
        assert c.date == "2026-04-25"
        assert c.days_old == 5
        assert c.freshness == "FRESH"
        assert c.source_url.endswith("acme-q4")
        assert c.magnitude_score >= 6  # earnings_beat base
        # BCD's only filing is out of the 90-day lookback → symbol drops
        assert "BCD" not in catalysts_by_symbol

    def test_lookback_window_drops_old_in_window(self):
        # Tighten lookback to 3 days; the 2026-04-25 filing is 5 days old
        # so it should drop.
        catalysts_by_symbol = build_filing_catalysts(
            today=TODAY,
            fetcher=fixture_fetcher(SMALL_FIXTURE),
            lookback_days=3,
        )
        assert catalysts_by_symbol == {}

    def test_drops_forward_dated_filings(self):
        # Synthesize a fake fetcher emitting a forward-dated filing
        def fake_fetch(_today):
            return {
                "FUTURE": [
                    {
                        "symbol": "FUTURE",
                        "date": "2027-01-01",
                        "title": "Q4 FY28 Results",
                        "body": "Beat estimates by 50%.",
                        "source_url": "https://example.com/x",
                    }
                ]
            }
        out = build_filing_catalysts(today=TODAY, fetcher=fake_fetch)
        assert out == {}

    def test_handles_malformed_date_gracefully(self):
        def fake_fetch(_today):
            return {
                "BROKEN": [
                    {
                        "symbol": "BROKEN",
                        "date": "not-a-date",
                        "title": "Q4 results beat estimates",
                        "body": "EPS beat estimates by 10%.",
                        "source_url": "",
                    }
                ]
            }
        out = build_filing_catalysts(today=TODAY, fetcher=fake_fetch)
        assert out == {}

    def test_runtime_fixture_classifies_known_events(self):
        """End-to-end smoke against the committed runtime fixture.

        The fixture has 7 entries — 5 classify, 2 should drop (DIVISLAB
        bare quarterly with no beat, VEDL AGM notice). Verifies the
        full pipeline from JSON → Catalyst[].
        """
        if not RUNTIME_FIXTURE.exists():
            pytest.skip("runtime fixture not present in this checkout")

        out = build_filing_catalysts(
            today=TODAY,
            fetcher=fixture_fetcher(RUNTIME_FIXTURE),
        )
        # Expected to classify: RPGLIFE (earnings_beat), SUNPHARMA
        # (buyback), INDUSTOWER (mgmt change), ATUL (earnings_beat),
        # BHARATFORG (m_and_a). Expected to drop: DIVISLAB, VEDL.
        assert set(out.keys()) == {
            "RPGLIFE",
            "SUNPHARMA",
            "INDUSTOWER",
            "ATUL",
            "BHARATFORG",
        }
        types_seen = {c.type for sym in out for c in out[sym]}
        assert types_seen == {
            "earnings_beat",
            "buyback",
            "management_change",
            "m_and_a",
        }
        # Freshness must be set to a valid bucket on every record.
        # BHARATFORG (2026-03-28, 33 days old) is STALE on TODAY, which
        # is correct behaviour — STALE is informational, not dropped.
        for sym, catalysts in out.items():
            for c in catalysts:
                assert c.freshness in ("FRESH", "RECENT", "STALE")
