"""Tests for §13.1 Source 4 — SEBI insider trade classifier."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from saadhana_filter.catalysts.sources.insider_trades import (
    MIN_VALUE_CR,
    ROLE_WEIGHTS,
    build_insider_trade_catalysts,
    fixture_fetcher,
)

RUNTIME_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "catalysts"
    / "insider_trades_fixture.json"
)
TODAY = date(2026, 5, 1)


def _stub_fetcher(records: list[dict]):
    def fetch(_today: date) -> list[dict]:
        return records
    return fetch


def _disclosure(
    *,
    symbol="ACME",
    trade_date="2026-04-25",
    insider_name="Person X",
    role="promoter",
    action="BUY",
    value_cr=10.0,
    is_esop_exercise=False,
):
    return {
        "symbol": symbol,
        "trade_date": trade_date,
        "insider_name": insider_name,
        "role": role,
        "action": action,
        "value_cr": value_cr,
        "is_esop_exercise": is_esop_exercise,
        "source_url": "https://example.com",
    }


class TestInsiderTradeClassification:
    def test_promoter_buying(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure()]),
        )
        c = out["ACME"][0]
        assert c.type == "promoter_buying"
        assert c.freshness == "FRESH"  # 6d under 14d
        assert "Promoter" in c.detail
        assert "buys" in c.detail

    def test_promoter_selling_classifies(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(action="SELL")]),
        )
        assert out["ACME"][0].type == "promoter_selling"

    def test_director_buying(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="director")]),
        )
        assert out["ACME"][0].type == "insider_buying"

    def test_kmp_buying(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="kmp")]),
        )
        assert out["ACME"][0].type == "insider_buying"

    def test_employee_buying(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="employee")]),
        )
        assert out["ACME"][0].type == "insider_buying"

    def test_director_selling_drops(self):
        # Director SELL = ESOP exit noise → drop
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="director", action="SELL")]),
        )
        assert out == {}

    def test_kmp_selling_drops(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="kmp", action="SELL")]),
        )
        assert out == {}

    def test_esop_exercise_drops(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(is_esop_exercise=True)]),
        )
        assert out == {}

    def test_below_min_value_drops(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(value_cr=MIN_VALUE_CR - 0.1)]),
        )
        assert out == {}

    def test_unknown_role_drops(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="auditor")]),
        )
        assert out == {}


class TestInsiderTradeMagnitude:
    def test_promoter_full_role_weight(self):
        # ₹10 Cr promoter buy: base 10 * (10/10) * 1.0 = 10
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(value_cr=10.0)]),
        )
        assert out["ACME"][0].magnitude_score == 10

    def test_director_weighted_lower(self):
        # ₹5 Cr director buy: base 10 * (6/10) * 1.0 = 6
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="director", value_cr=5.0)]),
        )
        assert out["ACME"][0].magnitude_score == 6

    def test_employee_smallest_weight(self):
        # ₹3 Cr employee buy: base 6 * (2/10) * 1.0 = 1.2 → 1
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(role="employee", value_cr=3.0)]),
        )
        assert out["ACME"][0].magnitude_score == 1

    def test_cluster_boost_on_two_promoter_buys(self):
        # Two promoter buys on same symbol → both get 1.5× boost
        # ₹10 Cr × promoter (1.0) × 1.5 = 15 → cap 10
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([
                _disclosure(value_cr=10.0, trade_date="2026-04-25"),
                _disclosure(value_cr=10.0, trade_date="2026-04-22",
                            insider_name="Person Y"),
            ]),
        )
        assert len(out["ACME"]) == 2
        for c in out["ACME"]:
            assert c.magnitude_score == 10  # cap

    def test_no_cluster_boost_for_sells(self):
        # Promoter SELL doesn't cluster with promoter BUY for the boost.
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([
                _disclosure(value_cr=5.0, action="BUY"),
                _disclosure(value_cr=5.0, action="SELL", trade_date="2026-04-22"),
            ]),
        )
        # Buy: 10 * (10/10) * 1.0 = 10  (no cluster mate)
        # Sell: 10 * (10/10) * 1.0 = 10
        assert all(c.magnitude_score == 10 for c in out["ACME"])

    def test_role_weights_strict_ordering(self):
        # Sanity: weights must respect promoter > director > kmp > employee
        assert ROLE_WEIGHTS["promoter"] > ROLE_WEIGHTS["director"]
        assert ROLE_WEIGHTS["director"] > ROLE_WEIGHTS["kmp"]
        assert ROLE_WEIGHTS["kmp"] > ROLE_WEIGHTS["employee"]


class TestInsiderTradeFreshness:
    def test_fresh_under_14d(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(trade_date="2026-04-25")]),  # 6d
        )
        assert out["ACME"][0].freshness == "FRESH"

    def test_recent_15_to_60(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(trade_date="2026-04-01")]),  # 30d
        )
        assert out["ACME"][0].freshness == "RECENT"

    def test_over_60d_drops(self):
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=_stub_fetcher([_disclosure(trade_date="2026-02-15")]),  # 75d
        )
        assert out == {}


class TestInsiderTradeRuntimeFixture:
    def test_runtime_fixture_classifies_known_disclosures(self):
        if not RUNTIME_FIXTURE.exists():
            pytest.skip("runtime fixture not present in this checkout")
        out = build_insider_trade_catalysts(
            today=TODAY,
            fetcher=fixture_fetcher(RUNTIME_FIXTURE),
        )
        # Expected to classify:
        #   JSWENERGY ×2 (Sajjan Jindal BUY + JSW Group Trust BUY,
        #     same-symbol cluster), TATAPOWER (Chandrasekaran BUY),
        #     BHARATFORG (director Suresh Sharma BUY → insider_buying),
        #     VEDL (Anil Agarwal SELL → promoter_selling)
        # Expected to drop:
        #   TCS (ESOP exercise), INFY (>60d STALE)
        assert sorted(out.keys()) == [
            "BHARATFORG",
            "JSWENERGY",
            "TATAPOWER",
            "VEDL",
        ]
        assert len(out["JSWENERGY"]) == 2
        assert all(c.type == "promoter_buying" for c in out["JSWENERGY"])
        assert out["BHARATFORG"][0].type == "insider_buying"
        assert out["VEDL"][0].type == "promoter_selling"
