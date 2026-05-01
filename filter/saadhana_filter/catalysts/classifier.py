"""§13.1 deterministic filing-text → catalyst-type classifier.

Keyword-based, fully deterministic — no LLM, no probabilistic scoring.
Phase E layers an LLM news-classification source on top, but Phase D
keeps the classifier auditable: every catalyst tag is reproducible by
re-running the same input through the same keyword rules.

Design notes:
- Order of checks matters. We test the higher-precedence catalyst types
  first (buyback / m_and_a / mgmt change) before falling through to
  earnings semantics, so a "buyback announced after Q4 results" filing
  classifies as ``buyback`` (more specific) rather than
  ``earnings_beat``.
- Classifier returns ``None`` when no rule fires; the caller drops the
  filing rather than emitting a low-confidence catalyst.
"""

from __future__ import annotations

from saadhana_filter.catalysts.types import CatalystType

# Keyword sets — case-insensitive matched on the concatenated title+body.
# Curated from a sample of BSE/NSE filings; extend as new patterns surface.
_BUYBACK_KEYWORDS = (
    "buyback",
    "buy back",
    "buy-back",
    "share repurchase",
)
_M_AND_A_KEYWORDS = (
    "acquisition of",
    "acquired ",
    "merger",
    "scheme of arrangement",
    "amalgamation",
    "asset purchase",
)
_MGMT_KEYWORDS = (
    "resignation of",
    "resigned",
    "stepped down",
    "appointed as managing director",
    "appointed as ceo",
    "appointment of managing director",
    "appointment of chief executive",
    "new managing director",
    "new ceo",
)
_GUIDANCE_RAISE_KEYWORDS = (
    "raised guidance",
    "raised outlook",
    "upward revision",
    "increased outlook",
    "guidance upgraded",
)
_EARNINGS_KEYWORDS = (
    "quarterly result",
    "quarterly results",
    "annual result",
    "annual results",
    "earnings",
    "q1 fy",
    "q2 fy",
    "q3 fy",
    "q4 fy",
)
_EARNINGS_BEAT_KEYWORDS = (
    "beat estimates",
    "beat consensus",
    "exceeded estimates",
    "exceeded consensus",
    "ahead of estimates",
    "above estimates",
)
_STRONG_KEYWORDS = (
    "significantly",
    "double-digit",
    "doubled",
    "major",
    "substantial",
)


def _hit(text: str, keywords: tuple[str, ...]) -> bool:
    return any(k in text for k in keywords)


def classify_filing(title: str, body: str) -> CatalystType | None:
    """Map a corporate filing's title + body to a catalyst type, or ``None``."""
    text = f"{title} {body}".lower()

    # Higher-precedence types first — a "buyback announced alongside Q4
    # results" filing should classify as buyback, not earnings_beat.
    if _hit(text, _BUYBACK_KEYWORDS):
        return "buyback"
    if _hit(text, _M_AND_A_KEYWORDS):
        return "m_and_a"
    if _hit(text, _MGMT_KEYWORDS):
        return "management_change"
    if _hit(text, _GUIDANCE_RAISE_KEYWORDS):
        return "guidance_raise"

    # Earnings — only positive (beat / exceeded). A bare quarterly-result
    # filing without an explicit beat signal is uninformative noise; we
    # drop it rather than tagging every quarterly announcement.
    if _hit(text, _EARNINGS_KEYWORDS) and _hit(text, _EARNINGS_BEAT_KEYWORDS):
        return "earnings_beat"

    return None


# ──────────────────────────────────────────────────────────────────────
# Magnitude scoring (0..10, deterministic).
# ──────────────────────────────────────────────────────────────────────
_BASE_MAGNITUDE: dict[CatalystType, int] = {
    "earnings_beat": 6,
    "guidance_raise": 7,
    "buyback": 6,
    "management_change": 5,
    "m_and_a": 7,
    "policy_tailwind": 6,
    "fii_increase": 5,
    "dii_increase": 5,
    "promoter_buying": 7,
    "promoter_selling": 5,
    "insider_buying": 4,
    "block_deal_buy": 5,
    "block_deal_sell": 5,
    "sector_momentum": 4,
}


def magnitude_score(text: str, catalyst_type: CatalystType) -> int:
    """Return a deterministic 0..10 magnitude for the catalyst.

    Base score is per type; "strength" keywords (``significantly``,
    ``double-digit``, etc.) bump it up by 2. Multiple hits cap at +3.
    """
    if catalyst_type not in _BASE_MAGNITUDE:
        raise ValueError(f"Unknown catalyst type: {catalyst_type}")
    text_l = text.lower()
    base = _BASE_MAGNITUDE[catalyst_type]
    strength_hits = sum(1 for kw in _STRONG_KEYWORDS if kw in text_l)
    boost = min(3, strength_hits * 2)
    return min(10, max(0, base + boost))
