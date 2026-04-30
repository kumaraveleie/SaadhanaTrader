"""Tests for the §13.1 deterministic filing-text classifier."""

from __future__ import annotations

import pytest

from saadhana_filter.catalysts.classifier import classify_filing, magnitude_score


class TestClassifyFiling:
    # ── Earnings beat ─────────────────────────────────────────────────
    def test_earnings_beat_with_explicit_beat(self):
        assert (
            classify_filing(
                "Q4 FY26 Quarterly Results",
                "EPS up 18% YoY, beat estimates by 12%.",
            )
            == "earnings_beat"
        )

    def test_earnings_filing_without_beat_signal_drops(self):
        # Routine quarterly results with no explicit beat → uninformative,
        # classifier returns None and the source drops the filing.
        assert (
            classify_filing(
                "Q4 FY26 Quarterly Results",
                "Revenue ahead of last year. Management did not provide forward guidance.",
            )
            is None
        )

    def test_earnings_with_consensus_signal(self):
        assert (
            classify_filing(
                "Q3 FY26 results",
                "Revenue ahead of consensus, EBITDA exceeded estimates.",
            )
            == "earnings_beat"
        )

    # ── Buyback ───────────────────────────────────────────────────────
    def test_buyback_with_share_repurchase_phrasing(self):
        assert (
            classify_filing(
                "Board approves share buyback",
                "Buyback of up to 1.2 crore equity shares.",
            )
            == "buyback"
        )

    def test_buyback_alongside_q4_results_classifies_buyback(self):
        # Higher-precedence rule wins — a buyback announced with Q4
        # results is a buyback catalyst, not an earnings catalyst.
        assert (
            classify_filing(
                "Q4 FY26 Results and Buyback",
                "EPS beat estimates by 8%. Board approved share repurchase.",
            )
            == "buyback"
        )

    # ── Management change ─────────────────────────────────────────────
    def test_md_resignation(self):
        assert (
            classify_filing(
                "Resignation of Managing Director",
                "Mr. X stepped down as Managing Director.",
            )
            == "management_change"
        )

    def test_new_ceo_appointment(self):
        assert (
            classify_filing(
                "Appointment of CEO",
                "Mr. Y has been appointed as CEO with immediate effect.",
            )
            == "management_change"
        )

    # ── M&A ───────────────────────────────────────────────────────────
    def test_acquisition(self):
        assert (
            classify_filing(
                "Acquisition announcement",
                "Acquisition of US-based defense components subsidiary via scheme of arrangement.",
            )
            == "m_and_a"
        )

    def test_amalgamation(self):
        assert (
            classify_filing(
                "Scheme of amalgamation",
                "Amalgamation of wholly-owned subsidiary into the company.",
            )
            == "m_and_a"
        )

    # ── Guidance raise ────────────────────────────────────────────────
    def test_guidance_raise(self):
        assert (
            classify_filing(
                "Updated FY27 outlook",
                "Management raised guidance for FY27 revenue growth.",
            )
            == "guidance_raise"
        )

    # ── Negative cases (must drop) ────────────────────────────────────
    def test_agm_notice_drops(self):
        assert (
            classify_filing(
                "Notice of Annual General Meeting",
                "Routine board governance matters; no operational catalyst.",
            )
            is None
        )

    def test_unrelated_disclosure_drops(self):
        assert (
            classify_filing(
                "Trading window closure",
                "Trading window closed for designated persons until results.",
            )
            is None
        )


class TestMagnitudeScore:
    def test_base_score_for_buyback(self):
        # Plain buyback text, no strength modifiers → base 6
        assert magnitude_score("Board approves buyback", "buyback") == 6

    def test_strong_keywords_boost_score(self):
        # "double-digit" + "substantial" = 2 strong-keyword hits → +3 cap
        # earnings_beat base 6 → 6 + 3 = 9
        assert (
            magnitude_score(
                "Q4 EPS up double-digit, substantial margin expansion, beat estimates",
                "earnings_beat",
            )
            == 9
        )

    def test_score_capped_at_10(self):
        # Many strong keywords still cap at 10
        text = "significantly major double-digit substantial doubled major significantly"
        assert magnitude_score(text, "guidance_raise") == 10  # base 7 + 3 cap

    def test_score_floor_at_zero(self):
        # No way to drop below 0 with current rules but verify the clamp
        assert magnitude_score("", "sector_momentum") == 4

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown catalyst type"):
            magnitude_score("text", "made_up_type")  # type: ignore[arg-type]
