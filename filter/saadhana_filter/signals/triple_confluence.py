"""§5.10 — Triple confluence scoring + candidate function.

Combines the three trend-flavoured indicators (Sec.5.7 MA crossover,
Sec.5.8 Adaptive SuperTrend, Sec.5.9 Deviation Trend) into the
**Triple confluence cohort**. Each component is invoked independently
on the same ``df`` and ``on_bar``; the cohort score is the count of
components with ``qualified=True AND direction=+1``.

Tiering (count-based, NOT weighted score):
    0 / 1 of 3  → not a candidate
    2 of 3      → medium conviction (STANDARD §10 sizing)
    3 of 3      → high conviction (HIGH §10 sizing per §14)

Bearish abstention semantics (spec §5.10 edge case): components whose
``direction == -1`` are recorded in ``agreeing_components`` metadata
under a ``bearish`` bucket but DO NOT count against the bullish
score. Insufficient-history abstentions also don't count — they cap
the score (3-of-3 is impossible until full history).
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

from saadhana_filter.indicators.adaptive_supertrend import (
    AdaptiveSuperTrendResult,
    compute_adaptive_supertrend,
)
from saadhana_filter.indicators.deviation_trend import (
    DeviationTrendResult,
    compute_deviation_trend,
)
from saadhana_filter.indicators.ma_crossover import (
    MACrossoverResult,
    compute_ma_crossover,
)

COMPONENT_NAMES: tuple[str, ...] = ("ma_crossover", "adaptive_st", "deviation_trend")


class TripleConfluenceResult(TypedDict, total=False):
    qualified: bool
    conviction: str  # 'medium' | 'high' | 'none'
    score: int
    agreeing_components: list[str]
    bearish_components: list[str]
    ma_crossover: MACrossoverResult
    adaptive_st: AdaptiveSuperTrendResult
    deviation_trend: DeviationTrendResult


def _is_bullish_qualified(component: dict) -> bool:
    """A component contributes to the bullish score when it both
    ``qualified=True`` AND ``direction=+1``. ``direction`` is
    optional on Sec.5.7 (no direction field) — for that case
    ``qualified=True`` alone is sufficient since the indicator
    has no bearish form."""
    if not component.get("qualified"):
        return False
    direction = component.get("direction")
    if direction is None:
        return True
    return direction == 1


def _is_bearish(component: dict) -> bool:
    """A component is *bearish* when its current direction is -1 —
    independent of qualified-flag (Adaptive SuperTrend and Deviation
    Trend can be in -1 even without a qualifying flip).
    """
    return component.get("direction") == -1


def candidate_triple_confluence(
    df: pd.DataFrame,
    *,
    on_bar: int | None = None,
    ma_crossover_kwargs: dict | None = None,
    adaptive_st_kwargs: dict | None = None,
    deviation_trend_kwargs: dict | None = None,
) -> TripleConfluenceResult:
    """Sec.5.10 candidate function — referenced by §14a registry as
    ``saadhana_filter.signals.candidate_triple_confluence``.

    The three component-specific kwargs let the cohort tune each
    indicator's defaults without breaking out of this single call;
    the daily scan passes them through unchanged.
    """
    if on_bar is None:
        on_bar = len(df) - 1

    ma = compute_ma_crossover(df, on_bar=on_bar, **(ma_crossover_kwargs or {}))
    ast = compute_adaptive_supertrend(df, on_bar=on_bar, **(adaptive_st_kwargs or {}))
    dev = compute_deviation_trend(df, on_bar=on_bar, **(deviation_trend_kwargs or {}))

    components: dict[str, dict] = {
        "ma_crossover": dict(ma),
        "adaptive_st": dict(ast),
        "deviation_trend": dict(dev),
    }

    agreeing = [name for name, comp in components.items() if _is_bullish_qualified(comp)]
    bearish = [name for name, comp in components.items() if _is_bearish(comp)]
    score = len(agreeing)

    if score >= 3:
        conviction = "high"
        qualified = True
    elif score == 2:
        conviction = "medium"
        qualified = True
    else:
        conviction = "none"
        qualified = False

    return TripleConfluenceResult(
        qualified=qualified,
        conviction=conviction,
        score=score,
        agreeing_components=agreeing,
        bearish_components=bearish,
        ma_crossover=ma,
        adaptive_st=ast,
        deviation_trend=dev,
    )
