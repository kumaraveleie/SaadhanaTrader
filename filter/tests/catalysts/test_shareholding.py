"""Tests for §13.1 Source 2 — NSE shareholding-pattern classifier."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from saadhana_filter.catalysts.sources.shareholding import (
    THRESHOLD_PP,
    build_shareholding_catalysts,
    fixture_fetcher,
)

RUNTIME_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "catalysts"
    / "shareholding_fixture.json"
)
TODAY = date(2026, 5, 1)


def _stub_fetcher(records: list[dict]):
    def fetch(_today: date) -> list[dict]:
        return records
    return fetch


class TestShareholdingClassification:
    def test_fii_increase_above_threshold(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "FII",
                "delta_pp": 1.4,
                "new_pct": 24.8,
                "source_url": "https://example.com",
            }]),
        )
        assert "ACME" in out
        c = out["ACME"][0]
        assert c.type == "fii_increase"
        assert c.magnitude_score == 3  # round(1.4 * 2)
        assert c.freshness == "FRESH"  # 10 days old < 30
        assert "FII +1.4pp" in c.detail
        assert "Q4 FY26" in c.detail

    def test_dii_increase(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "DII",
                "delta_pp": 1.1,
                "new_pct": 18.2,
                "source_url": "https://example.com",
            }]),
        )
        assert out["ACME"][0].type == "dii_increase"

    def test_promoter_buying_high_magnitude(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "PROMOTER",
                "delta_pp": 2.5,
                "new_pct": 31.5,
                "source_url": "https://example.com",
            }]),
        )
        c = out["ACME"][0]
        assert c.type == "promoter_buying"
        assert c.magnitude_score == 5  # round(2.5 * 2)

    def test_below_threshold_drops(self):
        # 0.2pp delta < 0.5pp → drop
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "FII",
                "delta_pp": 0.2,
                "new_pct": 33.2,
                "source_url": "https://example.com",
            }]),
        )
        assert out == {}

    def test_threshold_boundary_strict(self):
        # delta == THRESHOLD_PP → drop (strict-less-than)
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "FII",
                "delta_pp": THRESHOLD_PP - 0.0001,
                "new_pct": 20.0,
                "source_url": "",
            }]),
        )
        assert out == {}

    def test_negative_delta_drops(self):
        # We only emit "increase" catalysts; -1.0pp drops silently.
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "FII",
                "delta_pp": -1.0,
                "new_pct": 19.0,
                "source_url": "",
            }]),
        )
        assert out == {}

    def test_unknown_category_drops(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",
                "quarter": "Q4 FY26",
                "category": "RETAIL",
                "delta_pp": 1.5,
                "new_pct": 10.0,
                "source_url": "",
            }]),
        )
        assert out == {}


class TestShareholdingFreshness:
    def test_fresh_window_under_30d(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-04-21",  # 10 days old
                "quarter": "Q4 FY26",
                "category": "FII",
                "delta_pp": 1.0,
                "new_pct": 20.0,
                "source_url": "",
            }]),
        )
        assert out["ACME"][0].freshness == "FRESH"

    def test_recent_window_31_to_90d(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2026-03-01",  # ~61 days old
                "quarter": "Q3 FY26",
                "category": "FII",
                "delta_pp": 1.0,
                "new_pct": 20.0,
                "source_url": "",
            }]),
        )
        # Source 2 uses 30/90 freshness windows → 61d = RECENT
        assert out["ACME"][0].freshness == "RECENT"

    def test_over_lookback_drops(self):
        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([{
                "symbol": "ACME",
                "filing_date": "2025-10-01",  # ~7 months old
                "quarter": "Q1 FY26",
                "category": "FII",
                "delta_pp": 1.0,
                "new_pct": 20.0,
                "source_url": "",
            }]),
        )
        assert out == {}


class TestShareholdingRuntimeFixture:
    def test_runtime_fixture_classifies_six_drops_one(self):
        if not RUNTIME_FIXTURE.exists():
            pytest.skip("runtime fixture not present in this checkout")

        out = build_shareholding_catalysts(
            today=TODAY,
            fetcher=fixture_fetcher(RUNTIME_FIXTURE),
        )
        # 7 fixture entries: 2 FII + 2 DII + 2 PROMOTER + 1 below-threshold (INFY 0.2pp)
        # 6 should classify; INFY should drop.
        assert "INFY" not in out
        assert sorted(out.keys()) == [
            "DIVISLAB",
            "HINDUNILVR",
            "ITC",
            "M_AND_M",
            "RELIANCE",
            "TCS",
        ]
        types_seen = {c.type for sym in out for c in out[sym]}
        assert types_seen == {"fii_increase", "dii_increase", "promoter_buying"}
