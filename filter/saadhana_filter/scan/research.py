"""§21.1 /research-page data generator.

Computes a per-symbol indicator snapshot for every Tier-1-passing
symbol in the universe — independent of whether the symbol qualifies
for a §5 BUY today. The output feeds the public ``/research`` page,
which surfaces three panels (Sector Strength stub for Phase Q/M1,
52WH Breakout Watch, Strength Despite Weakness).

The lifecycle classifier here is the **K1 placeholder** for the M2
Pattern Lifecycle Engine (`spec/thinking_engine.md` §7). The full
6-marker classifier ships in Phase R; this 4-bucket simplification
(INITIAL / CONFIRMED / LATE / UNKNOWN) is sufficient to surface the
"don't chase exhaustion gaps" signal in the meantime.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd

from saadhana_filter.indicators.conditions import (
    INST_FLOW_LOOKBACK,
    pro_setup_score,
)
from saadhana_filter.indicators.primitives import (
    bollinger_bandwidth,
    rsi,
    sma,
)

LifecycleTag = Literal["INITIAL", "CONFIRMED", "LATE", "UNKNOWN"]

# Lifecycle classifier thresholds (K1 v1; the M2/Phase R version
# replaces these with a 6-marker design).
LATE_RSI = 80.0
LATE_DIST_FROM_50DMA_PCT = 0.15
LATE_BARS_SINCE_52WH_BREAK = 5
LATE_BB_WIDTH_OVER_MEDIAN = 2.0

INITIAL_BARS_SINCE_PIVOT_BREAK = 15
INITIAL_DIST_FROM_50DMA_PCT = 0.05
INITIAL_RSI_LOW = 55.0
INITIAL_RSI_HIGH = 70.0

CONFIRMED_MIN_PROSETUP_SCORE = 11

NEAR_52WH_PCT = 0.05  # within 5% of 52-week high


@dataclass
class ResearchRow:
    """One per-symbol snapshot row emitted to ``signals/research.json``."""

    symbol: str
    sector: str

    # Price action vs Nifty
    close_today: float
    close_yesterday: float
    pct_change_today: float  # decimal, e.g. 0.024 = +2.4%

    # Distance / context
    dist_from_50dma_pct: float  # decimal
    dist_from_52wh_pct: float  # decimal; negative = below 52WH
    bars_since_52wh_break: int | None  # None = price never broke 52WH recently

    # Indicators
    rsi_14: float
    bb_width_pct: float
    bb_width_over_median: float
    inst_flow_score_30b: int

    # Score + lifecycle
    pro_setup_score: int
    lifecycle: LifecycleTag


@dataclass
class ResearchSnapshot:
    """Top-level payload written to ``signals/research.json``."""

    scan_date: str
    spec_version: str
    universe_size: int
    tier1_passed: int
    nifty_close_today: float
    nifty_close_yesterday: float
    nifty_pct_change_today: float
    rows: list[ResearchRow] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
def _bars_since_52wh_break(close: pd.Series, high_52w: pd.Series) -> int | None:
    """How many bars ago did `close` last break above the trailing 52WH?

    A "break" = close > 99.9% of the trailing 252-bar max-of-high. Returns
    None if never broke in the available history.
    """
    breaks = close >= high_52w * 0.999
    if not breaks.any():
        return None
    last_break_pos = breaks.values.nonzero()[0][-1]
    last_idx = len(close) - 1
    return int(last_idx - last_break_pos)


def _classify_lifecycle(
    *,
    rsi_14: float,
    dist_from_50dma_pct: float,
    bars_since_52wh_break: int | None,
    bb_width_over_median: float,
    inst_flow_score_30b: int,
    pro_setup_score: int,
) -> LifecycleTag:
    """K1 v1 lifecycle classifier — see module docstring."""
    # LATE — any of the three exhaustion markers
    if rsi_14 > LATE_RSI:
        return "LATE"
    if dist_from_50dma_pct > LATE_DIST_FROM_50DMA_PCT:
        return "LATE"
    if (
        bars_since_52wh_break is not None
        and bars_since_52wh_break < LATE_BARS_SINCE_52WH_BREAK
        and bb_width_over_median > LATE_BB_WIDTH_OVER_MEDIAN
    ):
        return "LATE"

    # INITIAL — fresh strength, all four conditions
    initial_bars_ok = (
        bars_since_52wh_break is not None
        and bars_since_52wh_break < INITIAL_BARS_SINCE_PIVOT_BREAK
    )
    if (
        initial_bars_ok
        and dist_from_50dma_pct < INITIAL_DIST_FROM_50DMA_PCT
        and INITIAL_RSI_LOW <= rsi_14 <= INITIAL_RSI_HIGH
        and inst_flow_score_30b > 0
    ):
        return "INITIAL"

    # CONFIRMED — trend running, score-gated
    if pro_setup_score >= CONFIRMED_MIN_PROSETUP_SCORE:
        return "CONFIRMED"

    return "UNKNOWN"


def _row_for(
    symbol: str,
    df: pd.DataFrame,
    sector: str,
) -> ResearchRow | None:
    """Compute the per-symbol research snapshot. Returns None if the
    underlying data lacks the lookback our indicators need."""
    if len(df) < 252:
        return None

    close = df["close"]
    high = df["high"]

    close_today = float(close.iloc[-1])
    close_yesterday = float(close.iloc[-2])
    pct_change_today = (close_today - close_yesterday) / close_yesterday

    sma_50 = sma(close, 50)
    sma_50_today = float(sma_50.iloc[-1])
    dist_from_50dma_pct = (close_today - sma_50_today) / sma_50_today

    high_52w = high.rolling(252, min_periods=60).max()
    high_52w_today = float(high_52w.iloc[-1])
    dist_from_52wh_pct = (close_today - high_52w_today) / high_52w_today
    bars_since = _bars_since_52wh_break(close, high_52w)

    rsi_series = rsi(close, 14)
    rsi_14 = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0

    bbw = bollinger_bandwidth(close, 20, 2.0)
    bbw_today = float(bbw.iloc[-1]) if not pd.isna(bbw.iloc[-1]) else 0.0
    bbw_median_30b = float(bbw.rolling(30, min_periods=30).median().iloc[-1])
    bbw_over_median = bbw_today / bbw_median_30b if bbw_median_30b > 0 else 0.0

    score_panel = pro_setup_score(df)
    score_today = int(score_panel["score"].iloc[-1])

    # Inst. flow score = 30-bar net buy/sell from the existing primitive
    # The pro_setup_score panel already includes ``inst_flow_score`` as a
    # boolean (>0 net); we want the actual integer count for the table.
    from saadhana_filter.indicators.conditions import _flow_flags

    buys, sells = _flow_flags(df)
    score_30b = int(
        (buys.rolling(INST_FLOW_LOOKBACK, min_periods=INST_FLOW_LOOKBACK).sum()
         - sells.rolling(INST_FLOW_LOOKBACK, min_periods=INST_FLOW_LOOKBACK).sum()).iloc[-1]
    )

    lifecycle = _classify_lifecycle(
        rsi_14=rsi_14,
        dist_from_50dma_pct=dist_from_50dma_pct,
        bars_since_52wh_break=bars_since,
        bb_width_over_median=bbw_over_median,
        inst_flow_score_30b=score_30b,
        pro_setup_score=score_today,
    )

    return ResearchRow(
        symbol=symbol,
        sector=sector,
        close_today=close_today,
        close_yesterday=close_yesterday,
        pct_change_today=pct_change_today,
        dist_from_50dma_pct=dist_from_50dma_pct,
        dist_from_52wh_pct=dist_from_52wh_pct,
        bars_since_52wh_break=bars_since,
        rsi_14=rsi_14,
        bb_width_pct=bbw_today,
        bb_width_over_median=bbw_over_median,
        inst_flow_score_30b=score_30b,
        pro_setup_score=score_today,
        lifecycle=lifecycle,
    )


# ──────────────────────────────────────────────────────────────────────────
# Main entry — generates the full snapshot
# ──────────────────────────────────────────────────────────────────────────
def build_research_snapshot(
    *,
    scan_date: date,
    spec_version: str,
    universe: tuple[str, ...],
    fundamentals_passed: set[str],
    sectors: Mapping[str, str],
    nifty_df: pd.DataFrame,
    ohlcv_provider: Callable[[str], pd.DataFrame],
) -> ResearchSnapshot:
    """Build the per-symbol research snapshot for ``/research``.

    Only Tier-1-passing symbols are included — research-mode UX still
    respects the §4 fundamental gate even though it's a non-trading
    surface. Symbols missing OHLCV or with insufficient lookback are
    skipped silently.
    """
    nifty_close_today = float(nifty_df["close"].iloc[-1])
    nifty_close_yesterday = float(nifty_df["close"].iloc[-2])
    nifty_pct_change = (nifty_close_today - nifty_close_yesterday) / nifty_close_yesterday

    rows: list[ResearchRow] = []
    for symbol in universe:
        if symbol not in fundamentals_passed:
            continue
        try:
            df = ohlcv_provider(symbol)
        except Exception:  # noqa: BLE001 — best-effort per-symbol
            continue
        if df.empty:
            continue
        sector = sectors.get(symbol, "UNKNOWN")
        row = _row_for(symbol, df, sector)
        if row is not None:
            rows.append(row)

    return ResearchSnapshot(
        scan_date=scan_date.isoformat(),
        spec_version=spec_version,
        universe_size=len(universe),
        tier1_passed=len(fundamentals_passed),
        nifty_close_today=nifty_close_today,
        nifty_close_yesterday=nifty_close_yesterday,
        nifty_pct_change_today=nifty_pct_change,
        rows=rows,
    )


def snapshot_to_dict(snap: ResearchSnapshot) -> dict:
    """JSON-friendly dict mirror of ResearchSnapshot."""
    return {
        "scan_date": snap.scan_date,
        "spec_version": snap.spec_version,
        "universe_size": snap.universe_size,
        "tier1_passed": snap.tier1_passed,
        "nifty_close_today": snap.nifty_close_today,
        "nifty_close_yesterday": snap.nifty_close_yesterday,
        "nifty_pct_change_today": snap.nifty_pct_change_today,
        "rows": [
            {
                "symbol": r.symbol,
                "sector": r.sector,
                "close_today": r.close_today,
                "close_yesterday": r.close_yesterday,
                "pct_change_today": r.pct_change_today,
                "dist_from_50dma_pct": r.dist_from_50dma_pct,
                "dist_from_52wh_pct": r.dist_from_52wh_pct,
                "bars_since_52wh_break": r.bars_since_52wh_break,
                "rsi_14": r.rsi_14,
                "bb_width_pct": r.bb_width_pct,
                "bb_width_over_median": r.bb_width_over_median,
                "inst_flow_score_30b": r.inst_flow_score_30b,
                "pro_setup_score": r.pro_setup_score,
                "lifecycle": r.lifecycle,
            }
            for r in snap.rows
        ],
    }


def filter_strength_despite_weakness(snap: ResearchSnapshot) -> list[ResearchRow]:
    """Apply the K1 'Strength Despite Weakness' panel filter:

    - Stock close > yesterday close (positive %change)
    - Nifty close < yesterday close (Nifty negative %change)
    - Stock within 5% of 52WH OR closed above 52WH today
    - (Tier 1 already enforced upstream)

    Returns rows in the panel's required sort order: lifecycle bucket
    first (INITIAL → CONFIRMED → LATE → UNKNOWN), then descending
    distance from 52WH (closer first / less negative first).
    """
    if snap.nifty_pct_change_today >= 0:
        return []  # Panel requires Nifty down — surface nothing if market is up

    matches = [
        r
        for r in snap.rows
        if r.pct_change_today > 0
        and (r.dist_from_52wh_pct >= -NEAR_52WH_PCT)
    ]

    bucket_order = {"INITIAL": 0, "CONFIRMED": 1, "LATE": 2, "UNKNOWN": 3}
    return sorted(
        matches,
        key=lambda r: (bucket_order[r.lifecycle], -r.dist_from_52wh_pct),
    )
