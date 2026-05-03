"""Sec.6.4 Tier 2 Quality Score — operational definition (Diamond Layer 3).

§14.1 defines the canonical 6-check booster; Sec.6.4 operationalises
it as a callable filter and ships a degraded **v0** that uses the
checks computable from the current fundamentals snapshot.

v0 (today): 5 checks built on the Tier 1 columns
  1. EPS YoY > 0
  2. Revenue YoY > 0
  3. Promoter holding ≥ 40%  (tighter than Tier 1's ≥ 30%)
  4. Promoter pledge = 0%    (tighter than Tier 1's ≤ 25%)
  5. Debt/Equity ≤ 1.0       (tighter than Tier 1's ≤ 1.5)
     — Banks/NBFCs swap to GNPA ≤ 4% AND CAR ≥ 12% per §4.1.

canonical (when data lands): the 6 checks of §14.1
  1. ROE > 15% (3-year average)
  2. ROCE > 18% (3-year average)
  3. Earnings CAGR > 15% (3-year)
  4. Free cash flow positive (last 4 quarters)
  5. Promoter buying in last 6 months
  6. FII or DII stake rising vs 4 quarters ago

The function picks the version automatically from the columns
present on the input row; tests pin both behaviours.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

from saadhana_filter.signals.tier1 import is_bank_or_nbfc

# Sec.6.4 thresholds — matching the spec table.
V0_PROMOTER_HOLDING_MIN = 40.0
V0_PROMOTER_PLEDGE_MAX = 0.0
V0_DEBT_EQUITY_MAX = 1.0
V0_GNPA_MAX = 4.0  # §4.1 swap for banks/NBFCs
V0_CAR_MIN = 12.0  # §4.1 swap for banks/NBFCs

CANONICAL_ROE_MIN = 15.0
CANONICAL_ROCE_MIN = 18.0
CANONICAL_EARNINGS_CAGR_MIN = 15.0


# ─────────────────────────────────────────────────────────────────────
# v0 — 5-check score from current fundamentals columns
# ─────────────────────────────────────────────────────────────────────
def _v0_score(row: pd.Series) -> int:
    """Return Tier 2 v0 score 0..5 for one fundamentals row.

    Banks / NBFCs / financial-services issuers swap the D/E check for
    the §4.1 GNPA + CAR pair (counts as a single check pass when both
    GNPA ≤ 4 AND CAR ≥ 12). Other sectors check D/E ≤ 1.0 directly.
    """
    score = 0
    eps = row.get("eps_yoy")
    if eps is not None and not pd.isna(eps) and float(eps) > 0:
        score += 1
    rev = row.get("revenue_yoy")
    if rev is not None and not pd.isna(rev) and float(rev) > 0:
        score += 1
    holding = row.get("promoter_holding_pct")
    if (
        holding is not None
        and not pd.isna(holding)
        and float(holding) >= V0_PROMOTER_HOLDING_MIN
    ):
        score += 1
    pledge = row.get("promoter_pledge_pct")
    if (
        pledge is not None
        and not pd.isna(pledge)
        and float(pledge) <= V0_PROMOTER_PLEDGE_MAX
    ):
        score += 1
    sector = str(row.get("sector", ""))
    if is_bank_or_nbfc(sector):
        gnpa = row.get("gnpa")
        car = row.get("car")
        if (
            gnpa is not None and not pd.isna(gnpa) and float(gnpa) <= V0_GNPA_MAX
            and car is not None and not pd.isna(car) and float(car) >= V0_CAR_MIN
        ):
            score += 1
    else:
        de = row.get("debt_to_equity")
        if de is not None and not pd.isna(de) and float(de) <= V0_DEBT_EQUITY_MAX:
            score += 1
    return score


# ─────────────────────────────────────────────────────────────────────
# Canonical — 6-check score per §14.1 (when data lands)
# ─────────────────────────────────────────────────────────────────────
_CANONICAL_REQUIRED = (
    "roe_3y_avg",
    "roce_3y_avg",
    "earnings_cagr_3y",
    "fcf_4q_positive",
    "promoter_buying_6m",
    "fii_dii_qoq_rising",
)


def _has_canonical_columns(row: pd.Series) -> bool:
    """Return True iff every canonical check's column is present."""
    return all(col in row.index for col in _CANONICAL_REQUIRED)


def _canonical_score(row: pd.Series) -> int:
    """Return Tier 2 canonical score 0..6 per §14.1. Each input column
    is treated as a boolean / numeric pass-flag depending on how the
    upstream data source materialises it (this contract is locked at
    the data-source spec time)."""
    score = 0
    roe = row.get("roe_3y_avg")
    if roe is not None and not pd.isna(roe) and float(roe) > CANONICAL_ROE_MIN:
        score += 1
    roce = row.get("roce_3y_avg")
    if roce is not None and not pd.isna(roce) and float(roce) > CANONICAL_ROCE_MIN:
        score += 1
    cagr = row.get("earnings_cagr_3y")
    if (
        cagr is not None
        and not pd.isna(cagr)
        and float(cagr) > CANONICAL_EARNINGS_CAGR_MIN
    ):
        score += 1
    fcf = row.get("fcf_4q_positive")
    if fcf is not None and not pd.isna(fcf) and bool(fcf):
        score += 1
    pb = row.get("promoter_buying_6m")
    if pb is not None and not pd.isna(pb) and bool(pb):
        score += 1
    flow = row.get("fii_dii_qoq_rising")
    if flow is not None and not pd.isna(flow) and bool(flow):
        score += 1
    return score


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────
def compute_tier2_score(
    row: pd.Series,
    *,
    version: Literal["v0", "canonical", "auto"] = "auto",
) -> int:
    """Compute Tier 2 score for one fundamentals row.

    ``version='auto'`` (default) picks ``canonical`` when all six
    required columns are present, otherwise falls back to ``v0``.
    Pin ``version`` explicitly in tests / shadow-mode CRs.
    """
    if version == "canonical" or (version == "auto" and _has_canonical_columns(row)):
        return _canonical_score(row)
    return _v0_score(row)


def tier2_filter(
    fundamentals: pd.DataFrame,
    *,
    threshold: int = 4,
    version: Literal["v0", "canonical", "auto"] = "auto",
) -> pd.DataFrame:
    """Return the rows whose Tier 2 score meets ``threshold``.

    Default threshold = 4 (matches both the v0 ≥ 4 / 5 = 80% and the
    canonical ≥ 4 / 6 = 67% Diamond Layer 3 gate per Sec.6.4).
    """
    scores = fundamentals.apply(
        lambda r: compute_tier2_score(r, version=version), axis=1
    )
    return fundamentals.loc[scores >= threshold]


__all__ = [
    "V0_PROMOTER_HOLDING_MIN",
    "V0_PROMOTER_PLEDGE_MAX",
    "V0_DEBT_EQUITY_MAX",
    "V0_GNPA_MAX",
    "V0_CAR_MIN",
    "CANONICAL_ROE_MIN",
    "CANONICAL_ROCE_MIN",
    "CANONICAL_EARNINGS_CAGR_MIN",
    "compute_tier2_score",
    "tier2_filter",
]
