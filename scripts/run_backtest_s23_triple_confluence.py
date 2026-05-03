"""S2.3 — Triple confluence cohort backtest (production path).

Replays the Sec.5.10 Triple confluence cohort on the full InvestQuest
universe over the same 3-year window as the G1 baseline. Generates
`spec/samples/backtest_report_s23_triple_confluence.md` matching the
G1 report schema, plus a JSON trade dump for the per-symbol overlap
analysis vs the parallel verifier.

Usage:
    python scripts/run_backtest_s23_triple_confluence.py
        [--limit N] [--year-window N]
        [--relaxed-scoring]  [--wide-stop]
        [--report-suffix TAG]

Flags:
    --limit N           Limit universe to top-N symbols by market cap.
                        Default: process the full universe (~497).
    --year-window N     Test window in years. Default 3 (matches G1).
    --relaxed-scoring   ASK 6: vote bullish on direction==+1 (drop the
                        fresh-qualified gate from Sec.5.10 scoring).
    --wide-stop         ASK 7: 6%/9% stop/target, 60-bar time stop
                        (TC position-horizon calibration). Keeps R:R
                        at 1.5x.
    --exclude-financials  v2.1 §0.5 mirror: skip universe rows whose
                        sector label contains 'Financial', 'NBFC',
                        or 'Bank' (case-insensitive). v2.1's
                        sector_exclusions=['FINANCIAL_SERVICES',
                        'NBFC', 'BANK'] all collapse to "Financial
                        Services" in the InvestQuest CSV.
    --report-suffix TAG Append "_TAG" to the output filename so paired
                        re-runs don't overwrite each other.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "filter"))

from saadhana_filter.data.loader import load_eod  # noqa: E402
from saadhana_filter.data.universe import load_universe  # noqa: E402
from saadhana_filter.indicators.adaptive_supertrend import (  # noqa: E402
    _kmeans_3_linear_seeds,
)
from saadhana_filter.indicators.ma_crossover import _compute_ma  # noqa: E402
from saadhana_filter.indicators.primitives import atr as wilder_atr  # noqa: E402
from saadhana_filter.indicators.primitives import sma  # noqa: E402

# Risk model — matches the §10 STANDARD tier locked for the
# triple_confluence cohort plus the §7 target ladder. Module-level
# defaults; ``--wide-stop`` overrides at runtime.
ENTRY_STOP_PCT = 0.0385
TARGET_T1_PCT = 0.05
TARGET_T2_PCT = 0.10
TARGET_T3_PCT = 0.15
TIME_STOP_BARS = 25

# Wide-stop variant for the position-horizon TC cohort (Ask 7).
WIDE_ENTRY_STOP_PCT = 0.06
WIDE_TARGET_T1_PCT = 0.05
WIDE_TARGET_T2_PCT = 0.07
WIDE_TARGET_T3_PCT = 0.09
WIDE_TIME_STOP_BARS = 60

# Module-level mutable risk params used by simulate_trade. ``main()``
# patches these when --wide-stop is passed; otherwise they stay at the
# strict §10/§7 defaults.
_RISK = {
    "entry_stop": ENTRY_STOP_PCT,
    "t1": TARGET_T1_PCT,
    "t2": TARGET_T2_PCT,
    "t3": TARGET_T3_PCT,
    "time_stop_bars": TIME_STOP_BARS,
}
# Module-level scoring mode toggle: "strict" (Sec.5.10) or "relaxed"
# (direction-only). Patched by main() when --relaxed-scoring is passed.
_SCORING_MODE = "strict"

# Backtest indicator parameters — match the production candidate
# function defaults so this runner stays in sync with what the daily
# scan uses. If the cohort defaults change, update here too.
MA_FAST_PERIOD = 20
MA_SLOW_PERIOD = 50
MA_TYPE = "TEMA"
MA_SLOPE_WINDOW = 3
MA_DIRECTION_SMOOTHE = 2
MA_SIGNAL_FRESHNESS = 5

AST_ATR_PERIOD = 10
AST_TRAINING_PERIOD = 100
AST_FACTOR = 3.0
AST_SIGNAL_FRESHNESS = 3
AST_CONFIRM_SIGNALS = True

DT_SMA_LENGTH = 50
DT_ATR_LENGTH = 200
DT_SLOPE_LAG = 5
DT_PERCENTILE_WINDOW = 500
DT_SLOPE_THRESHOLD = 0.1
DT_SIGNAL_FRESHNESS = 3


# ─────────────────────────────────────────────────────────────────────
# Fast vectorized trajectory builders
# ─────────────────────────────────────────────────────────────────────
# Each function computes the full per-bar (qualified, direction) trace
# for ONE symbol's df, in a single pass. The backtest scan window then
# reads off the trace at each scan bar — converting the per-symbol
# cost from O(scan_window × n_bars) (the per-call recomputation) to
# O(n_bars) (one pass). On a 750-bar 500-symbol universe this drops
# the runtime from hours to minutes.

def _build_ma_crossover_trace(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Returns (qualified, direction) arrays of length len(df).

    qualified[i] is True iff the bullish-crossover + slope + smoothing
    contract held at bar i looking back signal_freshness_bars.
    direction[i] is +1 when fast > slow at bar i, -1 otherwise.
    """
    n = len(df)
    qualified = np.zeros(n, dtype=bool)
    direction = np.zeros(n, dtype=int)

    fast = _compute_ma(df, n=MA_FAST_PERIOD, ma_type=MA_TYPE, source="close").to_numpy()
    slow = _compute_ma(df, n=MA_SLOW_PERIOD, ma_type="EMA", source="close").to_numpy()

    # Direction at every bar.
    finite = np.isfinite(fast) & np.isfinite(slow)
    direction[finite & (fast > slow)] = +1
    direction[finite & (fast < slow)] = -1

    # Bullish-crossover trace: bar where fast was ≤ slow, now >.
    cross = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not (np.isfinite(fast[i]) and np.isfinite(slow[i])
                and np.isfinite(fast[i - 1]) and np.isfinite(slow[i - 1])):
            continue
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
            cross[i] = True

    # qualified[i] = True iff a bullish cross fired in [i-freshness+1, i]
    # AND slope_pct ≥ 0 over slope_window AND fast_now ≥ fast[i - smoothe].
    # min_slope_pct default is 0.0 so the slope check is just sign-based.
    for i in range(MA_SLOW_PERIOD + max(MA_SLOPE_WINDOW, MA_DIRECTION_SMOOTHE), n):
        if not (np.isfinite(fast[i]) and np.isfinite(slow[i])):
            continue
        if direction[i] != +1:
            continue
        # fresh cross in trailing freshness window
        lo = max(0, i - MA_SIGNAL_FRESHNESS + 1)
        if not cross[lo:i + 1].any():
            continue
        # slope on slow MA
        slow_lag = slow[i - MA_SLOPE_WINDOW]
        if not np.isfinite(slow_lag) or slow_lag == 0:
            continue
        # min_slope_pct=0 → just need slow rising (slope >= 0)
        if slow[i] - slow_lag < 0:
            continue
        # direction-smoothing on fast MA
        f_lag = fast[i - MA_DIRECTION_SMOOTHE]
        if not np.isfinite(f_lag) or fast[i] < f_lag:
            continue
        qualified[i] = True

    return qualified, direction


