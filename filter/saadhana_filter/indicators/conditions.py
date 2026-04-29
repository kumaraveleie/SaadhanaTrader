"""§5 — the 13 BUY-entry conditions.

Each ``cond_*`` function is a pure transform that takes an OHLCV frame
(``open, high, low, close, volume`` columns, datetime index) and returns
a ``pd.Series[bool]`` aligned to the input index. ``True`` on a bar means
that condition is met **on that bar**; bars where lookback is incomplete
are ``False`` (never ``NaN`` — downstream aggregation is allowed to sum).

The single-argument shape keeps tests trivial and matches what the
TypeScript mirror in ``trader/app/lib/indicators/`` will expose. A few
conditions share an intermediate computation (entry stop, ATR-projected
target); those primitives live in :mod:`saadhana_filter.indicators.primitives`.

Spec-section markers in each docstring are load-bearing — §16 drift
detection greps for them.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

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

# ──────────────────────────────────────────────────────────────────────────
# Tunables (carried verbatim from spec §5)
# ──────────────────────────────────────────────────────────────────────────
HEAVY_BUY_RVOL = 1.5
INSTITUTIONAL_BUY_RVOL = 2.5
INST_FLOW_LOOKBACK = 30
INST_FLOW_5D_WINDOW = 5
RSI_LOWER, RSI_UPPER = 50.0, 70.0
WEEKLY_HHHL_LOOKBACK = 8  # weeks
WEEKLY_HHHL_HALF = 4
DISTANCE_TO_STOP_MAX_PCT = 0.03
ATR_TARGET_DAYS = 20
MIN_UPSIDE_PCT = 0.05
MIN_RR_RATIO = 2.0
EXTENDED_NEAR_52WH_PCT = 0.02
BASE_LOOKBACK_BARS = 25  # ≈ 5 weeks of trading days
BASE_TIGHTNESS_PCT = 0.10
BREAKOUT_LOOKBACK = 3
BB_MEDIAN_LOOKBACK = 30


def _empty_bool(idx: pd.Index) -> pd.Series:
    return pd.Series(False, index=idx, dtype=bool)


# ──────────────────────────────────────────────────────────────────────────
# §5.1 Trend qualification
# ──────────────────────────────────────────────────────────────────────────
def cond_stage_2(df: pd.DataFrame) -> pd.Series:
    """§5.1 #1 — close > 30-week SMA AND 30W SMA is rising.

    30W SMA is computed on daily close as 150-bar SMA (≈ 30 weeks of
    trading days). "Rising" = today's SMA > yesterday's.
    """
    sma_30w = sma(df["close"], 150)
    rising = sma_30w.diff() > 0
    above = df["close"] > sma_30w
    return (above & rising).fillna(False)


def cond_above_50_and_200_ema(df: pd.DataFrame) -> pd.Series:
    """§5.1 #2 — Price > 50-EMA AND Price > 200-EMA."""
    e50 = ema(df["close"], 50)
    e200 = ema(df["close"], 200)
    return ((df["close"] > e50) & (df["close"] > e200)).fillna(False)


def cond_5ema_above_20ema_rising(df: pd.DataFrame) -> pd.Series:
    """§5.1 #3 — 5-EMA > 20-EMA AND 5-EMA rising bar-over-bar."""
    e5 = ema(df["close"], 5)
    e20 = ema(df["close"], 20)
    rising = e5.diff() > 0
    return ((e5 > e20) & rising).fillna(False)


def cond_weekly_hh_hl(df: pd.DataFrame) -> pd.Series:
    """§5.1 #4 — Higher-highs / higher-lows on weekly chart, last 8 weeks.

    Resamples to weekly bars and asks: in the most recent 8 weekly bars,
    is the *late half* (4 weeks) ``max(high)`` > the *early half*
    ``max(high)`` AND late-half ``min(low)`` > early-half ``min(low)``?
    Both conditions must hold to satisfy "HH/HL structure".

    Result is forward-filled to all daily bars within the qualifying
    week so the daily condition vector is dense.
    """
    weekly = weekly_resample(df)
    if len(weekly) < WEEKLY_HHHL_LOOKBACK:
        return _empty_bool(df.index)

    late_high = weekly["high"].rolling(WEEKLY_HHHL_HALF, min_periods=WEEKLY_HHHL_HALF).max()
    early_high = (
        weekly["high"]
        .shift(WEEKLY_HHHL_HALF)
        .rolling(WEEKLY_HHHL_HALF, min_periods=WEEKLY_HHHL_HALF)
        .max()
    )
    late_low = weekly["low"].rolling(WEEKLY_HHHL_HALF, min_periods=WEEKLY_HHHL_HALF).min()
    early_low = (
        weekly["low"]
        .shift(WEEKLY_HHHL_HALF)
        .rolling(WEEKLY_HHHL_HALF, min_periods=WEEKLY_HHHL_HALF)
        .min()
    )
    weekly_flag = ((late_high > early_high) & (late_low > early_low)).fillna(False).astype(bool)

    # Map weekly flag onto daily index. Each daily bar inherits the most
    # recent *completed* week's flag (forward-fill from weekly close
    # dates, which fall on Fridays).
    daily_flag = weekly_flag.reindex(weekly_flag.index.union(df.index)).ffill()
    return daily_flag.reindex(df.index).fillna(False).astype(bool)


