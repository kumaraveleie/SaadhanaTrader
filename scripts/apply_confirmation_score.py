"""Action 1 — apply the 5-point confirmation score as a Layer-7
post-hoc filter on the corrected combined-config TC trade list.

Reports trade count, hit rate, PF, Sharpe, and ₹1L cash return at
filter strengths {≥ 2/5, ≥ 3/5, ≥ 4/5}, plus the no-filter baseline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "filter"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from saadhana_filter.data.loader import load_eod  # noqa: E402
from saadhana_filter.indicators.primitives import macd, rsi, sma  # noqa: E402
from saadhana_filter.quality.confirmation_score import _adx, _rolling_vwap  # noqa: E402

TRACK1_PATH = REPO_ROOT / "spec" / "samples" / "backtest_s23_trades_combined.json"

INITIAL_CAPITAL = 100_000
POS_SIZE_FRAC = 0.20
MAX_CONCURRENT = 5
SLIPPAGE_PCT = 0.004
BROKER_PER_TRADE = 40.0
STCG_RATE = 0.15

RSI_THRESHOLD = 45.0
ADX_THRESHOLD = 15.0
VWAP_WINDOW = 20
SMA_WINDOW = 20


def _per_symbol_indicators(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Compute all 5 indicator series once for the full df."""
    close = df["close"]
    rsi14 = rsi(close, 14).to_numpy(dtype=float)
    adx14 = _adx(df, 14).to_numpy(dtype=float)
    vwap_n = _rolling_vwap(df, VWAP_WINDOW).to_numpy(dtype=float)
    macd_df = macd(close, 12, 26, 9)
    macd_line = macd_df["macd"].to_numpy(dtype=float)
    macd_signal = macd_df["signal"].to_numpy(dtype=float)
    sma20 = sma(close, SMA_WINDOW).to_numpy(dtype=float)
    return {
        "rsi": rsi14,
        "adx": adx14,
        "vwap": vwap_n,
        "macd": macd_line,
        "macd_sig": macd_signal,
        "sma": sma20,
        "close": close.to_numpy(dtype=float),
    }


def _score_at_bar(ind: dict[str, np.ndarray], bar: int) -> int:
    """Compute 0-5 BUY-side confirmation score at the given bar."""
    score = 0
    rsi_v = ind["rsi"][bar]
    if np.isfinite(rsi_v) and rsi_v > RSI_THRESHOLD:
        score += 1
    adx_v = ind["adx"][bar]
    if np.isfinite(adx_v) and adx_v > ADX_THRESHOLD:
        score += 1
    vwap_v = ind["vwap"][bar]
    close_v = ind["close"][bar]
    if np.isfinite(vwap_v) and np.isfinite(close_v) and close_v > vwap_v:
        score += 1
    ml, ms = ind["macd"][bar], ind["macd_sig"][bar]
    if np.isfinite(ml) and np.isfinite(ms) and ml > ms:
        score += 1
    sma_v = ind["sma"][bar]
    if np.isfinite(sma_v) and np.isfinite(close_v) and close_v > sma_v:
        score += 1
    return score


def _metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "hit_rate_pct": 0.0, "pf": None, "sharpe": 0.0,
                "win_rate_pct": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0}
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
        return {"final": INITIAL_CAPITAL, "ret_pct": 0.0, "ann_pct": 0.0, "n_taken": 0}
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


