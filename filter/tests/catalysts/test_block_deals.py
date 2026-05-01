"""Tests for §13.1 Source 3 — NSE block & bulk deals classifier."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from saadhana_filter.catalysts.sources.block_deals import (
    MIN_DEAL_VALUE_CR,
    build_block_deal_catalysts,
    fixture_fetcher,
)

RUNTIME_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "catalysts"
    / "block_deals_fixture.json"
)
TODAY = date(2026, 5, 1)


def _stub_fetcher(records: list[dict]):
    def fetch(_today: date) -> list[dict]:
        return records
    return fetch


def _deal(
    *,
    symbol="ACME",
    deal_date="2026-04-28",
    side="BUY",
    counterparty_name="Nippon Life MF",
    counterparty_kind="mutual_fund",
    deal_value_cr=200.0,
):
    return {
        "symbol": symbol,
        "deal_date": deal_date,
        "side": side,
        "counterparty_name": counterparty_name,
        "counterparty_kind": counterparty_kind,
        "deal_value_cr": deal_value_cr,
        "source_url": "https://example.com",
    }


class TestBlockDealClassification:
    def test_institutional_buy_above_threshold(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal()]),
        )
        c = out["ACME"][0]
        assert c.type == "block_deal_buy"
        assert c.magnitude_score == 2  # round(200/100 * 1.0) = 2
        assert c.freshness == "FRESH"  # 3 days old

    def test_institutional_sell_classifies_as_sell(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(side="SELL")]),
        )
        assert out["ACME"][0].type == "block_deal_sell"

    def test_below_min_value_drops(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_value_cr=MIN_DEAL_VALUE_CR - 1)]),
        )
        assert out == {}

    def test_retail_counterparty_drops(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(counterparty_kind="individual")]),
        )
        assert out == {}

    def test_unknown_counterparty_drops(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(counterparty_kind=None)]),
        )
        assert out == {}

    def test_invalid_side_drops(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(side="HOLD")]),
        )
        assert out == {}


class TestBlockDealMagnitude:
    def test_100_cr_yields_magnitude_1(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_value_cr=100.0)]),
        )
        assert out["ACME"][0].magnitude_score == 1

    def test_500_cr_yields_magnitude_5(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_value_cr=500.0)]),
        )
        assert out["ACME"][0].magnitude_score == 5

    def test_caps_at_10(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_value_cr=2000.0)]),
        )
        assert out["ACME"][0].magnitude_score == 10

    def test_cluster_boost_when_two_buys_same_symbol(self):
        # Two buys on ACME → both get the 1.5× boost.
        # base = 200/100 = 2.0, boost 1.5 → magnitude 3
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([
                _deal(deal_value_cr=200.0, deal_date="2026-04-28"),
                _deal(deal_value_cr=200.0, deal_date="2026-04-26"),
            ]),
        )
        assert len(out["ACME"]) == 2
        for c in out["ACME"]:
            assert c.magnitude_score == 3

    def test_no_cluster_boost_for_mixed_sides(self):
        # One buy + one sell on same symbol → no clustering boost.
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([
                _deal(deal_value_cr=200.0, side="BUY"),
                _deal(deal_value_cr=200.0, side="SELL", deal_date="2026-04-26"),
            ]),
        )
        # Both magnitude 2 (base 2.0, no boost)
        for c in out["ACME"]:
            assert c.magnitude_score == 2


class TestBlockDealFreshness:
    def test_fresh_under_7d(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_date="2026-04-28")]),  # 3d
        )
        assert out["ACME"][0].freshness == "FRESH"

    def test_recent_8_to_30(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_date="2026-04-15")]),  # 16d
        )
        assert out["ACME"][0].freshness == "RECENT"

    def test_over_30d_drops(self):
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_deal(deal_date="2026-03-15")]),  # 47d
        )
        assert out == {}


class TestBlockDealRuntimeFixture:
    def test_runtime_fixture_classifies_known_deals(self):
        if not RUNTIME_FIXTURE.exists():
            pytest.skip("runtime fixture not present in this checkout")
        out = build_block_deal_catalysts(
            today=TODAY,
            fetcher=fixture_fetcher(RUNTIME_FIXTURE),
        )
        # Expected to classify: DIVISLAB (×2 with cluster boost), TCS,
        # RELIANCE, HDFCBANK (sell). Expected to drop: WIPRO (retail
        # counterparty), BHARTIARTL (47d STALE).
        assert sorted(out.keys()) == [
            "DIVISLAB",
            "HDFCBANK",
            "RELIANCE",
            "TCS",
        ]
        # DIVISLAB has 2 buys both clustered
        assert len(out["DIVISLAB"]) == 2
        for c in out["DIVISLAB"]:
            assert c.type == "block_deal_buy"
        # HDFCBANK is a SELL
        assert out["HDFCBANK"][0].type == "block_deal_sell"
