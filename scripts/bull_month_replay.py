"""Action 2 — bull-trend month replay test.

Find the strongest +5%+ Nifty month in 2023-2026 (using a universe-
mean proxy if Nifty cache is missing), filter our existing 3-year
combined-config trade list to entries inside that month, and apply
sector-breadth + confirmation-score ≥ 3 stacking. Compute ₹1L
return for the month.

If our setup in a strong-trend month produces 30-100% returns, the
friend's '5L in trending month' claim is replicable on real data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "filter"))

from saadhana_filter.data.loader import load_eod  # noqa: E402
from saadhana_filter.data.universe import load_universe  # noqa: E402

TRADES_PATH = REPO_ROOT / "spec" / "samples" / "backtest_s23_trades_combined_scored.json"

INITIAL_CAPITAL = 100_000
POS_SIZE_FRAC = 0.20
MAX_CONCURRENT = 5
SLIPPAGE_PCT = 0.004
BROKER_PER_TRADE = 40.0
STCG_RATE = 0.15
SECTOR_BREADTH_THRESHOLD = 70.0


def _load_nifty_proxy() -> pd.Series:
    """Try Nifty (^NSEI) from local cache; fall back to a universe-mean
    daily-return proxy if no Nifty data is available."""
    for ticker in ("^NSEI", "NIFTY", "NIFTY50"):
        try:
            df = load_eod(ticker)
            df.columns = [c.lower() for c in df.columns]
            df.index = pd.to_datetime(df.index).tz_localize(None)
            print(f"  Using Nifty index OHLCV from cache: {ticker}")
            return df["close"]
        except Exception:
            continue

    print("  No Nifty index in cache — using universe-mean daily close as proxy")
    from datetime import date, timedelta
    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))

    closes = []
    for sym in list(universe.head(50).index):  # Top-50 by mcap as the proxy
        try:
            df = load_eod(sym)
        except Exception:
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if "close" not in df.columns or len(df) < 100:
            continue
        # Normalise each name to start at 100 so the mean isn't skewed by price level.
        norm = df["close"] / df["close"].iloc[0] * 100.0
        closes.append(norm.rename(sym))
    if not closes:
        return pd.Series(dtype=float)
    df_all = pd.concat(closes, axis=1)
    return df_all.mean(axis=1)


def _find_best_bull_month(close: pd.Series) -> tuple[pd.Timestamp, float]:
    """Find the strongest single calendar month (Nifty %change)."""
    monthly = close.resample("ME").last().pct_change() * 100.0
    monthly = monthly.dropna()
    best_month_end = monthly.idxmax()
    best_pct = float(monthly.loc[best_month_end])
    print(f"  Best bull month: {best_month_end.date()} (+{best_pct:.2f}%)")
    print("  Top 5 candidates:")
    for d, p in monthly.sort_values(ascending=False).head(5).items():
        print(f"    {d.date()}: {p:+.2f}%")
    return best_month_end, best_pct


def _cash_window(trades: list[dict]) -> dict:
    if not trades:
        return {"final": INITIAL_CAPITAL, "ret_pct": 0.0, "n_taken": 0}
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
    return {
        "final": round(post_tax, 0),
        "net_pnl": round(post_tax - INITIAL_CAPITAL, 0),
        "ret_pct": round(ret_pct, 2),
        "n_taken": n_taken,
    }


def _metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "hit_rate_pct": 0.0, "win_rate_pct": 0.0,
                "pf": None, "avg_win_pct": 0.0, "avg_loss_pct": 0.0}
    rets = np.array([t["return_pct"] for t in trades], dtype=float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    n_t1 = sum(
        1 for t in trades if (t.get("days_to_t1") is not None and t["days_to_t1"] > 0)
    )
    pf = (wins.sum() / abs(losses.sum())) if losses.sum() < 0 else float("nan")
    return {
        "n": len(trades),
        "hit_rate_pct": round(100.0 * n_t1 / len(trades), 1),
        "win_rate_pct": round(100.0 * (rets > 0).sum() / len(rets), 1),
        "avg_win_pct": round(wins.mean() * 100.0, 2) if wins.size else 0.0,
        "avg_loss_pct": round(losses.mean() * 100.0, 2) if losses.size else 0.0,
        "pf": round(pf, 2) if not np.isnan(pf) else None,
    }


def _build_breadth_lookup(
    trade_dates: set[pd.Timestamp], universe: pd.DataFrame
) -> dict[tuple[pd.Timestamp, str], float]:
    """Compute % of symbols in sector with close >= SMA(50) at each date."""
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
    for d in trade_dates:
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


def main() -> int:
    if not TRADES_PATH.exists():
        print(f"ERROR: scored trade JSON missing — run apply_confirmation_score.py first")
        return 2
    trades = json.loads(TRADES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(trades)} scored trades from Track 1 (combined)")

    print("\nResolving Nifty proxy...")
    nifty = _load_nifty_proxy()
    if nifty.empty:
        print("Could not build Nifty proxy. Aborting.")
        return 2

    print("\nFinding best bull month...")
    best_end, best_pct = _find_best_bull_month(nifty)

    # Month boundaries — Nifty 'best month' is the period (best_end - 1 month, best_end].
    month_start = (best_end.replace(day=1))
    print(f"\nBull-month window: {month_start.date()} → {best_end.date()} (+{best_pct:.2f}%)")

    # Filter trades whose entry_date is in the bull month.
    in_month = []
    for t in trades:
        d = pd.Timestamp(t["entry_date"])
        if month_start <= d <= best_end:
            in_month.append(t)
    print(f"Trades entered during bull month: {len(in_month)}")

    if not in_month:
        print("No trades in bull month — cannot replay.")
        return 0

    # Filter ladder
    print()
    print("=" * 110)
    print(f"BULL-MONTH REPLAY — {month_start.date()} → {best_end.date()} (Nifty/proxy +{best_pct:.2f}%)")
    print("=" * 110)
    print(
        f"| {'Filter':<35} | {'N':>5} | {'Hit%':>5} | {'Win%':>5} | "
        f"{'PF':>5} | {'AvgW':>7} | {'AvgL':>7} | "
        f"{'Final ₹':>10} | {'Net P&L':>9} | {'Return%':>8} |"
    )
    print(f"|{'-' * 37}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|"
          f"{'-' * 9}|{'-' * 9}|{'-' * 12}|{'-' * 11}|{'-' * 10}|")

    # Pre-compute breadth lookup over the bull month dates.
    from datetime import date, timedelta
    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))
    print(f"  Computing sector-breadth across {len({pd.Timestamp(t['entry_date']) for t in in_month})} unique dates...")
    breadth_lookup = _build_breadth_lookup(
        {pd.Timestamp(t["entry_date"]) for t in in_month}, universe
    )
    print(f"  Breadth lookup built ({len(breadth_lookup)} (date, sector) pairs)")
    print()
    print(
        f"| {'Filter':<35} | {'N':>5} | {'Hit%':>5} | {'Win%':>5} | "
        f"{'PF':>5} | {'AvgW':>7} | {'AvgL':>7} | "
        f"{'Final ₹':>10} | {'Net P&L':>9} | {'Return%':>8} |"
    )
    print(f"|{'-' * 37}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|"
          f"{'-' * 9}|{'-' * 9}|{'-' * 12}|{'-' * 11}|{'-' * 10}|")

    def _filter_breadth(ts: list[dict]) -> list[dict]:
        return [
            t for t in ts
            if breadth_lookup.get(
                (pd.Timestamp(t["entry_date"]), t.get("sector", "Unknown"))
            ) is not None
            and breadth_lookup[(pd.Timestamp(t["entry_date"]), t.get("sector", "Unknown"))]
            > SECTOR_BREADTH_THRESHOLD
        ]

    def _filter_score(ts: list[dict], threshold: int) -> list[dict]:
        return [t for t in ts if (t.get("confirm_score") or 0) >= threshold]

    for label, fn in [
        ("All TC entries (combined)", lambda t: t),
        ("+ sector breadth > 70", _filter_breadth),
        ("+ score ≥ 3/5", lambda t: _filter_score(t, 3)),
        ("+ breadth > 70 AND score ≥ 3", lambda t: _filter_score(_filter_breadth(t), 3)),
    ]:
        sub = fn(in_month) if not isinstance(fn, type(lambda: 0)) else fn(in_month)
        m = _metrics(sub)
        c = _cash_window(sub)
        print(
            f"| {label:<35} | {m['n']:>5} | {m['hit_rate_pct']:>4.1f}% | "
            f"{m['win_rate_pct']:>4.1f}% | {m['pf']!s:>5} | "
            f"{m['avg_win_pct']:>+6.2f}% | {m['avg_loss_pct']:>+6.2f}% | "
            f"₹{c['final']:>9,.0f} | ₹{c['net_pnl']:>+8,.0f} | "
            f"{c['ret_pct']:>+7.2f}% |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