# ──────────────────────────────────────────────────────────────────────────
# §5.2 Momentum qualification
# ──────────────────────────────────────────────────────────────────────────
def cond_rsi_50_70(df: pd.DataFrame) -> pd.Series:
    """§5.2 #5 — RSI(14) ∈ [50, 70]. Inclusive on both ends per spec phrasing."""
    r = rsi(df["close"], 14)
    return ((r >= RSI_LOWER) & (r <= RSI_UPPER)).fillna(False)


def cond_macd_hist_rising(df: pd.DataFrame) -> pd.Series:
    """§5.2 #6 — MACD histogram > 0 AND rising bar-over-bar."""
    h = macd(df["close"])["hist"]
    return ((h > 0) & (h.diff() > 0)).fillna(False)


# ──────────────────────────────────────────────────────────────────────────
# §5.3 Volume / accumulation qualification
# ──────────────────────────────────────────────────────────────────────────
def _flow_flags(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return (heavy_buy_or_better, heavy_sell_or_worse) per-bar flags.

    A "buy" bar is an up-close with RVOL ≥ 1.5x; "sell" is a down-close
    with RVOL ≥ 1.5x. Equal-close bars contribute to neither side.
    """
    up_bar = df["close"] > df["open"]
    down_bar = df["close"] < df["open"]
    r = rvol(df["volume"], 50)
    heavy = r >= HEAVY_BUY_RVOL
    return (heavy & up_bar).fillna(False), (heavy & down_bar).fillna(False)


def cond_institutional_flow(df: pd.DataFrame) -> pd.Series:
    """§5.3 #7 — Institutional Buy or Heavy Buy in the **last 5** trading days.

    Heavy Buy = up-bar AND RVOL ≥ 1.5; Institutional Buy = up-bar AND RVOL
    ≥ 2.5. Either qualifies. The condition is True on bar t if any bar in
    ``[t-4 .. t]`` (5 bars inclusive of today) is a heavy-or-institutional
    buy.
    """
    buys, _sells = _flow_flags(df)
    return buys.rolling(INST_FLOW_5D_WINDOW, min_periods=1).sum().gt(0).fillna(False)


def cond_inst_flow_score(df: pd.DataFrame) -> pd.Series:
    """§5.3 #8 — 30-bar Institutional Flow Score > 0.

    Score = ``Σ_buy − Σ_sell`` over a rolling 30-bar window.
    """
    buys, sells = _flow_flags(df)
    score = (
        buys.rolling(INST_FLOW_LOOKBACK, min_periods=INST_FLOW_LOOKBACK).sum()
        - sells.rolling(INST_FLOW_LOOKBACK, min_periods=INST_FLOW_LOOKBACK).sum()
    )
    return (score > 0).fillna(False)


# ──────────────────────────────────────────────────────────────────────────
# §5.4 Risk qualification
# ──────────────────────────────────────────────────────────────────────────
def _atr_target_components(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Compute (stop, target, risk_pct, reward_pct) used by §5.4 conditions.

    - ``stop``    = entry_stop primitive (max of 20-EMA, 5-bar low − ATR×0.5)
    - ``high52``  = trailing 52-week high (252 bars), excludes today
    - ``target``  = min(close + ATR(14)×20, high52)  — ATR-feasible upside
                    capped at the nearest resistance
    - ``risk_pct``    = (close − stop) / close
    - ``reward_pct``  = (target − close) / close
    """
    close = df["close"]
    a = atr(df, 14)
    stop = entry_stop(df, atr_series=a)
    high52 = df["high"].shift(1).rolling(252, min_periods=60).max()
    atr_target = close + a * ATR_TARGET_DAYS
    # When close has already taken out the prior 52-week high, the
    # resistance leg is "open territory" — only the ATR projection caps
    # the target. Equivalent: drop high52 from the min when it sits at
    # or below close.
    resistance = high52.where(high52 > close)
    target = pd.concat([atr_target, resistance], axis=1).min(axis=1, skipna=True)
    risk_pct = (close - stop) / close
    reward_pct = (target - close) / close
    return stop, target, risk_pct, reward_pct


def cond_distance_to_stop_le_3pct(df: pd.DataFrame) -> pd.Series:
    """§5.4 #9 — Distance to entry stop ≤ 3% of close.

    Stop must be **below** close (positive risk) and the gap must not
    exceed 3%. A trade where the stop sits above price is not a long
    setup and resolves False.
    """
    _stop, _target, risk_pct, _reward = _atr_target_components(df)
    return ((risk_pct > 0) & (risk_pct <= DISTANCE_TO_STOP_MAX_PCT)).fillna(False)


def cond_atr_upside_ge_5pct(df: pd.DataFrame) -> pd.Series:
    """§5.4 #10 — ATR-projected upside to nearest resistance ≥ 5%.

    The reward leg uses ``min(ATR×20, resistance − close)``, so this
    condition asserts that **both** the volatility budget and the room
    to the nearest resistance support a ≥ 5% move.
    """
    _stop, _target, _risk, reward_pct = _atr_target_components(df)
    return (reward_pct >= MIN_UPSIDE_PCT).fillna(False)


def cond_rr_ge_2(df: pd.DataFrame) -> pd.Series:
    """§5.4 #11 — Risk / Reward ratio ≥ 2:1 (reward ≥ 2× risk)."""
    _stop, _target, risk_pct, reward_pct = _atr_target_components(df)
    safe_risk = risk_pct.where(risk_pct > 0, np.nan)
    rr = reward_pct / safe_risk
    return (rr >= MIN_RR_RATIO).fillna(False)


# ──────────────────────────────────────────────────────────────────────────
# §5.5 Not-extended qualification
# ──────────────────────────────────────────────────────────────────────────
def _fresh_breakout(df: pd.DataFrame) -> pd.Series:
    """Helper: True on bar t if the last 3 bars contain a break above a
    ≥ 5-week tight base (range ≤ 10%).

    The base window is the 25 bars *before* the breakout candle.
    """
    close = df["close"]
    prior_max = close.shift(1).rolling(BASE_LOOKBACK_BARS, min_periods=BASE_LOOKBACK_BARS).max()
    prior_min = close.shift(1).rolling(BASE_LOOKBACK_BARS, min_periods=BASE_LOOKBACK_BARS).min()
    tight = ((prior_max - prior_min) / prior_min).fillna(np.inf) <= BASE_TIGHTNESS_PCT
    breaks_out = close > prior_max
    candle_break = (breaks_out & tight).fillna(False)
    # broaden to "any of the last 3 bars was a breakout candle"
    return candle_break.rolling(BREAKOUT_LOOKBACK, min_periods=1).max().astype(bool)


def cond_not_extended(df: pd.DataFrame) -> pd.Series:
    """§5.5 #12 — NOT within 2% of 52-week high, **unless** a fresh
    breakout from a base of ≥ 5 weeks happened in the last 3 bars."""
    close = df["close"]
    high52 = df["high"].rolling(252, min_periods=60).max()
    near_top = close >= (1 - EXTENDED_NEAR_52WH_PCT) * high52
    breakout = _fresh_breakout(df)
    return ((~near_top) | breakout).fillna(False)


def cond_bb_width_alive(df: pd.DataFrame) -> pd.Series:
    """§5.5 #13 — BB Width > 30-bar median, OR price has just broken
    out of consolidation in the last 3 bars."""
    bbw = bollinger_bandwidth(df["close"], 20, 2.0)
    bbw_median = bbw.rolling(BB_MEDIAN_LOOKBACK, min_periods=BB_MEDIAN_LOOKBACK).median()
    alive = (bbw > bbw_median).fillna(False)
    breakout = _fresh_breakout(df)
    return (alive | breakout).fillna(False)


# ──────────────────────────────────────────────────────────────────────────
# §5 — Pro-Setup Score aggregator
# ──────────────────────────────────────────────────────────────────────────
ALL_CONDITIONS: tuple[tuple[str, Callable[[pd.DataFrame], pd.Series]], ...] = (
    ("stage_2", cond_stage_2),
    ("above_50_and_200_ema", cond_above_50_and_200_ema),
    ("5ema_above_20ema_rising", cond_5ema_above_20ema_rising),
    ("weekly_hh_hl", cond_weekly_hh_hl),
    ("rsi_50_70", cond_rsi_50_70),
    ("macd_hist_rising", cond_macd_hist_rising),
    ("institutional_flow", cond_institutional_flow),
    ("inst_flow_score", cond_inst_flow_score),
    ("distance_to_stop_le_3pct", cond_distance_to_stop_le_3pct),
    ("atr_upside_ge_5pct", cond_atr_upside_ge_5pct),
    ("rr_ge_2", cond_rr_ge_2),
    ("not_extended", cond_not_extended),
    ("bb_width_alive", cond_bb_width_alive),
)
"""(name, function) pairs in spec order — used by the score aggregator,
the ledger snapshot writer (Phase H) and the parity tests (§16)."""


def pro_setup_score(df: pd.DataFrame) -> pd.DataFrame:
    """§5 — return a frame with one bool column per condition plus a
    ``score`` integer column (0..13).

    A BUY candidate per spec is ``score == 13``. WATCH = 10–12. Below 10
    is WAIT.
    """
    cols = {name: fn(df).astype(bool) for name, fn in ALL_CONDITIONS}
    out = pd.DataFrame(cols, index=df.index)
    out["score"] = out.sum(axis=1).astype("int64")
    return out
