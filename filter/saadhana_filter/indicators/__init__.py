"""§5 — the 13 technical conditions, plus shared math primitives."""

from saadhana_filter.indicators.conditions import (
    cond_5ema_above_20ema_rising,
    cond_above_50_and_200_ema,
    cond_atr_upside_ge_5pct,
    cond_bb_width_alive,
    cond_distance_to_stop_le_3pct,
    cond_inst_flow_score,
    cond_institutional_flow,
    cond_macd_hist_rising,
    cond_recent_strength_not_extended,
    cond_rr_ge_2,
    cond_rsi_50_70,
    cond_stage_2,
    cond_weekly_hh_hl,
    pro_setup_score,
)
from saadhana_filter.indicators.primitives import (
    atr,
    bollinger_bandwidth,
    ema,
    entry_stop,
    macd,
    rsi,
    rvol,
    sma,
    weekly_resample,
)

__all__ = [
    # primitives
    "atr",
    "bollinger_bandwidth",
    "ema",
    "entry_stop",
    "macd",
    "rsi",
    "rvol",
    "sma",
    "weekly_resample",
    # 13 conditions
    "cond_stage_2",
    "cond_above_50_and_200_ema",
    "cond_5ema_above_20ema_rising",
    "cond_weekly_hh_hl",
    "cond_rsi_50_70",
    "cond_macd_hist_rising",
    "cond_institutional_flow",
    "cond_inst_flow_score",
    "cond_distance_to_stop_le_3pct",
    "cond_atr_upside_ge_5pct",
    "cond_rr_ge_2",
    "cond_recent_strength_not_extended",
    "cond_bb_width_alive",
    # aggregator
    "pro_setup_score",
]
