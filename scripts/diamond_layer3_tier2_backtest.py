"""Phase 1 Step 1.4 — Tier 2 v0 backtest validation.

Apply the Sec.6.4 v0 Tier 2 score (5 checks from current fundamentals
data) as a Diamond Layer 3 post-hoc filter on three trade lists:

  1. TC + Sector Pulse (Diamond Layer 6 trades from Track 3)
  2. TC alone (combined-config baseline)
  3. Pro-setup 13/13 (G1 InvestQuest baseline)

For each, compare:
  - Layer 0: cohort baseline
  - Layer 0 + Tier 2 ≥ 4 / 5 (the spec'd threshold)
  - Layer 0 + Tier 2 = 5 / 5 (strictest)

The Phase 1 checkpoint criteria (per the operator's brief):
  ≥ 4pp lift  → PROCEED to Phase 2
  1–3pp lift  → STOP, post results, operator decides
  < 1pp lift  → STOP, hypothesis broken
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "filter"))

from saadhana_filter.data.loader import load_eod  # noqa: E402
from saadhana_filter.data.universe import load_universe  # noqa: E402
from saadhana_filter.quality.tier2 import compute_tier2_score  # noqa: E402

# Inputs
TC_TRADES_PATH = REPO_ROOT / "spec" / "samples" / "backtest_s23_trades_combined.json"
PRO_SETUP_TRADES_PATH = (
    REPO_ROOT / "spec" / "samples" / "backtest_g1_investquest_universe_trades.json"
)
FUND_PATH = REPO_ROOT / "data" / "fundamentals_investquest_universe.parquet"

INITIAL_CAPITAL = 100_000
POS_SIZE_FRAC = 0.20
MAX_CONCURRENT = 5
SLIPPAGE_PCT = 0.004
BROKER_PER_TRADE = 40.0
STCG_RATE = 0.15
SECTOR_BREADTH_THRESHOLD = 70.0


# ─────────────────────────────────────────────────────────────────────
# Tier 2 v0 score per symbol
# ─────────────────────────────────────────────────────────────────────
def _build_tier2_lookup() -> dict[str, int]:
    fund = pd.read_parquet(FUND_PATH)
    if "symbol" in fund.columns:
        fund = fund.set_index("symbol")
    out: dict[str, int] = {}
    for sym, row in fund.iterrows():
        out[str(sym)] = compute_tier2_score(row, version="v0")
    return out


# ─────────────────────────────────────────────────────────────────────
# Sector breadth lookup (for the TC + Sector Pulse layer)
# ─────────────────────────────────────────────────────────────────────
def _build_breadth_lookup(
    trade_dates: set[pd.Timestamp], universe: pd.DataFrame
) -> dict[tuple[pd.Timestamp, str], float]:
    sectors_by_sym: dict[str, str] = {}
    above_by_sym: dict[str, pd.Series] = {}
    for sym, row in universe.iterrows():
        try:
            df = load_eod(sym)
        except Exception:
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if "close" not in df.columns or len(df) < 50:
            continue
        sma50 = df["close"].rolling(50, min_periods=50).mean()
        above = (df["close"] >= sma50)
        sectors_by_sym[sym] = str(row.get("sector", "Unknown"))
        above_by_sym[sym] = above

    by_sector: dict[str, list[str]] = {}
    for sym, sec in sectors_by_sym.items():
        by_sector.setdefault(sec, []).append(sym)

    lookup: dict[tuple[pd.Timestamp, str], float] = {}
    for d in sorted(trade_dates):
        for sec, syms in by_sector.items():
            n_total = 0
            n_above = 0
            for s in syms:
                a = above_by_sym.get(s)
                if a is None:
                    continue
                idx = a.index.searchsorted(d)
                if idx >= len(a) or a.index[idx] != d:
                    continue
                v = a.iloc[idx]
                if pd.isna(v):
                    continue
                n_total += 1
                if bool(v):
                    n_above += 1
            if n_total >= 5:
                lookup[(d, sec)] = 100.0 * n_above / n_total
    return lookup


# ─────────────────────────────────────────────────────────────────────
# Metrics + cash sim
# ─────────────────────────────────────────────────────────────────────
def _metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "hit_rate_pct": 0.0, "win_rate_pct": 0.0, "pf": None,
                "sharpe": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0}
    rets = np.array([t["return_pct"] for t in trades], dtype=float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    n_t1 = sum(
        1 for t in trades if (t.get("days_to_t1") is not None and t["days_to_t1"] > 0)
    )
    pf = (wins.sum() / abs(losses.sum())) if losses.sum() < 0 else float("nan")
    sh = float(np.sqrt(252) * rets.mean() / rets.std(ddof=0)) if rets.std(ddof=0) > 0 else 0.0
    return {
        "n": len(trades),
        "hit_rate_pct": round(100.0 * n_t1 / len(trades), 1),
        "win_rate_pct": round(100.0 * (rets > 0).sum() / len(rets), 1),
        "avg_win_pct": round(wins.mean() * 100.0, 2) if wins.size else 0.0,
        "avg_loss_pct": round(losses.mean() * 100.0, 2) if losses.size else 0.0,
        "pf": round(pf, 2) if not np.isnan(pf) else None,
        "sharpe": round(sh, 2),
    }


def _cash_3yr(trades: list[dict]) -> dict:
    if not trades:
        return {"final": INITIAL_CAPITAL, "ret_pct": 0.0, "ann_pct": 0.0,
                "n_taken": 0, "net_pnl": 0}
    chrono = sorted(trades, key=lambda t: t["entry_date"])
    capital = INITIAL_CAPITAL
    open_slots: list[tuple[pd.Timestamp, float]] = []
    n_taken = 0
    for t in chrono:
        entry_dt = pd.Timestamp(t["entry_date"])
        open_slots = [s for s in open_slots if s[0] > entry_dt]
        if len(open_slots) >= MAX_CONCURRENT:
            continue
        position = capital * POS_SIZE_FRAC
        gross = position * t["return_pct"]
        slip = position * SLIPPAGE_PCT
        net = gross - slip - BROKER_PER_TRADE
        capital += net
        n_taken += 1
        exit_dt = entry_dt + pd.Timedelta(days=int(t["days_held"]) + 5)
        open_slots.append((exit_dt, position))
    if capital > INITIAL_CAPITAL:
        post_tax = INITIAL_CAPITAL + (capital - INITIAL_CAPITAL) * (1.0 - STCG_RATE)
    else:
        post_tax = capital
    ret_pct = (post_tax - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0
    ann_pct = (((post_tax / INITIAL_CAPITAL) ** (1.0 / 3.0)) - 1.0) * 100.0
    return {
        "final": round(post_tax, 0),
        "net_pnl": round(post_tax - INITIAL_CAPITAL, 0),
        "ret_pct": round(ret_pct, 2),
        "ann_pct": round(ann_pct, 2),
        "n_taken": n_taken,
    }


def _print_layer(label: str, trades: list[dict]) -> dict:
    m = _metrics(trades)
    c = _cash_3yr(trades)
    print(
        f"| {label:<35} | {m['n']:>5} | {m['hit_rate_pct']:>5.1f}% | "
        f"{m['win_rate_pct']:>5.1f}% | {m['pf']!s:>5} | {m['sharpe']:>+6.2f} | "
        f"₹{c['final']:>9,.0f} | ₹{c['net_pnl']:>+9,.0f} | "
        f"{c['ret_pct']:>+7.2f}% | {c['ann_pct']:>+7.2f}% |"
    )
    return {"label": label, **m, **c}


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main() -> int:
    print("Building Tier 2 v0 lookup from fundamentals snapshot...")
    tier2_score = _build_tier2_lookup()
    print(f"  Universe size: {len(tier2_score)}")
    score_dist = pd.Series(tier2_score).value_counts().sort_index()
    print("  Tier 2 v0 score distribution:")
    for s, n in score_dist.items():
        print(f"    score={s}: {n} symbols ({100.0 * n / len(tier2_score):.1f}%)")

    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))

    # ─── TC + Sector Pulse trade list (Diamond Layer 6 baseline) ───
    print("\nLoading TC combined trades + computing sector breadth...")
    tc_trades = json.loads(TC_TRADES_PATH.read_text(encoding="utf-8"))
    breadth = _build_breadth_lookup(
        {pd.Timestamp(t["entry_date"]) for t in tc_trades}, universe
    )
    tc_breadth_filtered = [
        t for t in tc_trades
        if breadth.get(
            (pd.Timestamp(t["entry_date"]), t.get("sector", "Unknown"))
        ) is not None
        and breadth[(pd.Timestamp(t["entry_date"]), t.get("sector", "Unknown"))]
        > SECTOR_BREADTH_THRESHOLD
    ]
    print(f"  TC + Sector Pulse: {len(tc_breadth_filtered)} of {len(tc_trades)}")

    # ─── Pro-setup trade list ───
    pro_trades = json.loads(PRO_SETUP_TRADES_PATH.read_text(encoding="utf-8"))
    print(f"  Pro-setup 13/13 G1: {len(pro_trades)}")

    # ─── Print one big ladder per cohort ───
    header = (
        f"| {'Layer':<35} | {'N':>5} | {'Hit%':>5} | {'Win%':>5} | "
        f"{'PF':>5} | {'Sharpe':>6} | {'Final ₹':>10} | {'Net P&L':>10} | "
        f"{'Return%':>8} | {'Annual%':>8} |"
    )
    sep = (
        f"|{'-' * 37}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 8}|"
        f"{'-' * 12}|{'-' * 12}|{'-' * 10}|{'-' * 10}|"
    )

    cohorts = [
        ("TC + Sector Pulse (Diamond L6)", tc_breadth_filtered),
        ("TC combined (no breadth)", tc_trades),
        ("Pro-setup 13/13 (G1)", pro_trades),
    ]

    summary_rows = []
    for cohort_name, trades in cohorts:
        print()
        print("=" * 130)
        print(f"COHORT: {cohort_name}")
        print("=" * 130)
        print(header)
        print(sep)

        baseline = _print_layer("0 baseline (cohort as-is)", trades)
        rows = {"baseline": baseline}

        for threshold, label in [
            (4, "+ Tier 2 v0 ≥ 4 / 5 (Layer 3)"),
            (5, "+ Tier 2 v0 = 5 / 5 (strictest)"),
        ]:
            sub = [t for t in trades if tier2_score.get(t["symbol"], 0) >= threshold]
            r = _print_layer(label, sub)
            rows[f"thresh_{threshold}"] = r

        # Phase 1 checkpoint logic — lift on hit rate.
        lift_4 = rows["thresh_4"]["hit_rate_pct"] - baseline["hit_rate_pct"]
        lift_5 = rows["thresh_5"]["hit_rate_pct"] - baseline["hit_rate_pct"]
        n_kept_4 = (
            100.0 * rows["thresh_4"]["n"] / baseline["n"] if baseline["n"] else 0.0
        )
        n_kept_5 = (
            100.0 * rows["thresh_5"]["n"] / baseline["n"] if baseline["n"] else 0.0
        )

        print()
        print(
            f"  Hit-rate lift (Layer 0 → Layer 0 + Tier 2 ≥ 4 / 5): "
            f"{baseline['hit_rate_pct']:+.1f}pp → "
            f"{rows['thresh_4']['hit_rate_pct']:+.1f}pp "
            f"(Δ {lift_4:+.1f}pp; N kept {rows['thresh_4']['n']} of "
            f"{baseline['n']} = {n_kept_4:.0f}%)"
        )
        print(
            f"  Hit-rate lift (Layer 0 → Layer 0 + Tier 2 = 5 / 5): "
            f"{baseline['hit_rate_pct']:+.1f}pp → "
            f"{rows['thresh_5']['hit_rate_pct']:+.1f}pp "
            f"(Δ {lift_5:+.1f}pp; N kept {rows['thresh_5']['n']} of "
            f"{baseline['n']} = {n_kept_5:.0f}%)"
        )
        if lift_4 >= 4.0:
            verdict = "PROCEED to Phase 2 (Tier 2 ≥ 4pp lift)"
        elif lift_4 >= 1.0:
            verdict = (
                "STOP, post results — operator decides (1–3pp lift)"
            )
        else:
            verdict = "Hypothesis broken (< 1pp lift)"
        print(f"  → Phase 1 checkpoint: {verdict}")
        summary_rows.append({"cohort": cohort_name, "lift_4": lift_4, "lift_5": lift_5})

    # ─── Final summary ───
    print()
    print("=" * 130)
    print("PHASE 1 CHECKPOINT — Tier 2 v0 lift across cohorts")
    print("=" * 130)
    for s in summary_rows:
        print(
            f"  {s['cohort']:<40} hit-rate lift @ ≥4/5: {s['lift_4']:+.1f}pp, "
            f"@ =5/5: {s['lift_5']:+.1f}pp"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
