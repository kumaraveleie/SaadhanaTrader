"""§13.1 source 5: sector-momentum catalyst.

Pure classifier wrapper — no fetcher. Reads the sector aggregates
already computed by ``saadhana_filter.sectors.strength`` and emits
``sector_momentum`` catalysts for every constituent of every
qualifying sector.

A sector qualifies when ALL three conditions fire:
  - ``rs_5d > 1.05``                       (sector outperforming Nifty by ≥5% over 5d)
  - ``breadth_above_50dma > 0.55``         (>55% of constituents above 50-DMA)
  - ``sector_index_change_5d > 0``         (sector positive over the 5d window —
                                            not just less negative than Nifty)

The catalyst is identical for every member of the sector (distinguished
only by ``Catalyst.symbol`` when threaded into ``CatalystSummary``).

Magnitude scoring per CR-005-aligned formula::

    base = min(10, sector_index_change_5d * 100 * 2)
    multiplier = 1 + (breadth_above_50dma - 0.5)   # 0.5..1.5
    magnitude = round(base * multiplier)            # int 0..10

Examples:
  +1.5% sector with 70% breadth → base 3.0, mult 1.2 → magnitude 4
  +3.0% sector with 80% breadth → base 6.0, mult 1.3 → magnitude 8
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from saadhana_filter.catalysts.types import Catalyst, freshness_for

RS_5D_THRESHOLD = 1.05
BREADTH_50DMA_THRESHOLD = 0.55


def _qualifies(agg: Mapping) -> bool:
    rs = agg.get("rs_5d")
    breadth = agg.get("breadth_above_50dma")
    change_5d = agg.get("sector_index_change_5d")
    if rs is None or breadth is None or change_5d is None:
        return False
    return (
        rs > RS_5D_THRESHOLD
        and breadth > BREADTH_50DMA_THRESHOLD
        and change_5d > 0
    )


def _magnitude(change_5d: float, breadth: float) -> int:
    base = min(10.0, change_5d * 100 * 2)
    multiplier = 1 + (breadth - 0.5)
    return max(0, min(10, round(base * multiplier)))


def _detail(label: str, change_5d: float, breadth: float) -> str:
    return (
        f"{label} {change_5d * 100:+.2f}% over 5d, "
        f"{round(breadth * 100)}% of constituents above 50-DMA"
    )


def _source_url(slug: str) -> str:
    # Best-effort link to the NSE sectors page; replaced with a per-
    # index URL once the live data path lands in Phase D2.
    return f"https://www.nseindia.com/market-data/sectors-overview?sector={slug}"


def build_sector_momentum_catalysts(
    *,
    today_iso: str,
    sector_aggregates: Iterable[Mapping],
    sector_constituents: Mapping[str, Iterable[str]],
) -> dict[str, list[Catalyst]]:
    """Emit a sector_momentum catalyst for every constituent of every
    qualifying sector.

    Parameters
    ----------
    today_iso
        Scan date in YYYY-MM-DD form. The catalyst's ``date`` and
        ``days_old`` are pinned to today (sector momentum is a
        current-day signal — always FRESH).
    sector_aggregates
        Iterable of dict-shaped sector aggregates. The function reads
        ``sector`` (slug), ``sector_label``, ``rs_5d``,
        ``breadth_above_50dma``, ``today_pct``.
    sector_constituents
        Map ``{sector_slug: [symbol, ...]}``. Each symbol in a
        qualifying sector receives the catalyst.
    """
    out: dict[str, list[Catalyst]] = {}
    for agg in sector_aggregates:
        if not _qualifies(agg):
            continue
        slug = agg["sector"]
        label = agg["sector_label"]
        change_5d = float(agg["sector_index_change_5d"])
        breadth = float(agg["breadth_above_50dma"])
        members = list(sector_constituents.get(slug, []))
        if not members:
            continue
        catalyst = Catalyst(
            type="sector_momentum",
            date=today_iso,
            days_old=0,
            freshness=freshness_for(0),
            source_url=_source_url(slug),
            detail=_detail(label, change_5d, breadth),
            magnitude_score=_magnitude(change_5d, breadth),
        )
        for sym in members:
            out.setdefault(sym, []).append(catalyst)
    return out