def main() -> int:
    trades = json.loads(TRACK1_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(trades)} trades from corrected Track 1 (combined config)")

    # Group by symbol so we compute indicators once per symbol.
    by_symbol: dict[str, list[dict]] = {}
    for t in trades:
        by_symbol.setdefault(t["symbol"], []).append(t)
    print(f"Computing 5-point confirmation score across {len(by_symbol)} symbols...")

    n_scored = 0
    for sym, sym_trades in by_symbol.items():
        try:
            df = load_eod(sym)
        except Exception:
            for t in sym_trades:
                t["confirm_score"] = None
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        ind = _per_symbol_indicators(df)
        for t in sym_trades:
            entry_dt = pd.Timestamp(t["entry_date"])
            idx = df.index.searchsorted(entry_dt)
            if idx >= len(df) or df.index[idx] != entry_dt:
                t["confirm_score"] = None
                continue
            t["confirm_score"] = _score_at_bar(ind, idx)
            n_scored += 1
        if n_scored % 500 == 0:
            print(f"  scored {n_scored}/{len(trades)}", flush=True)
    print(f"  scored {n_scored}/{len(trades)} (skipped {len(trades) - n_scored})")

    # Filter ladders.
    print()
    print("=" * 110)
    print("ACTION 1 — Confirmation-score filter ladder")
    print("=" * 110)
    print(
        f"| {'Filter strength':<28} | {'N':>5} | {'Hit%':>5} | "
        f"{'Win%':>5} | {'PF':>5} | {'Sharpe':>6} | "
        f"{'Final ₹':>10} | {'Net P&L':>10} | {'Return%':>8} | {'Annual%':>8} |"
    )
    print(f"|{'-' * 30}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 8}|"
          f"{'-' * 12}|{'-' * 12}|{'-' * 10}|{'-' * 10}|")

    rows = []
    for label, threshold in [
        ("Baseline (no confirmation)", None),
        ("+ score ≥ 2/5", 2),
        ("+ score ≥ 3/5", 3),
        ("+ score ≥ 4/5", 4),
        ("+ score == 5/5 (max)", 5),
    ]:
        if threshold is None:
            sub = [t for t in trades if t.get("confirm_score") is not None]
        else:
            sub = [t for t in trades if (t.get("confirm_score") or 0) >= threshold]
        m = _metrics(sub)
        c = _cash_3yr(sub)
        print(
            f"| {label:<28} | {m['n']:>5} | {m['hit_rate_pct']:>4.1f}% | "
            f"{m['win_rate_pct']:>4.1f}% | {m['pf']!s:>5} | {m['sharpe']:>+6.2f} | "
            f"₹{c['final']:>9,.0f} | ₹{c['net_pnl']:>+9,.0f} | "
            f"{c['ret_pct']:>+7.2f}% | {c['ann_pct']:>+7.2f}% |"
        )
        rows.append({"label": label, "threshold": threshold, **m, **c})

    # Distribution of scores.
    print()
    print("Score distribution across the 2980 trades:")
    score_counts = pd.Series([t.get("confirm_score") for t in trades]).value_counts(
        dropna=False
    ).sort_index()
    for s, n in score_counts.items():
        s_label = f"score={s}" if s is not None else "score=None (no OHLCV)"
        print(f"  {s_label:<25} {n}")

    # Stack on top of 3-of-3 conviction.
    print()
    print("=" * 110)
    print("ACTION 1 (alt) — Confirmation × 3-of-3 stacked filter")
    print("=" * 110)
    print(
        f"| {'Filter (3-of-3 + score≥X)':<28} | {'N':>5} | {'Hit%':>5} | "
        f"{'Win%':>5} | {'PF':>5} | {'Sharpe':>6} | "
        f"{'Final ₹':>10} | {'Net P&L':>10} | {'Return%':>8} | {'Annual%':>8} |"
    )
    print(f"|{'-' * 30}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 7}|{'-' * 8}|"
          f"{'-' * 12}|{'-' * 12}|{'-' * 10}|{'-' * 10}|")
    high_only = [t for t in trades if t.get("conviction") == "high"]
    for label, threshold in [
        ("3-of-3 only (Layer 1)", None),
        ("3-of-3 + score ≥ 3/5", 3),
        ("3-of-3 + score ≥ 4/5", 4),
        ("3-of-3 + score == 5/5", 5),
    ]:
        if threshold is None:
            sub = high_only
        else:
            sub = [t for t in high_only if (t.get("confirm_score") or 0) >= threshold]
        m = _metrics(sub)
        c = _cash_3yr(sub)
        print(
            f"| {label:<28} | {m['n']:>5} | {m['hit_rate_pct']:>4.1f}% | "
            f"{m['win_rate_pct']:>4.1f}% | {m['pf']!s:>5} | {m['sharpe']:>+6.2f} | "
            f"₹{c['final']:>9,.0f} | ₹{c['net_pnl']:>+9,.0f} | "
            f"{c['ret_pct']:>+7.2f}% | {c['ann_pct']:>+7.2f}% |"
        )

    # Save the scored trade JSON for Action 2 / spec amendments.
    out = REPO_ROOT / "spec" / "samples" / "backtest_s23_trades_combined_scored.json"
    out.write_text(json.dumps(trades, indent=2), encoding="utf-8")
    print(f"\nScored trade JSON written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
