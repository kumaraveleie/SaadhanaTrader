"""Tests for §13.1 Source 5 — sector momentum catalyst classifier."""

from __future__ import annotations

from saadhana_filter.catalysts.sources.sector_momentum import (
    BREADTH_50DMA_THRESHOLD,
    RS_5D_THRESHOLD,
    build_sector_momentum_catalysts,
)

TODAY = "2026-05-01"


def _agg(
    *,
    sector="PHARMACEUTICALS",
    label="Pharmaceuticals",
    rs_5d=1.07,
    breadth_above_50dma=0.70,
    sector_index_change_5d=0.015,
):
    """Minimal sector aggregate dict with only the fields the
    classifier reads. Real aggregates carry many more keys; classifier
    is intentionally tolerant."""
    return {
        "sector": sector,
        "sector_label": label,
        "rs_5d": rs_5d,
        "breadth_above_50dma": breadth_above_50dma,
        "sector_index_change_5d": sector_index_change_5d,
    }


class TestSectorMomentumQualification:
    def test_pharma_qualifies_when_rs_breadth_today_all_above_thresholds(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg()],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB", "SUNPHARMA"]},
        )
        assert set(out.keys()) == {"DIVISLAB", "SUNPHARMA"}
        assert out["DIVISLAB"][0].type == "sector_momentum"
        assert out["DIVISLAB"][0].freshness == "FRESH"
        assert out["DIVISLAB"][0].days_old == 0

    def test_negative_rs_drops(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(rs_5d=0.92)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out == {}

    def test_low_breadth_drops_even_with_strong_rs(self):
        # RS = 1.20 is strong but only 40% above 50-DMA → drop
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(rs_5d=1.20, breadth_above_50dma=0.40)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out == {}

    def test_zero_or_negative_5d_change_drops(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(sector_index_change_5d=0.0)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out == {}

    def test_rs_at_threshold_drops_strict_inequality(self):
        # rs_5d == RS_5D_THRESHOLD → strict-> filter excludes
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(rs_5d=RS_5D_THRESHOLD)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out == {}

    def test_breadth_at_threshold_drops_strict_inequality(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(breadth_above_50dma=BREADTH_50DMA_THRESHOLD)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out == {}

    def test_no_constituents_drops_silently(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg()],
            sector_constituents={},
        )
        assert out == {}

    def test_missing_aggregate_field_drops(self):
        # rs_5d=None (Nifty 5d return was 0) → safely drops
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(rs_5d=None)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out == {}


class TestSectorMomentumMagnitude:
    def test_user_example_modest_sector_lift(self):
        # +1.5% sector with 70% breadth → base 3.0, mult 1.2 → ≈ 3.6 → 4
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(sector_index_change_5d=0.015, breadth_above_50dma=0.70)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out["DIVISLAB"][0].magnitude_score == 4

    def test_user_example_strong_sector_lift(self):
        # +3.0% sector with 80% breadth → base 6.0, mult 1.3 → ≈ 7.8 → 8
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(sector_index_change_5d=0.030, breadth_above_50dma=0.80)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out["DIVISLAB"][0].magnitude_score == 8

    def test_caps_at_10(self):
        # Very strong sector pump → magnitude clamps at 10
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg(sector_index_change_5d=0.10, breadth_above_50dma=0.95)],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        assert out["DIVISLAB"][0].magnitude_score == 10


class TestSectorMomentumDetail:
    def test_detail_includes_label_pct_breadth(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg()],
            sector_constituents={"PHARMACEUTICALS": ["DIVISLAB"]},
        )
        d = out["DIVISLAB"][0].detail
        assert "Pharmaceuticals" in d
        assert "5d" in d
        assert "above 50-DMA" in d


class TestSectorMomentumEachConstituentGetsCatalyst:
    def test_all_members_receive_same_catalyst_object(self):
        out = build_sector_momentum_catalysts(
            today_iso=TODAY,
            sector_aggregates=[_agg()],
            sector_constituents={"PHARMACEUTICALS": ["A", "B", "C"]},
        )
        assert sorted(out.keys()) == ["A", "B", "C"]
        # Same Catalyst instance shared across members (immutable, frozen)
        assert out["A"][0] is out["B"][0]
        assert out["B"][0] is out["C"][0]
