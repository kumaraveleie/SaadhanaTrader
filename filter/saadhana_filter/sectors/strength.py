"""§3.1 Sector Strength v0 — deterministic sector aggregator.

Group ResearchRows by NSE Industry (``sub_industry``) and compute:
  - Today's % change (mean across constituents)
  - Sector-vs-Nifty relative strength over 5d / 20d / 60d
  - Breadth (% above 50-DMA, % above 200-DMA)
  - Top stocks by today's move
  - Institutional footprint (sum 30-bar inst-flow, count of 5d
    buy-bars across constituents) and rank

This is the K1 v0 surface. The full M1 module (Phase Q) replaces
the placeholder ``sector_phase = "Confirming"`` with a real
lead/confirming/mature/fading classifier and adds the catalyst-
sourced "Triggers" section once Phase D ships.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import pandas as pd

from saadhana_filter.catalysts.types import catalyst_to_dict
from saadhana_filter.scan.research import LifecycleTag, ResearchRow

MIN_SECTOR_SIZE = 5  # below this, the sector aggregate is too noisy to surface
TRIGGER_HIGHLIGHTS = 5  # top-N catalysts surfaced per sector for the drill-down


@dataclass
class TopStock:
    symbol: str
    today_pct: float
    pct_change_5d: float
    phase: LifecycleTag
    inst_flow_score_30b: int


@dataclass
class SectorStrength:
    sector: str  # slug e.g. "PHARMACEUTICALS"
    sector_label: str  # human label e.g. "Pharmaceuticals"
    today_pct: float  # decimal — mean of constituent today % changes
    sector_index_change_5d: float | None  # decimal — mean 5d return
    sector_index_change_20d: float | None
    sector_index_change_60d: float | None
    rs_5d: float | None  # ratio sector_return / nifty_return; None if Nifty flat
    rs_20d: float | None
    rs_60d: float | None
    breadth_above_50dma: float  # decimal 0..1
    breadth_above_200dma: float  # decimal 0..1
    sector_phase: str = "Confirming"  # M1 v0 placeholder
    sector_phase_note: str = "Phase Q M1 pending"
    top_stocks: list[TopStock] = field(default_factory=list)
    inst_flow_total: int = 0
    inst_buy_bar_count_5d: int = 0
    sector_count: int = 0
    rank_by_inst_flow: int = 0
    # §13 catalyst rollup across sector constituents — populates the
    # /research drill-down "Triggers" section.
    catalyst_rollup: dict = field(default_factory=dict)


def _slugify(label: str) -> str:
    return (
        label.upper()
        .replace("&", "AND")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )


def _safe_div(num: float, den: float) -> float | None:
    if den == 0 or pd.isna(den):
        return None
    return num / den


def _nifty_window_return(nifty_df: pd.DataFrame, window: int) -> float | None:
    """N-bar return on the Nifty index ending today."""
    close = nifty_df["close"]
    if len(close) <= window:
        return None
    today = float(close.iloc[-1])
    past = float(close.iloc[-(window + 1)])
    if past == 0:
        return None
    return (today - past) / past


def _stock_window_return(
    symbol: str,
    window: int,
    ohlcv_provider: Callable[[str], pd.DataFrame],
) -> float | None:
    try:
        df = ohlcv_provider(symbol)
    except Exception:  # noqa: BLE001
        return None
    if df.empty or "close" not in df.columns:
        return None
    close = df["close"]
    if len(close) <= window:
        return None
    today = float(close.iloc[-1])
    past = float(close.iloc[-(window + 1)])
    if past == 0:
        return None
    return (today - past) / past


def _catalyst_rollup_for(members: list[ResearchRow]) -> dict:
    """Aggregate catalysts across sector constituents.

    Returns a dict with summary counts + the top-N most-recent catalysts
    (one entry per (symbol, catalyst) pair, tagged with the source
    symbol so the UI can route to /stock/[symbol]).
    """
    fresh = sum(r.catalyst_count_fresh for r in members)
    recent = sum(r.catalyst_count_recent for r in members)
    high = sum(1 for r in members if r.has_high_conviction_catalyst)

    flat: list[tuple[str, dict]] = []
    for r in members:
        for c in r.catalysts:
            flat.append((r.symbol, catalyst_to_dict(c)))

    # Sort by date desc (most recent first); ties broken by magnitude desc
    flat.sort(key=lambda pair: (pair[1]["date"], pair[1]["magnitude_score"]), reverse=True)
    highlights = [
        {"symbol": symbol, **catalyst}
        for symbol, catalyst in flat[:TRIGGER_HIGHLIGHTS]
    ]
    return {
        "fresh_count": fresh,
        "recent_count": recent,
        "high_conviction_count": high,
        "highlights": highlights,
    }


def build_sector_strength(
    *,
    rows: list[ResearchRow],
    nifty_df: pd.DataFrame,
    ohlcv_provider: Callable[[str], pd.DataFrame],
    industry_labels: Mapping[str, str] | None = None,
) -> list[SectorStrength]:
    """Build the sector-strength snapshot. Sorted by today_pct descending."""
    if not rows:
        return []

    by_industry: dict[str, list[ResearchRow]] = {}
    for r in rows:
        by_industry.setdefault(r.sub_industry, []).append(r)

    nifty_5d = _nifty_window_return(nifty_df, 5)
    nifty_20d = _nifty_window_return(nifty_df, 20)
    nifty_60d = _nifty_window_return(nifty_df, 60)

    sectors: list[SectorStrength] = []
    for industry_label, members in by_industry.items():
        if len(members) < MIN_SECTOR_SIZE:
            continue
        if industry_label in {"Unknown", "UNKNOWN", ""}:
            continue

        today_pct = sum(r.pct_change_today for r in members) / len(members)
        breadth_50 = sum(1 for r in members if r.dist_from_50dma_pct > 0) / len(members)
        breadth_200 = sum(1 for r in members if r.dist_from_200dma_pct > 0) / len(members)

        # Sector aggregate window returns: average of constituent returns
        ret_5d_vals = [
            v for v in (
                _stock_window_return(r.symbol, 5, ohlcv_provider) for r in members
            ) if v is not None
        ]
        ret_20d_vals = [
            v for v in (
                _stock_window_return(r.symbol, 20, ohlcv_provider) for r in members
            ) if v is not None
        ]
        ret_60d_vals = [
            v for v in (
                _stock_window_return(r.symbol, 60, ohlcv_provider) for r in members
            ) if v is not None
        ]
        sector_5d = sum(ret_5d_vals) / len(ret_5d_vals) if ret_5d_vals else None
        sector_20d = sum(ret_20d_vals) / len(ret_20d_vals) if ret_20d_vals else None
        sector_60d = sum(ret_60d_vals) / len(ret_60d_vals) if ret_60d_vals else None

        rs_5d = (
            _safe_div(1 + sector_5d, 1 + nifty_5d)
            if sector_5d is not None and nifty_5d is not None
            else None
        )
        rs_20d = (
            _safe_div(1 + sector_20d, 1 + nifty_20d)
            if sector_20d is not None and nifty_20d is not None
            else None
        )
        rs_60d = (
            _safe_div(1 + sector_60d, 1 + nifty_60d)
            if sector_60d is not None and nifty_60d is not None
            else None
        )

        top = sorted(members, key=lambda r: r.pct_change_today, reverse=True)[:5]
        top_stocks = [
            TopStock(
                symbol=r.symbol,
                today_pct=r.pct_change_today,
                pct_change_5d=r.pct_change_5d,
                phase=r.lifecycle,
                inst_flow_score_30b=r.inst_flow_score_30b,
            )
            for r in top
        ]

        inst_total = sum(r.inst_flow_score_30b for r in members)
        inst_buy_count = sum(r.inst_buy_bar_count_5d for r in members)

        sectors.append(
            SectorStrength(
                sector=_slugify(industry_label),
                sector_label=(
                    industry_labels.get(industry_label, industry_label)
                    if industry_labels
                    else industry_label
                ),
                today_pct=today_pct,
                sector_index_change_5d=sector_5d,
                sector_index_change_20d=sector_20d,
                sector_index_change_60d=sector_60d,
                rs_5d=rs_5d,
                rs_20d=rs_20d,
                rs_60d=rs_60d,
                breadth_above_50dma=breadth_50,
                breadth_above_200dma=breadth_200,
                top_stocks=top_stocks,
                inst_flow_total=inst_total,
                inst_buy_bar_count_5d=inst_buy_count,
                sector_count=len(members),
                catalyst_rollup=_catalyst_rollup_for(members),
            )
        )

    # Rank by aggregate inst flow (descending)
    sectors_sorted_by_flow = sorted(sectors, key=lambda s: s.inst_flow_total, reverse=True)
    for rank, s in enumerate(sectors_sorted_by_flow, start=1):
        s.rank_by_inst_flow = rank

    # Final order: by today % descending — strongest movers first
    return sorted(sectors, key=lambda s: s.today_pct, reverse=True)


def sector_to_dict(s: SectorStrength) -> dict:
    return {
        "sector": s.sector,
        "sector_label": s.sector_label,
        "today_pct": s.today_pct,
        "sector_index_change_5d": s.sector_index_change_5d,
        "sector_index_change_20d": s.sector_index_change_20d,
        "sector_index_change_60d": s.sector_index_change_60d,
        "rs_5d": s.rs_5d,
        "rs_20d": s.rs_20d,
        "rs_60d": s.rs_60d,
        "breadth_above_50dma": s.breadth_above_50dma,
        "breadth_above_200dma": s.breadth_above_200dma,
        "sector_phase": s.sector_phase,
        "sector_phase_note": s.sector_phase_note,
        "top_stocks": [
            {
                "symbol": t.symbol,
                "today_pct": t.today_pct,
                "pct_change_5d": t.pct_change_5d,
                "phase": t.phase,
                "inst_flow_score_30b": t.inst_flow_score_30b,
            }
            for t in s.top_stocks
        ],
        "inst_flow_total": s.inst_flow_total,
        "inst_buy_bar_count_5d": s.inst_buy_bar_count_5d,
        "sector_count": s.sector_count,
        "rank_by_inst_flow": s.rank_by_inst_flow,
        "catalyst_rollup": s.catalyst_rollup,
    }