def _build_adaptive_supertrend_trace(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (qualified, direction) arrays.

    Computes the full SuperTrend trajectory in one pass — K-means runs
    once per bar in the loop (faithful to Pine), but the trajectory is
    built once per symbol rather than once per scan-day query.
    """
    n = len(df)
    qualified = np.zeros(n, dtype=bool)
    direction = np.zeros(n, dtype=int)

    atr_arr = wilder_atr(df, AST_ATR_PERIOD).to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    hl2 = (high + low) / 2.0

    super_trend = np.full(n, np.nan)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)

    for i in range(n):
        if not np.isfinite(atr_arr[i]) or atr_arr[i] <= 0:
            continue
        if i + 1 < AST_TRAINING_PERIOD:
            continue
        window = atr_arr[i + 1 - AST_TRAINING_PERIOD : i + 1]
        if not np.all(np.isfinite(window)):
            continue
        centroids = _kmeans_3_linear_seeds(window)
        cluster_idx = int(np.argmin(np.abs(centroids - atr_arr[i])))
        assigned_centroid = float(centroids[cluster_idx])

        basic_upper = hl2[i] + AST_FACTOR * assigned_centroid
        basic_lower = hl2[i] - AST_FACTOR * assigned_centroid

        if i == 0 or not np.isfinite(final_upper[i - 1]):
            final_upper[i] = basic_upper
            final_lower[i] = basic_lower
        else:
            final_lower[i] = (
                basic_lower
                if basic_lower > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]
                else final_lower[i - 1]
            )
            final_upper[i] = (
                basic_upper
                if basic_upper < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]
                else final_upper[i - 1]
            )

        if i == 0 or not np.isfinite(super_trend[i - 1]):
            direction[i] = -1
        elif super_trend[i - 1] == final_upper[i - 1]:
            direction[i] = +1 if close[i] > final_upper[i] else -1
        else:
            direction[i] = -1 if close[i] < final_lower[i] else +1
        super_trend[i] = final_lower[i] if direction[i] == +1 else final_upper[i]

    # qualified detection: confirm_signals=True means flip detected at
    # bar j is reported on bar j+1.
    for j in range(2, n):
        if AST_CONFIRM_SIGNALS:
            # qualified at bar j iff direction[j-1]==+1 AND direction[j-2]!=+1
            # AND direction[j]==+1 (sustained), within freshness window.
            if direction[j] != +1:
                continue
            lo = max(2, j - AST_SIGNAL_FRESHNESS + 1)
            for k in range(j, lo - 1, -1):
                if direction[k - 1] == +1 and direction[k - 2] != +1:
                    qualified[j] = True
                    break
        else:
            if direction[j] != +1:
                continue
            lo = max(1, j - AST_SIGNAL_FRESHNESS + 1)
            for k in range(j, lo - 1, -1):
                if direction[k] == +1 and direction[k - 1] != +1:
                    qualified[j] = True
                    break
    return qualified, direction


def _build_deviation_trend_trace(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (qualified, direction) arrays.

    Computes the full slope_norm trajectory in one pass.
    """
    n = len(df)
    qualified = np.zeros(n, dtype=bool)
    direction = np.zeros(n, dtype=int)

    avg_series = sma(df["close"], DT_SMA_LENGTH)
    slope_series = avg_series - avg_series.shift(DT_SLOPE_LAG)
    slope_max = slope_series.rolling(
        DT_PERCENTILE_WINDOW, min_periods=DT_PERCENTILE_WINDOW
    ).max()
    with np.errstate(divide="ignore", invalid="ignore"):
        slope_norm = (slope_series / slope_max).to_numpy(dtype=float)

    current = 0
    last_bullish = -1
    for i in range(1, n):
        n_now = slope_norm[i]
        n_prev = slope_norm[i - 1]
        if not np.isfinite(n_now) or not np.isfinite(n_prev):
            direction[i] = current
            continue
        if (
            n_prev <= DT_SLOPE_THRESHOLD
            and n_now > DT_SLOPE_THRESHOLD
            and current != +1
        ):
            current = +1
            last_bullish = i
        elif (
            n_prev >= -DT_SLOPE_THRESHOLD
            and n_now < -DT_SLOPE_THRESHOLD
            and current == +1
        ):
            current = -1
        direction[i] = current
        # qualified at bar i iff a fresh bullish flip is within trailing
        # freshness window AND we're currently +1.
        if (
            last_bullish >= 0
            and i - last_bullish < DT_SIGNAL_FRESHNESS
            and current == +1
        ):
            qualified[i] = True
    return qualified, direction


def build_tc_trace(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Build the full TC trace for one symbol's df. Returns a dict with
    per-bar arrays for ma_qualified, ma_direction, ast_qualified,
    ast_direction, dev_qualified, dev_direction, tc_score, tc_qualified.

    Scoring mode is controlled by module-level ``_SCORING_MODE``:
      - "strict"  (Sec.5.10): bull vote requires qualified=True AND direction=+1
      - "relaxed" (Ask 6):    bull vote requires only direction=+1
    """
    ma_q, ma_d = _build_ma_crossover_trace(df)
    ast_q, ast_d = _build_adaptive_supertrend_trace(df)
    dev_q, dev_d = _build_deviation_trend_trace(df)

    if _SCORING_MODE == "strict":
        bull = (
            (ma_q & (ma_d == +1)).astype(int)
            + (ast_q & (ast_d == +1)).astype(int)
            + (dev_q & (dev_d == +1)).astype(int)
        )
    elif _SCORING_MODE == "relaxed":
        bull = (
            (ma_d == +1).astype(int)
            + (ast_d == +1).astype(int)
            + (dev_d == +1).astype(int)
        )
        # Anti-spam: in relaxed mode every bar in a sustained uptrend
        # would qualify forever. Restrict tc_qualified to bars where
        # the score INCREASED from the previous bar — i.e., a fresh
        # 2→3 transition or 1→2 transition. This makes "qualified" a
        # one-shot per regime change, matching the spirit of fresh
        # confluence even though individual components don't gate on
        # freshness.
        prev_bull = np.concatenate([[0], bull[:-1]])
        tc_qualified = (bull >= 2) & (bull > prev_bull)
        return {
            "ma_qualified": ma_q,
            "ma_direction": ma_d,
            "ast_qualified": ast_q,
            "ast_direction": ast_d,
            "dev_qualified": dev_q,
            "dev_direction": dev_d,
            "tc_score": bull,
            "tc_qualified": tc_qualified,
        }
    else:
        raise ValueError(f"unknown scoring mode: {_SCORING_MODE}")
    tc_qualified = bull >= 2
    return {
        "ma_qualified": ma_q,
        "ma_direction": ma_d,
        "ast_qualified": ast_q,
        "ast_direction": ast_d,
        "dev_qualified": dev_q,
        "dev_direction": dev_d,
        "tc_score": bull,
        "tc_qualified": tc_qualified,
    }


# ─────────────────────────────────────────────────────────────────────
# Trade record + simulator
# ─────────────────────────────────────────────────────────────────────
@dataclass
class TCTrade:
    symbol: str
    entry_date: str  # ISO
    entry_price: float
    entry_bar: int
    exit_date: str
    exit_price: float
    exit_bar: int
    return_pct: float
    days_held: int
    days_to_t1: int | None
    outcome: str
    conviction: str  # 'medium' or 'high'
    sector: str
    market_cap_cr: float


def simulate_trade(
    df: pd.DataFrame,
    entry_bar: int,
    *,
    symbol: str,
    conviction: str,
    sector: str,
    market_cap_cr: float,
) -> TCTrade | None:
    """Walk forward from ``entry_bar``. Stop / target ladder / time stop.

    Stop: −3.85% from entry. Target ladder: T1 = +5%, T2 = +10%,
    T3 = +15%. Time stop: 25 bars. ``days_to_t1`` records first +5%
    touch (used by §11 hit-rate metric); the trade continues to T3
    or stop or time stop regardless.
    """
    if entry_bar + 1 >= len(df):
        return None
    entry_price = float(df["close"].iloc[entry_bar])
    if entry_price <= 0:
        return None
    stop = entry_price * (1.0 - _RISK["entry_stop"])
    t1 = entry_price * (1.0 + _RISK["t1"])
    t3 = entry_price * (1.0 + _RISK["t3"])

    days_to_t1: int | None = None
    end_bar = min(entry_bar + 1 + _RISK["time_stop_bars"], len(df))

    for i in range(entry_bar + 1, end_bar):
        h = float(df["high"].iloc[i])
        lo = float(df["low"].iloc[i])
        # Within-bar order: assume worst-case stop hit before target
        # (conservative; matches the G1 backtester's convention).
        if lo <= stop:
            return TCTrade(
                symbol=symbol,
                entry_date=str(df.index[entry_bar].date()),
                entry_price=entry_price,
                entry_bar=entry_bar,
                exit_date=str(df.index[i].date()),
                exit_price=stop,
                exit_bar=i,
                return_pct=(stop - entry_price) / entry_price,
                days_held=i - entry_bar,
                days_to_t1=days_to_t1,
                outcome="STOP_HIT",
                conviction=conviction,
                sector=sector,
                market_cap_cr=market_cap_cr,
            )
        if h >= t1 and days_to_t1 is None:
            days_to_t1 = i - entry_bar
        if h >= t3:
            return TCTrade(
                symbol=symbol,
                entry_date=str(df.index[entry_bar].date()),
                entry_price=entry_price,
                entry_bar=entry_bar,
                exit_date=str(df.index[i].date()),
                exit_price=t3,
                exit_bar=i,
                return_pct=_RISK["t3"],  # bugfix: was TARGET_T3_PCT global
                days_held=i - entry_bar,
                days_to_t1=(
                    days_to_t1 if days_to_t1 is not None else (i - entry_bar)
                ),
                outcome="WIN_T3",
                conviction=conviction,
                sector=sector,
                market_cap_cr=market_cap_cr,
            )

    # Time-stop exit on the last walked bar.
    last_i = end_bar - 1
    if last_i <= entry_bar:
        return None
    exit_price = float(df["close"].iloc[last_i])
    return_pct = (exit_price - entry_price) / entry_price
    if return_pct >= _RISK["t2"]:
        outcome = "WIN_T2"
    elif return_pct >= _RISK["t1"]:
        outcome = "WIN_T1"
    else:
        outcome = "TIME_EXIT"
    return TCTrade(
        symbol=symbol,
        entry_date=str(df.index[entry_bar].date()),
        entry_price=entry_price,
        entry_bar=entry_bar,
        exit_date=str(df.index[last_i].date()),
        exit_price=exit_price,
        exit_bar=last_i,
        return_pct=return_pct,
        days_held=last_i - entry_bar,
        days_to_t1=days_to_t1,
        outcome=outcome,
        conviction=conviction,
        sector=sector,
        market_cap_cr=market_cap_cr,
    )


# ─────────────────────────────────────────────────────────────────────
# Universe loading with date-fallback
# ─────────────────────────────────────────────────────────────────────
def _load_universe_with_fallback() -> pd.DataFrame:
    """Today's universe cache may be empty (daily cron writes the empty
    frame before market-cap fetcher runs). Fall back to yesterday's
    snapshot which carries the full 497-symbol InvestQuest universe."""
    universe = load_universe()
    if len(universe) == 0:
        print("  today's universe cache is empty; falling back to yesterday")
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))
    return universe


def _is_financial_sector(sec: str) -> bool:
    """v2.1 §0.5 mirror — match Financial Services / NBFC / Bank
    regardless of case or label form. Used by --exclude-financials."""
    s = (sec or "").lower()
    return ("financial" in s) or ("nbfc" in s) or ("bank" in s)


# ─────────────────────────────────────────────────────────────────────
# Backtest runner
# ─────────────────────────────────────────────────────────────────────
def run_backtest(
    *, limit: int | None, test_years: int, exclude_financials: bool = False
) -> tuple[list[TCTrade], pd.Timestamp, pd.Timestamp, int]:
    universe = _load_universe_with_fallback()
    if exclude_financials:
        before = len(universe)
        universe = universe[~universe["sector"].apply(_is_financial_sector)]
        print(f"  --exclude-financials: dropped {before - len(universe)} symbols")
    if limit is not None:
        universe = universe.head(limit)
    print(
        f"Universe: {len(universe)} symbols "
        f"(top-by-mcap; head: {list(universe.head(5).index)})"
    )

    end_dt = pd.Timestamp(date.today() - timedelta(days=1))
    start_dt = end_dt - pd.Timedelta(days=365 * test_years + 30)

    print(f"Test window: {start_dt.date()} → {end_dt.date()}")
    trades: list[TCTrade] = []
    n_processed = 0
    n_with_data = 0

    for sym, row in universe.iterrows():
        n_processed += 1
        try:
            df = load_eod(sym)
        except Exception:  # noqa: BLE001
            continue
        if df is None or df.empty:
            continue
        df.columns = [c.lower() for c in df.columns]
        # Slice to the test window with enough warm-up bars before
        # start_dt so deviation_trend's 506-bar minimum is met.
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if len(df) < 600:
            continue
        n_with_data += 1

        # The TC indicators (esp. deviation_trend) need 506+ trailing
        # bars; we walk only over scan days where on_bar covers that
        # warm-up.
        scan_start = max(506, df.index.searchsorted(start_dt))
        scan_end = min(len(df) - 1, df.index.searchsorted(end_dt))
        if scan_start >= scan_end:
            continue

        sector = str(row.get("sector", "Unknown"))
        mcap = float(row.get("market_cap_cr", 0.0))

        # Build the full TC trace once for this symbol; the per-bar
        # query reduces to array lookups inside the scan window.
        try:
            trace = build_tc_trace(df)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {sym}: trace build failed: {exc}", flush=True)
            continue

        # Prevent double-entry — once a position is opened, skip new
        # signals on this symbol until the trade closes.
        next_eligible_bar = scan_start
        for bar in range(scan_start, scan_end):
            if bar < next_eligible_bar:
                continue
            if not bool(trace["tc_qualified"][bar]):
                continue
            score = int(trace["tc_score"][bar])
            conviction = "high" if score == 3 else "medium"
            trade = simulate_trade(
                df,
                bar,
                symbol=sym,
                conviction=conviction,
                sector=sector,
                market_cap_cr=mcap,
            )
            if trade is None:
                continue
            trades.append(trade)
            next_eligible_bar = trade.exit_bar + 1

        if n_processed % 25 == 0:
            print(
                f"  processed {n_processed}/{len(universe)} · "
                f"with data {n_with_data} · trades so far {len(trades)}",
                flush=True,
            )
        # Heartbeat every 5 symbols so we can detect a hang early.
        elif n_processed % 5 == 0:
            print(f"    .. {n_processed}", flush=True)

    return trades, start_dt, end_dt, len(universe)


# ─────────────────────────────────────────────────────────────────────
# §11 metrics
# ─────────────────────────────────────────────────────────────────────
def compute_metrics(trades: list[TCTrade]) -> dict:
    """§11 hit-rate uses 'reached +5%' (days_to_t1 not None).
    Wins/losses by return_pct sign for win/loss ratio, profit factor,
    and Sharpe."""
    if not trades:
        return {
            "n_trades": 0, "hit_rate_pct": 0.0, "avg_days_to_t1": 0.0,
            "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
            "win_loss_ratio": 0.0, "profit_factor": 0.0, "sharpe_annualized": 0.0,
            "max_consecutive_losses": 0, "n_wins": 0, "n_losses": 0,
        }
    n = len(trades)
    n_reached_t1 = sum(1 for t in trades if t.days_to_t1 is not None)
    hit_rate_pct = 100.0 * n_reached_t1 / n
    days_to_t1_vals = [t.days_to_t1 for t in trades if t.days_to_t1 is not None]
    avg_days_to_t1 = float(np.mean(days_to_t1_vals)) if days_to_t1_vals else 0.0

    rets = np.array([t.return_pct for t in trades], dtype=float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    n_wins = int(wins.size)
    n_losses = int(losses.size)
    avg_win_pct = float(wins.mean() * 100.0) if n_wins else 0.0
    avg_loss_pct = float(losses.mean() * 100.0) if n_losses else 0.0
    sum_wins = float(wins.sum())
    sum_loss = float(losses.sum())
    win_loss_ratio = (
        abs(avg_win_pct / avg_loss_pct) if avg_loss_pct else float("inf")
    )
    profit_factor = (sum_wins / abs(sum_loss)) if sum_loss < 0 else float("inf")
    sharpe = (
        float(np.sqrt(252) * rets.mean() / rets.std(ddof=0))
        if rets.std(ddof=0) > 0
        else 0.0
    )

    # Max consecutive losses (chronological).
    chrono = sorted(trades, key=lambda t: t.entry_date)
    cur = mx = 0
    for t in chrono:
        if t.return_pct <= 0:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0

    return {
        "n_trades": n,
        "hit_rate_pct": round(hit_rate_pct, 1),
        "avg_days_to_t1": round(avg_days_to_t1, 1),
        "avg_win_pct": round(avg_win_pct, 2),
        "avg_loss_pct": round(avg_loss_pct, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_annualized": round(sharpe, 2),
        "max_consecutive_losses": mx,
        "n_wins": n_wins,
        "n_losses": n_losses,
    }


def bootstrap_envelope(trades: list[TCTrade], *, seed: int, resamples: int = 1000) -> dict:
    """1σ / 2σ bootstrap envelope on the trade pool."""
    if len(trades) < 2:
        return {}
    rng = np.random.default_rng(seed)
    n = len(trades)
    rets = np.array([t.return_pct for t in trades], dtype=float)
    days_to_t1 = np.array([
        t.days_to_t1 if t.days_to_t1 is not None else -1 for t in trades
    ])

    hit_rates = []
    avg_wins = []
    avg_losses = []
    pfs = []
    sharpes = []
    wl_ratios = []
    for _ in range(resamples):
        idx = rng.integers(0, n, size=n)
        r = rets[idx]
        d = days_to_t1[idx]
        hr = 100.0 * (d >= 0).sum() / n
        wins = r[r > 0]
        losses = r[r <= 0]
        avg_w = wins.mean() * 100.0 if wins.size else 0.0
        avg_l = losses.mean() * 100.0 if losses.size else 0.0
        sum_w = wins.sum()
        sum_l = losses.sum()
        pf = (sum_w / abs(sum_l)) if sum_l < 0 else 0.0
        sh = float(np.sqrt(252) * r.mean() / r.std(ddof=0)) if r.std(ddof=0) > 0 else 0.0
        wl = abs(avg_w / avg_l) if avg_l else 0.0
        hit_rates.append(hr)
        avg_wins.append(avg_w)
        avg_losses.append(avg_l)
        pfs.append(pf)
        sharpes.append(sh)
        wl_ratios.append(wl)

    def _band(vals: list[float]) -> dict:
        a = np.array(vals)
        m = float(a.mean())
        s = float(a.std(ddof=0))
        return {
            "mean": round(m, 2),
            "sigma_1": round(s, 2),
            "sigma_2": round(2 * s, 2),
            "band_1sigma": [round(m - s, 2), round(m + s, 2)],
            "band_2sigma": [round(m - 2 * s, 2), round(m + 2 * s, 2)],
        }

    return {
        "seed": seed,
        "resamples": resamples,
        "n_trades": n,
        "hit_rate": _band(hit_rates),
        "avg_win": _band(avg_wins),
        "avg_loss": _band(avg_losses),
        "profit_factor": _band(pfs),
        "sharpe": _band(sharpes),
        "win_loss_ratio": _band(wl_ratios),
    }


# ─────────────────────────────────────────────────────────────────────
# Report rendering (matches G1 schema)
# ─────────────────────────────────────────────────────────────────────
def _verdict(observed: float, target: float, op: str) -> str:
    if op == "ge":
        return "PASS" if observed >= target else "FAIL"
    if op == "le":
        return "PASS" if observed <= target else "FAIL"
    return "?"


def render_report(
    *,
    trades: list[TCTrade],
    metrics: dict,
    metrics_medium: dict,
    metrics_high: dict,
    envelope: dict,
    universe_size: int,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> str:
    n = metrics["n_trades"]
    n_med = metrics_medium["n_trades"]
    n_high = metrics_high["n_trades"]

    # Outcome distribution.
    outcome_counts: dict[str, int] = {}
    for t in trades:
        outcome_counts[t.outcome] = outcome_counts.get(t.outcome, 0) + 1
    outcome_rows = "\n".join(
        f"| `{k}` | {v} |"
        for k, v in sorted(outcome_counts.items(), key=lambda kv: -kv[1])
    )

    # Sector breakdown.
    sectors: dict[str, list[TCTrade]] = {}
    for t in trades:
        sectors.setdefault(t.sector, []).append(t)
    sector_rows = []
    for sec in sorted(sectors.keys(), key=lambda s: -len(sectors[s])):
        sub = sectors[sec]
        wins = sum(1 for t in sub if t.return_pct > 0)
        losses = len(sub) - wins
        avg_ret = float(np.mean([t.return_pct for t in sub])) * 100.0
        hit = 100.0 * wins / len(sub)
        sector_rows.append(
            f"| `{sec}` | {len(sub)} | {wins} | {losses} | "
            f"{avg_ret:+.2f}% | {hit:.1f}% |"
        )

    # Marketcap-tier breakdown.
    tiers = {
        "MEGA (≥ ₹1 lakh Cr)": [],
        "LARGE (₹50k–1 lakh Cr)": [],
        "MID (₹15k–50k Cr)": [],
        "SMALL-MID (₹5k–15k Cr)": [],
    }
    for t in trades:
        m = t.market_cap_cr
        if m >= 100000.0:
            tiers["MEGA (≥ ₹1 lakh Cr)"].append(t)
        elif m >= 50000.0:
            tiers["LARGE (₹50k–1 lakh Cr)"].append(t)
        elif m >= 15000.0:
            tiers["MID (₹15k–50k Cr)"].append(t)
        else:
            tiers["SMALL-MID (₹5k–15k Cr)"].append(t)
    tier_rows = []
    for tier_name, sub in tiers.items():
        if not sub:
            tier_rows.append(f"| `{tier_name}` | 0 | 0 | 0 | n/a | n/a |")
            continue
        wins = sum(1 for t in sub if t.return_pct > 0)
        losses = len(sub) - wins
        avg_ret = float(np.mean([t.return_pct for t in sub])) * 100.0
        hit = 100.0 * wins / len(sub)
        tier_rows.append(
            f"| `{tier_name}` | {len(sub)} | {wins} | {losses} | "
            f"{avg_ret:+.2f}% | {hit:.1f}% |"
        )

    # Diagnostic extras.
    rets = [t.return_pct for t in trades] if trades else [0.0]
    median = float(np.median(rets)) * 100.0
    best = max(rets) * 100.0
    worst = min(rets) * 100.0
    expectancy = float(np.mean(rets)) * 100.0

    # Verdicts.
    verdicts = [
        ("Hit rate (% reaching +5%)", "≥ 45%",
         f"{metrics['hit_rate_pct']}%", _verdict(metrics["hit_rate_pct"], 45.0, "ge")),
        ("Avg days to T1", "≤ 25",
         f"{metrics['avg_days_to_t1']}", _verdict(metrics["avg_days_to_t1"], 25.0, "le")),
        ("Avg win", "≥ +6%",
         f"{metrics['avg_win_pct']:+.2f}%", _verdict(metrics["avg_win_pct"], 6.0, "ge")),
        ("Avg loss", "≤ −3%",
         f"{metrics['avg_loss_pct']:+.2f}%", _verdict(metrics["avg_loss_pct"], -3.0, "le")),
        ("Max consecutive losses", "≤ 8",
         f"{metrics['max_consecutive_losses']}",
         _verdict(metrics["max_consecutive_losses"], 8, "le")),
        ("Win/loss ratio", "≥ 2.0",
         f"{metrics['win_loss_ratio']}",
         _verdict(metrics["win_loss_ratio"], 2.0, "ge")),
        ("Profit Factor", "≥ 1.8",
         f"{metrics['profit_factor']}",
         _verdict(metrics["profit_factor"], 1.8, "ge")),
        ("Sharpe (annualized)", "≥ 1.5",
         f"{metrics['sharpe_annualized']}",
         _verdict(metrics["sharpe_annualized"], 1.5, "ge")),
    ]
    overall = "PASS" if all(v[3] == "PASS" for v in verdicts) else "FAIL"
    metric_rows = "\n".join(f"| {m} | {t} | {o} | {v} |" for m, t, o, v in verdicts)

    # Bootstrap section.
    if envelope:
        env_rows = []
        for label, key in [
            ("Hit rate (%)", "hit_rate"),
            ("Avg win (%)", "avg_win"),
            ("Avg loss (%)", "avg_loss"),
            ("Profit Factor", "profit_factor"),
            ("Sharpe (annualized)", "sharpe"),
            ("Win/loss ratio", "win_loss_ratio"),
        ]:
            b = envelope[key]
            env_rows.append(
                f"| {label} | {b['mean']:+.2f} | {b['sigma_1']:.2f} | "
                f"{b['sigma_2']:.2f} | "
                f"[{b['band_1sigma'][0]:+.2f}, {b['band_1sigma'][1]:+.2f}] | "
                f"[{b['band_2sigma'][0]:+.2f}, {b['band_2sigma'][1]:+.2f}] |"
            )
        env_section = "\n".join(env_rows)
    else:
        env_section = "_(insufficient trade count for bootstrap)_"

    return f"""# Saadhana Backtest — Sprint 2.3 (Triple confluence cohort)

**Phase:** S2.3 — Triple confluence go/no-go decision
**Generated:** {date.today().isoformat()}
**Replay window:** {start_dt.date()} → {end_dt.date()}
**Universe:** {universe_size} symbols (InvestQuest, MCap ≥ ₹5,000 Cr · ADV ≥ ₹5 Cr)
**Cohort:** `triple_confluence` (Sec.5.10)
**Sector exclusions:** `[]` (v1 default per Sec.5.10; revisit if financial drag re-emerges)
**Per-trade risk:** §10 STANDARD (medium conviction) / HIGH (3-of-3 conviction)

---

## §11 Backtest Validation

**OVERALL: {overall}**

| Metric | Target | Observed | Verdict |
|---|---|---|---|
{metric_rows}

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
{outcome_rows}

**Total trades:** {n}
**Closed:** {n} ({metrics['n_wins']} wins, {metrics['n_losses']} losses)

## Conviction-tier split

| Conviction | N | Hit rate (% reaching +5%) | Avg win | Avg loss | Profit Factor | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| 2-of-3 medium (STANDARD sizing) | {n_med} | {metrics_medium['hit_rate_pct']:.1f}% | {metrics_medium['avg_win_pct']:+.2f}% | {metrics_medium['avg_loss_pct']:+.2f}% | {metrics_medium['profit_factor']:.2f} | {metrics_medium['sharpe_annualized']:.2f} |
| 3-of-3 high (HIGH sizing) | {n_high} | {metrics_high['hit_rate_pct']:.1f}% | {metrics_high['avg_win_pct']:+.2f}% | {metrics_high['avg_loss_pct']:+.2f}% | {metrics_high['profit_factor']:.2f} | {metrics_high['sharpe_annualized']:.2f} |

The tier split tests whether 3-of-3 conviction justifies the §10 HIGH sizing differential (2.0% vs 0.5% per trade). If the high-tier hit rate is materially higher than medium, sizing escalation is earned; if not, the spec keeps both at STANDARD for v1.

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
{chr(10).join(sector_rows)}

## Marketcap-tier Breakdown

| Tier | Trades | Wins (positive return) | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
{chr(10).join(tier_rows)}

## Diagnostic Extras

- Median trade return: {median:+.2f}%
- Best trade: {best:+.2f}%
- Worst trade: {worst:+.2f}%
- Expectancy per trade: {expectancy:+.2f}%

## Drift Envelope (bootstrap, 1000 resamples · seed 20260503)

| Metric | Mean | 1σ | 2σ | 1σ band | 2σ band |
|---|---:|---:|---:|---|---|
{env_section}

---

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing differential (medium = STANDARD 0.5% / high = HIGH 2.0% per §10)
  is captured in the conviction-tier split table above; the blended §11 metrics
  combine both tiers without size-weighting (each trade counted once for hit-rate
  purposes).
- §13 catalyst weighting is **off** in S2.3 — that layer is validated in Phase G2
  / S2.4 forensics.
- Sec.5.10 v1 ships `sector_exclusions = []` (sector-agnostic). If the sector
  breakdown shows the v2.1 §0.5 financial-cohort drag re-emerging on the TC
  pattern, a Sec.19 candidate rule proposes the exclusion with this report's
  evidence — same discipline as the original §0.5 amendment.
- Indicator code is faithful to Pine source post-Cycles 1/2/3 (commits 20ec0f0,
  b28d402, f02abd4). Cross-validation against the parallel verifier
  (`scripts/parallel_backtest/parallel_backtest_trades.csv`) is in the
  comparison post that follows this report.
"""


def main(argv: list[str] | None = None) -> int:
    global _SCORING_MODE, _RISK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit universe to top-N by mcap (debug)")
    parser.add_argument("--year-window", type=int, default=3)
    parser.add_argument("--relaxed-scoring", action="store_true",
                        help="Ask 6: vote bullish on direction==+1 only")
    parser.add_argument("--wide-stop", action="store_true",
                        help="Ask 7: 6%/9% stop/target, 60-bar time stop")
    parser.add_argument("--exclude-financials", action="store_true",
                        help="v2.1 §0.5 mirror — drop Financial/NBFC/Bank")
    parser.add_argument("--report-suffix", type=str, default="",
                        help="Append _suffix to output filename")
    args = parser.parse_args(argv)

    if args.relaxed_scoring:
        _SCORING_MODE = "relaxed"
        print("Scoring mode: RELAXED (direction-only; tc_qualified on score-up transition)")
    if args.wide_stop:
        _RISK = {
            "entry_stop": WIDE_ENTRY_STOP_PCT,
            "t1": WIDE_TARGET_T1_PCT,
            "t2": WIDE_TARGET_T2_PCT,
            "t3": WIDE_TARGET_T3_PCT,
            "time_stop_bars": WIDE_TIME_STOP_BARS,
        }
        print(
            f"Risk model: WIDE-STOP (stop {WIDE_ENTRY_STOP_PCT * 100:.1f}%, "
            f"T3 {WIDE_TARGET_T3_PCT * 100:.0f}%, "
            f"time-stop {WIDE_TIME_STOP_BARS} bars)"
        )

    print("S2.3 — Triple confluence backtest")
    trades, start_dt, end_dt, universe_size = run_backtest(
        limit=args.limit,
        test_years=args.year_window,
        exclude_financials=args.exclude_financials,
    )
    print(f"\nTotal trades: {len(trades)}")

    metrics = compute_metrics(trades)
    metrics_medium = compute_metrics([t for t in trades if t.conviction == "medium"])
    metrics_high = compute_metrics([t for t in trades if t.conviction == "high"])
    envelope = bootstrap_envelope(trades, seed=20260503, resamples=1000)

    report = render_report(
        trades=trades,
        metrics=metrics,
        metrics_medium=metrics_medium,
        metrics_high=metrics_high,
        envelope=envelope,
        universe_size=universe_size,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    out_dir = REPO_ROOT / "spec" / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.report_suffix}" if args.report_suffix else ""
    report_path = out_dir / f"backtest_report_s23_triple_confluence{suffix}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to {report_path}")

    # Trade dump for the per-symbol overlap analysis vs parallel verifier.
    trades_path = out_dir / f"backtest_s23_trades{suffix}.json"
    trades_path.write_text(
        json.dumps([asdict(t) for t in trades], indent=2),
        encoding="utf-8",
    )
    print(f"Trade JSON written to {trades_path}")

    # Print a banner on stderr.
    overall = "PASS" if (
        metrics["hit_rate_pct"] >= 45 and metrics["avg_win_pct"] >= 6
        and metrics["avg_loss_pct"] >= -3 and metrics["max_consecutive_losses"] <= 8
        and metrics["win_loss_ratio"] >= 2.0 and metrics["profit_factor"] >= 1.8
        and metrics["sharpe_annualized"] >= 1.5
    ) else "FAIL"
    print(json.dumps({
        "phase": "S2.3",
        "verdict": overall,
        "trades": len(trades),
        "trades_medium": metrics_medium["n_trades"],
        "trades_high": metrics_high["n_trades"],
        "hit_rate_pct": metrics["hit_rate_pct"],
        "profit_factor": metrics["profit_factor"],
        "sharpe": metrics["sharpe_annualized"],
    }, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
