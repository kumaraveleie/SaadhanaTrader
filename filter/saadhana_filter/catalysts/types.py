"""§13 Phase D catalyst dataclasses + freshness window thresholds.

The ``Catalyst`` shape mirrors the per-row JSON contract emitted to
``signals/research.json`` and ``signals/latest.json`` once integration
lands (Phase D6). Sources never emit raw HTML / PDF text; they emit
already-classified ``Catalyst`` records with a magnitude score so the
downstream consumers (UI, ledger, conviction tier) read a stable
schema regardless of which source produced the record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ──────────────────────────────────────────────────────────────────────
# Catalyst taxonomy (§13.1) — internal canonical keys.
# Adding a new source must NOT introduce new types without spec edit.
# ──────────────────────────────────────────────────────────────────────
CatalystType = Literal[
    "earnings_beat",
    "guidance_raise",
    "buyback",
    "management_change",
    "m_and_a",
    "policy_tailwind",
    "fii_increase",
    "dii_increase",
    "promoter_buying",
    "block_deal_buy",
    "sector_momentum",
]

FreshnessTag = Literal["FRESH", "RECENT", "STALE"]

# Window thresholds (calendar days). FRESH = high decision weight,
# RECENT = surfaces but does not gate, STALE = informational only.
FRESH_DAYS = 7
RECENT_DAYS = 30


def freshness_for(days_old: int) -> FreshnessTag:
    """Map a non-negative ``days_old`` to its freshness bucket."""
    if days_old < 0:
        raise ValueError(f"days_old must be >= 0, got {days_old}")
    if days_old < FRESH_DAYS:
        return "FRESH"
    if days_old < RECENT_DAYS:
        return "RECENT"
    return "STALE"


@dataclass(frozen=True)
class Catalyst:
    """A single classified catalyst event for a symbol."""

    type: CatalystType
    date: str  # ISO YYYY-MM-DD (filing / event date, not scrape date)
    days_old: int
    freshness: FreshnessTag
    source_url: str
    detail: str
    magnitude_score: int  # 0..10; ≥7 (with FRESH) flags high-conviction


@dataclass
class CatalystSummary:
    """Per-symbol roll-up of all catalysts across all sources."""

    symbol: str
    catalysts: list[Catalyst] = field(default_factory=list)
    catalyst_count_fresh: int = 0
    catalyst_count_recent: int = 0
    has_high_conviction_catalyst: bool = False


def catalyst_to_dict(c: Catalyst) -> dict:
    return {
        "type": c.type,
        "date": c.date,
        "days_old": c.days_old,
        "freshness": c.freshness,
        "source_url": c.source_url,
        "detail": c.detail,
        "magnitude_score": c.magnitude_score,
    }


def summary_to_dict(s: CatalystSummary) -> dict:
    return {
        "symbol": s.symbol,
        "catalysts": [catalyst_to_dict(c) for c in s.catalysts],
        "catalyst_count_fresh": s.catalyst_count_fresh,
        "catalyst_count_recent": s.catalyst_count_recent,
        "has_high_conviction_catalyst": s.has_high_conviction_catalyst,
    }
