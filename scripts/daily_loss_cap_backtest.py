"""Action 4 — backtest with §10.5 daily loss cap = 2% of capital.

Reads the corrected combined-config TC trade list. Walks trades
chronologically by entry_date. At each candidate entry, checks the
cohort's same-day cumulative realised P&L; if it has already dropped
to -max_daily_loss_pct × portfolio, the new entry is rejected.

Compares with-cap vs without-cap to evaluate whether the cap improves
drawdown without significantly hurting returns.

Per the operator's brief, the test is on TC + sector-breadth (the
working Diamond candidate from Track 3), so we apply the breadth
filter first, then layer the daily cap.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "filter"))

from saadhana_filter.data.loader import load_eod  # noqa: E402
from saadhana_filter.data.universe import load_universe  # noqa: E402

TRADES_PATH = REPO_ROOT / "spec" / "samples" / "backtest_s23_trades_combined.json"

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


def _simulate(
    trades: list[dict],
    *,
    max_daily_loss_pct: float | None,
) -> dict:
    """Walk trades chronologically with concurrency cap + optional
    same-day loss cap. Returns capital trajectory + drawdown stats."""
    chrono = sorted(trades, key=lambda t: t["entry_date"])
    capital = INITIAL_CAPITAL
    open_slots: list[tuple[pd.Timestamp, float]] = []
    daily_pnl: dict[pd.Timestamp, float] = defaultdict(float)
    capital_curve: list[tuple[pd.Timestamp, float]] = [
        (pd.Timestamp(chrono[0]["entry_date"]) if chrono else pd.Timestamp.now(), capital)
    ]

    n_taken = 0
    n_skipped_concurrency = 0
    n_skipped_cap = 0
    cap_skip_dates: list[pd.Timestamp] = []

    for t in chrono:
        entry_dt = pd.Timestamp(t["entry_date"])
        # Free expired slots.
        open_slots = [s for s in open_slots if s[0] > entry_dt]
        if len(open_slots) >= MAX_CONCURRENT:
            n_skipped_concurrency += 1
            continue

        # Daily-loss cap check (cohort-level: same-day cumulative P&L
        # already this bad → reject).
        if max_daily_loss_pct is not None:
            threshold = -max_daily_loss_pct * capital
            if daily_pnl[entry_dt] <= threshold:
                n_skipped_cap += 1
                cap_skip_dates.append(entry_dt)
                continue

        position_size = capital * POS_SIZE_FRAC
        gross = position_size * t["return_pct"]
        slippage = position_size * SLIPPAGE_PCT
        net_pnl = gross - slippage - BROKER_PER_TRADE

        capital += net_pnl
        daily_pnl[entry_dt] += net_pnl
        n_taken += 1
        exit_dt = entry_dt + pd.Timedelta(days=int(t["days_held"]) + 5)
        open_slots.append((exit_dt, position_size))
        capital_curve.append((entry_dt, capital))

    # Drawdown.
    peak = INITIAL_CAPITAL
    max_dd = 0.0
    for _, c in capital_curve:
        peak = max(peak, c)
        dd = (peak - c) / peak * 100.0
        max_dd = max(max_dd, dd)

    if capital > INITIAL_CAPITAL:
        post_tax = INITIAL_CAPITAL + (capital - INITIAL_CAPITAL) * (1.0 - STCG_RATE)
    else:
        post_tax = capital
    ret_pct = (post_tax - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0
    ann_pct = (((post_tax / INITIAL_CAPITAL) ** (1.0 / 3.0)) - 1.0) * 100.0

    return {
        "n_taken": n_taken,
        "n_skipped_concurrency": n_skipped_concurrency,
        "n_skipped_cap": n_skipped_cap,
        "cap_skip_dates": cap_skip_dates,
        "final": round(post_tax, 0),
        "net_pnl": round(post_tax - INITIAL_CAPITAL, 0),
        "ret_pct": round(ret_pct, 2),
        "ann_pct": round(ann_pct, 2),
        "max_dd_pct": round(max_dd, 2),
    }


def main() -> int:
    trades = json.loads(TRADES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(trades)} corrected combined-config trades")

    # Apply sector breadth filter first (TC + breadth = working candidate).
    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))
    print(f"  computing sector-breadth lookup across "
          f"{len({pd.Timestamp(t['entry_date']) for t in trades})} unique dates...")
    breadth = _build_breadth_lookup(
        {pd.Timestamp(t["entry_date"]) for t in trades}, universe
    )
    print(f"  breadth lookup built ({len(breadth)} (date, sector) pairs)")

    breadth_filtered = [
        t for t in trades
        if breadth.get((pd.Timestamp(t["entry_date"]), t.get("sector", "Unknown"))) is not None
        and breadth[(pd.Timestamp(t["entry_date"]), t.get("sector", "Unknown"))]
        > SECTOR_BREADTH_THRESHOLD
    ]
    print(f"\nAfter sector-breadth filter (>70%): {len(breadth_filtered)} trades")

    print()
    print("=" * 110)
    print("ACTION 4 — Daily loss cap on TC + sector-breadth (₹1L cash, 3yr)")
    print("=" * 110)
    print(f"| {'Configuration':<35} | {'Taken':>6} | {'Cap-skipped':>11} | {'Final ₹':>10} | {'Net P&L':>10} | {'Return%':>8} | {'Annual%':>8} | {'MaxDD%':>7} |")
    print(f"|{'-' * 37}|{'-' * 8}|{'-' * 13}|{'-' * 12}|{'-' * 12}|{'-' * 10}|{'-' * 10}|{'-' * 9}|")

    rows = []
    for label, cap in [
        ("No cap (baseline)", None),
        ("max_daily_loss_pct = 1.0%", 0.010),
        ("max_daily_loss_pct = 2.0%", 0.020),
        ("max_daily_loss_pct = 3.0%", 0.030),
        ("max_daily_loss_pct = 5.0%", 0.050),
    ]:
        r = _simulate(breadth_filtered, max_daily_loss_pct=cap)
        rows.append({"label": label, "cap": cap, **r})
        print(
            f"| {label:<35} | {r['n_taken']:>6} | {r['n_skipped_cap']:>11} | "
            f"₹{r['final']:>9,.0f} | ₹{r['net_pnl']:>+9,.0f} | "
            f"{r['ret_pct']:>+7.2f}% | {r['ann_pct']:>+7.2f}% | {r['max_dd_pct']:>6.2f}% |"
        )

    print()
    print("Cap-skip dates (under 2% cap):")
    target = next(r for r in rows if r["cap"] == 0.020)
    skip_dates = sorted(set(target["cap_skip_dates"]))
    print(f"  Total cap-skip events: {target['n_skipped_cap']}")
    print(f"  Distinct days hit by cap: {len(skip_dates)}")
    if skip_dates[:6]:
        print(f"  First 6 days where cap fired: " +
              ", ".join(d.strftime("%Y-%m-%d") for d in skip_dates[:6]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
