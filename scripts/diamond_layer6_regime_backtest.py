"""Path δ — Class 6 regime filter validation backtest.

Apply the regime filter (Sec.0.7.5 Class 6) as a post-hoc filter on:
  1. TC + Sector Pulse (Diamond Layer 1+6 baseline) — the headline test
  2. TC combined alone — control
  3. Pro-setup 13/13 — generalisation test

For each, compare three configurations:
  Layer 0: cohort baseline (no regime gate)
  Layer 6+: + regime ∈ {Risk_On, Caution}    (default allowed set)
  Layer 6++: + regime == Risk_On only        (strictest variant)

Phase δ checkpoint criteria (per the operator's brief):
  ≥ 4pp lift  → DIAMOND STACK VALIDATED on InvestQuest. Proceed to β.
  1–3pp lift  → mild compound. Proceed to β with measured expectations.
  0pp lift    → Diamond stacking fundamentally broken on InvestQuest.
                STOP, propose Path ε (universe pivot).
  HURTS       → regime classifier misaligned; investigate.
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
from saadhana_filter.quality.regime_filter import (  # noqa: E402
    get_regime,
    regime_qualified,
    reset_regime_cache,
)

TC_TRADES_PATH = REPO_ROOT / "spec" / "samples" / "backtest_s23_trades_combined.json"
PRO_SETUP_TRADES_PATH = (
    REPO_ROOT / "spec" / "samples" / "backtest_g1_investquest_universe_trades.json"
)

INITIAL_CAPITAL = 100_000
POS_SIZE_FRAC = 0.20
MAX_CONCURRENT = 5
SLIPPAGE_PCT = 0.004
BROKER_PER_TRADE = 40.0
STCG_RATE = 0.15
SECTOR_BREADTH_THRESHOLD = 70.0


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
    sh = (
        float(np.sqrt(252) * rets.mean() / rets.std(ddof=0))
        if rets.std(ddof=0) > 0 else 0.0
    )
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
        f"| {label:<40} | {m['n']:>5} | {m['hit_rate_pct']:>5.1f}% | "
        f"{m['win_rate_pct']:>5.1f}% | {m['pf']!s:>5} | {m['sharpe']:>+6.2f} | "
        f"₹{c['final']:>9,.0f} | ₹{c['net_pnl']:>+9,.0f} | "
        f"{c['ret_pct']:>+7.2f}% | {c['ann_pct']:>+7.2f}% |"
    )
    return {"label": label, **m, **c}


def main() -> int:
    print("Path δ — Class 6 regime filter validation")
    reset_regime_cache()  # ensure fresh build for the run
    print(f"  Today's regime: {get_regime(pd.Timestamp.now())}")

    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))

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

    pro_trades = json.loads(PRO_SETUP_TRADES_PATH.read_text(encoding="utf-8"))
    print(f"  Pro-setup 13/13 G1: {len(pro_trades)}")

    # Pre-tag every trade with its entry-date regime for audit + reporting.
    for t in tc_trades + tc_breadth_filtered + pro_trades:
        t["_regime"] = get_regime(pd.Timestamp(t["entry_date"]))

    header = (
        f"| {'Layer':<40} | {'N':>5} | {'Hit%':>5} | {'Win%':>5} | "
        f"{'PF':>5} | {'Sharpe':>6} | {'Final ₹':>10} | {'Net P&L':>10} | "
        f"{'Return%':>8} | {'Annual%':>8} |"
    )
    sep = (
        f"|{'-' * 42}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 8}|"
        f"{'-' * 12}|{'-' * 12}|{'-' * 10}|{'-' * 10}|"
    )

    cohorts = [
        ("TC + Sector Pulse (Layer 1+6 baseline)", tc_breadth_filtered),
        ("TC combined (control, no breadth)", tc_trades),
        ("Pro-setup 13/13 (G1 generalisation)", pro_trades),
    ]

    summary_rows = []
    for cohort_name, trades in cohorts:
        print()
        print("=" * 130)
        print(f"COHORT: {cohort_name}")
        print("=" * 130)

        # Regime distribution of entries.
        regime_dist = pd.Series([t.get("_regime") for t in trades]).value_counts(
            dropna=False
        )
        print(
            "  Entry-date regime distribution: "
            + ", ".join(f"{k}={v}" for k, v in regime_dist.items())
        )

        print(header)
        print(sep)

        baseline = _print_layer("0 baseline (cohort as-is)", trades)

        # Layer 6+ — Risk_On + Caution
        l6_default = [
            t for t in trades
            if regime_qualified(
                pd.Timestamp(t["entry_date"]),
                allowed_regimes=("Risk_On", "Caution"),
            )
        ]
        l6_row = _print_layer(
            "+ regime ∈ {Risk_On, Caution} (default)", l6_default
        )

        # Layer 6++ — Risk_On only (strict)
        l6_strict = [
            t for t in trades
            if regime_qualified(
                pd.Timestamp(t["entry_date"]), allowed_regimes=("Risk_On",)
            )
        ]
        l6_strict_row = _print_layer(
            "+ regime == Risk_On only (strict)", l6_strict
        )

        # Phase δ checkpoint logic — lift on hit rate.
        lift_default = l6_row["hit_rate_pct"] - baseline["hit_rate_pct"]
        lift_strict = l6_strict_row["hit_rate_pct"] - baseline["hit_rate_pct"]
        n_kept_default = (
            100.0 * l6_row["n"] / baseline["n"] if baseline["n"] else 0.0
        )
        n_kept_strict = (
            100.0 * l6_strict_row["n"] / baseline["n"] if baseline["n"] else 0.0
        )

        print()
        print(
            f"  Hit-rate lift (Layer 0 → + default): "
            f"{baseline['hit_rate_pct']:.1f}% → {l6_row['hit_rate_pct']:.1f}% "
            f"(Δ {lift_default:+.1f}pp; N kept {l6_row['n']} of "
            f"{baseline['n']} = {n_kept_default:.0f}%)"
        )
        print(
            f"  Hit-rate lift (Layer 0 → + strict):  "
            f"{baseline['hit_rate_pct']:.1f}% → "
            f"{l6_strict_row['hit_rate_pct']:.1f}% "
            f"(Δ {lift_strict:+.1f}pp; N kept {l6_strict_row['n']} of "
            f"{baseline['n']} = {n_kept_strict:.0f}%)"
        )
        best_lift = max(lift_default, lift_strict)
        if best_lift >= 4.0:
            verdict = "≥ 4pp lift — DIAMOND STACK VALIDATED on InvestQuest"
        elif best_lift >= 1.0:
            verdict = "1-3pp lift — mild compound; proceed with measured expectations"
        elif best_lift > -1.0:
            verdict = "≈ 0pp lift — Diamond stacking broken on this universe"
        else:
            verdict = "Class 6 HURTS — regime classifier misaligned, investigate"
        print(f"  → Phase δ checkpoint: {verdict}")
        summary_rows.append({
            "cohort": cohort_name,
            "lift_default": lift_default,
            "lift_strict": lift_strict,
            "best_lift": best_lift,
        })

    # ─── Final summary ───
    print()
    print("=" * 130)
    print("PHASE δ CHECKPOINT — Class 6 regime filter lift across cohorts")
    print("=" * 130)
    for s in summary_rows:
        print(
            f"  {s['cohort']:<45} hit-rate lift @ default: {s['lift_default']:+.1f}pp, "
            f"@ strict: {s['lift_strict']:+.1f}pp, best: {s['best_lift']:+.1f}pp"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
