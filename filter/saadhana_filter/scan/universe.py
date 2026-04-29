"""§2 — universe definition.

Default scope per spec is **Nifty 50** (low noise, high liquidity);
Nifty 500 is opt-in. The list below is a snapshot of the index
composition; treat it as a starting point — the production cron
(Phase M) should refresh from the NSE index file before each scan
to handle additions / deletions.

Symbols use **NSE convention** (no ``.NS`` suffix) — the data loader
appends it for yfinance internally.
"""

from __future__ import annotations

from enum import StrEnum

# Nifty 50 composition snapshot. Production code should refresh from
# https://www.nseindia.com/products/content/equities/indices/nifty_50.htm
# before each scan; this static list lets unit tests run offline and
# gives Phase C an initial universe.
NIFTY_50: tuple[str, ...] = (
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BHARTIARTL",
    "BPCL",
    "BRITANNIA",
    "CIPLA",
    "COALINDIA",
    "DIVISLAB",
    "DRREDDY",
    "EICHERMOT",
    "GRASIM",
    "HCLTECH",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HINDALCO",
    "HINDUNILVR",
    "ICICIBANK",
    "INDUSINDBK",
    "INFY",
    "ITC",
    "JSWSTEEL",
    "KOTAKBANK",
    "LT",
    "LTIM",
    "M&M",
    "MARUTI",
    "NESTLEIND",
    "NTPC",
    "ONGC",
    "POWERGRID",
    "RELIANCE",
    "SBILIFE",
    "SBIN",
    "SHRIRAMFIN",
    "SUNPHARMA",
    "TATACONSUM",
    "TATAMOTORS",
    "TATASTEEL",
    "TCS",
    "TECHM",
    "TITAN",
    "ULTRACEMCO",
    "WIPRO",
)


class UniverseScope(StrEnum):
    """§2 — selectable scan universes."""

    NIFTY_50 = "NIFTY_50"
    NIFTY_500 = "NIFTY_500"
    CUSTOM = "CUSTOM"


def get_universe(scope: UniverseScope = UniverseScope.NIFTY_50) -> tuple[str, ...]:
    """Return the symbol list for ``scope``.

    NIFTY_500 is not yet bundled (production cron pulls it live). For
    Phase C the default — Nifty 50 — is sufficient to satisfy §23's
    definition of done.
    """
    if scope == UniverseScope.NIFTY_50:
        return NIFTY_50
    raise NotImplementedError(
        f"Universe scope {scope.value} not yet bundled — production cron "
        "should pass an explicit symbol list."
    )
