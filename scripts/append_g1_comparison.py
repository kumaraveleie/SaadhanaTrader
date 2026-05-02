"""Append marketcap breakdown + old-baseline comparison + bootstrap
envelope to the auto-generated G1 backtest report.

S1.3 of the InvestQuest vertical-slice sprint.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "spec" / "samples" / "backtest_report_g1_investquest_universe.md"
TRADES_JSON = REPO / "spec" / "samples" / "backtest_g1_investquest_universe_trades.json"
UNIVERSE_PARQUET = Path.home() / ".saadhana" / "data" / "universe" / "2026-05-02.parquet"

# Old industrial-only baseline (from spec/samples/backtest_report_g1_final.md)
OLD_BASELINE = {
    "n_trades": 95,
    "hit_rate_pct": 41.1,
    "avg_days_to_t1": 11.3,
    "avg_win_pct": 6.19,
    "avg_loss_pct": -2.86,
    "max_consecutive_losses": 7,
    "win_loss_ratio": 2.16,
    "profit_factor": 1.95,
    "sharpe_annualized": 2.81,
    "expectancy_pct": 1.43,
    "median_return_pct": -0.38,
}


def _load_metrics() -> dict:
    p = REPO / "spec" / "samples" / "backtest_g1_investquest_universe_metrics.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _load_trades() -> list[dict]:
    return json.loads(TRADES_JSON.read_text(encoding="utf-8"))


def _load_universe() -> pd.DataFrame:
    return pd.read_parquet(UNIVERSE_PARQUET)


def _mcap_tier(cap_cr: float) -> str:
    if cap_cr >= 100_000:
        return "MEGA (≥ ₹1 lakh Cr)"
    if cap_cr >= 50_000:
        return "LARGE (₹50k–1 lakh Cr)"
    if cap_cr >= 15_000:
        return "MID (₹15k–50k Cr)"
    return "SMALL-MID (₹5k–15k Cr)"


def _marketcap_breakdown(trades: list[dict], universe: pd.DataFrame) -> str:
    """Group trades by marketcap tier of the entry symbol.

    ``trade["return_pct"]`` is stored as a decimal fraction in the
    backtest output (0.06 = 6%). Multiply by 100 for display + use
    0.05 as the +5% win threshold consistent with metrics.py.
    """
    rows: list[dict] = []
    for t in trades:
        sym = t["symbol"]
        if sym not in universe.index:
            tier = "UNKNOWN"
            cap = float("nan")
        else:
            cap = float(universe.loc[sym, "market_cap_cr"])
            tier = _mcap_tier(cap)
        rows.append({**t, "tier": tier, "cap_cr": cap})
    df = pd.DataFrame(rows)
    # "Wins" / "Hit Rate" columns mirror the sector breakdown definition
    # used by metrics.py::_is_win — any positive-return trade counts as
    # a win. The top-level §11 "hit rate (% reaching +5%)" is a separate
    # metric tracked above in the §11 Backtest Validation table.
    out_lines = ["| Tier | Trades | Wins (positive return) | Losses | Avg Return | Hit Rate |", "|---|---:|---:|---:|---:|---:|"]
    for tier in [
        "MEGA (≥ ₹1 lakh Cr)",
        "LARGE (₹50k–1 lakh Cr)",
        "MID (₹15k–50k Cr)",
        "SMALL-MID (₹5k–15k Cr)",
    ]:
        sub = df[df["tier"] == tier]
        if sub.empty:
            continue
        wins = int((sub["return_pct"] > 0).sum())
        losses = len(sub) - wins
        avg_pct = sub["return_pct"].mean() * 100
        hit = wins / len(sub) * 100
        out_lines.append(
            f"| `{tier}` | {len(sub)} | {wins} | {losses} | {avg_pct:+.2f}% | {hit:.1f}% |"
        )
    return "\n".join(out_lines)


def _comparison_table(curr: dict) -> str:
    out = ["| Metric | Old (industrial-only, N=95) | New (InvestQuest, N=129) | Δ |", "|---|---:|---:|---:|"]
    rows = [
        ("Hit rate", "hit_rate_pct", "41.1%", f"{curr['hit_rate_pct']:.1f}%"),
        ("Avg days to T1", "avg_days_to_t1", "11.3", f"{curr['avg_days_to_t1']:.1f}"),
        ("Avg win", "avg_win_pct", "+6.19%", f"+{curr['avg_win_pct']:.2f}%"),
        ("Avg loss", "avg_loss_pct", "−2.86%", f"{curr['avg_loss_pct']:.2f}%"),
        ("Max consec losses", "max_consecutive_losses", "7", str(curr['max_consecutive_losses'])),
        ("Win/loss ratio", "win_loss_ratio", "2.16", f"{curr['win_loss_ratio']:.2f}"),
        ("Profit Factor", "profit_factor", "1.95", f"{curr['profit_factor']:.2f}"),
        ("Sharpe (annualized)", "sharpe_annualized", "2.81", f"{curr['sharpe_annualized']:.2f}"),
        ("Expectancy", "expectancy_pct", "+1.43%", f"+{curr['expectancy_pct']:.2f}%"),
    ]
    for label, key, old, new in rows:
        old_val = OLD_BASELINE[key]
        new_val = curr[key]
        delta = new_val - old_val
        delta_str = f"{delta:+.2f}" if isinstance(delta, float) else f"{delta:+d}"
        out.append(f"| {label} | {old} | {new} | {delta_str} |")
    return "\n".join(out)


def _bootstrap_envelope(trades: list[dict], n_resamples: int = 1000) -> str:
    """Bootstrap each metric's 1-sigma and 2-sigma envelope from the
    trade list. Provides the baseline forensics auto-drift detection
    will compare trailing-window stats against (Sec.18).

    return_pct is fractional in the trades JSON; the bootstrap
    multiplies by 100 internally so the displayed envelope matches
    the percent-scale metrics in the rest of the report.
    """
    rng = np.random.default_rng(seed=20260502)
    # Convert to percent-scale up front so all displays match the
    # report's other percent metrics.
    returns_pct = np.array([t["return_pct"] for t in trades]) * 100
    days = np.array([t["days_held"] for t in trades])

    metrics: dict[str, list[float]] = {
        "hit_rate_pct": [],
        "avg_win_pct": [],
        "avg_loss_pct": [],
        "profit_factor": [],
        "sharpe_annualized": [],
        "win_loss_ratio": [],
    }
    n = len(trades)
    for _ in range(n_resamples):
        idx = rng.integers(0, n, n)
        r = returns_pct[idx]
        wins = r[r >= 5]
        losses = r[r < 5]
        # Approximate metrics consistent with metrics.py
        metrics["hit_rate_pct"].append(len(wins) / n * 100)
        metrics["avg_win_pct"].append(float(wins.mean()) if len(wins) else 0.0)
        metrics["avg_loss_pct"].append(float(losses.mean()) if len(losses) else 0.0)
        gross_win = wins.sum() if len(wins) else 0.0
        gross_loss = -losses.sum() if len(losses) else 0.0
        metrics["profit_factor"].append(gross_win / gross_loss if gross_loss > 0 else float("nan"))
        # Sharpe approx: daily-equivalent r over days_held, × √252
        d = days[idx]
        daily_eq = r / np.where(d > 0, d, 1)
        metrics["sharpe_annualized"].append(
            float((daily_eq.mean() / daily_eq.std()) * np.sqrt(252))
            if daily_eq.std() > 0
            else 0.0
        )
        if len(wins) and len(losses) and losses.mean() != 0:
            metrics["win_loss_ratio"].append(abs(wins.mean() / losses.mean()))

    out_lines = [
        "| Metric | Mean | 1σ | 2σ | 1σ band | 2σ band |",
        "|---|---:|---:|---:|---|---|",
    ]
    for label, key in [
        ("Hit rate (%)", "hit_rate_pct"),
        ("Avg win (%)", "avg_win_pct"),
        ("Avg loss (%)", "avg_loss_pct"),
        ("Profit Factor", "profit_factor"),
        ("Sharpe (annualized)", "sharpe_annualized"),
        ("Win/loss ratio", "win_loss_ratio"),
    ]:
        vals = [v for v in metrics[key] if not np.isnan(v)]
        if not vals:
            continue
        m = statistics.mean(vals)
        sd = statistics.stdev(vals)
        out_lines.append(
            f"| {label} | {m:+.2f} | {sd:.2f} | {2*sd:.2f} | "
            f"[{m-sd:+.2f}, {m+sd:+.2f}] | [{m-2*sd:+.2f}, {m+2*sd:+.2f}] |"
        )
    return "\n".join(out_lines)


def _root_cause_callout(trades: list[dict]) -> str:
    """Surface the financial-sector drag explicitly — the v2.1 §0.5
    amendment foresaw exactly this; the InvestQuest universe expansion
    re-introduces it. return_pct is fractional in the trades JSON."""
    # Hit rate here = % positive return (matches the auto-generated
    # sector breakdown table's column definition).
    df = pd.DataFrame(trades)
    df["return_pct_pct"] = df["return_pct"] * 100
    by_sector = df.groupby("sector").agg(
        n=("symbol", "count"),
        wins=("return_pct", lambda r: (r > 0).sum()),
        avg_pct=("return_pct_pct", "mean"),
    )
    by_sector["hit"] = by_sector["wins"] / by_sector["n"] * 100

    industrial = by_sector.loc["INDUSTRIAL"] if "INDUSTRIAL" in by_sector.index else None
    fin_keys = [k for k in ("FINANCIAL_SERVICES", "NBFC", "BANK") if k in by_sector.index]
    fin_n = by_sector.loc[fin_keys, "n"].sum() if fin_keys else 0
    fin_wins = by_sector.loc[fin_keys, "wins"].sum() if fin_keys else 0
    fin_hit = (fin_wins / fin_n * 100) if fin_n else 0.0
    fin_avg = (
        df[df["sector"].isin(fin_keys)]["return_pct_pct"].mean() if fin_keys else 0.0
    )

    if industrial is None or not fin_keys:
        return "_(no clean industrial vs financial split detected)_"

    blended_hit = (industrial["wins"] + fin_wins) / (industrial["n"] + fin_n) * 100
    return (
        f"**Industrial slice (N={int(industrial['n'])})**: hit "
        f"{industrial['hit']:.1f}%, avg {industrial['avg_pct']:+.2f}% — "
        f"essentially identical to the v2.1 G1-final baseline "
        f"(47.4% / +1.43% on N=95).\n\n"
        f"**Financial cohort (N={int(fin_n)} across "
        f"{', '.join(fin_keys)})**: hit {fin_hit:.1f}%, avg "
        f"{fin_avg:+.2f}%. This is the same signal degradation v2.1 "
        f"§0.5 amendment 1 documented — the A1 experiment showed "
        f"financials at 11% hit / −2.29% avg on 27 trades, which led "
        f"to the financial-sector exclusion. The InvestQuest universe "
        f"expansion re-introduces them. The blended hit rate of "
        f"{blended_hit:.1f}% is therefore not a regression — it's a "
        f"known-shape artifact of the universe choice."
    )


def main() -> None:
    metrics = _load_metrics()
    trades = _load_trades()
    universe = _load_universe()

    appendix = "\n\n---\n\n## Marketcap-tier Breakdown\n\n"
    appendix += _marketcap_breakdown(trades, universe)
    appendix += "\n\n---\n\n## Comparison vs Old Industrial-only Baseline\n\n"
    appendix += _comparison_table(metrics)
    appendix += "\n\n### Root cause — the v2.1 §0.5 financial drag re-emerges\n\n"
    appendix += _root_cause_callout(trades)
    appendix += "\n\n---\n\n## Drift Envelope (bootstrap, 1000 resamples)\n\n"
    appendix += (
        "Forensics auto-drift detection (Sec.18) compares the trailing "
        "4-week stats of every cohort against this envelope. 1σ-out flags; "
        "2σ-out pauses; 3σ-out retires. Bootstrap of the 129 trades:\n\n"
    )
    appendix += _bootstrap_envelope(trades)
    appendix += (
        "\n\n_Bootstrap seed: 20260502 · 1000 resamples · 129 trades. "
        "Replace with rolling-4-week measurements once Sec.18 forensics ships._\n"
    )
    appendix += "\n\n---\n\n## S1.3 Acceptance Status\n\n"
    drift_pp = metrics["hit_rate_pct"] - 41.1
    appendix += (
        "_Acceptance uses the §11 top-level hit rate (% reaching +5%), "
        "NOT the positive-return rate from the sector / marketcap "
        "breakdown tables above._\n\n"
        "| Acceptance criterion | Target | Observed | Verdict |\n"
        "|---|---|---|---|\n"
        f"| Trade count | ≥ 200 | {metrics['n_trades']} | "
        f"{'PASS' if metrics['n_trades'] >= 200 else 'FAIL — see note'} |\n"
        f"| Hit-rate drift vs old baseline | within ±5pp of 41.1% | "
        f"{metrics['hit_rate_pct']:.1f}% (Δ {drift_pp:+.1f}pp) | "
        f"{'PASS' if abs(drift_pp) <= 5 else 'FAIL — see note'} |\n\n"
        "**Note on failures:**\n"
        "- Trade count 129 < 200 because the seed list is still Nifty 500 "
        "(~497 names post-filter). Spec target is ~800–1000 names; reaching "
        "that requires the NSE-master-list expansion (TODO captured in "
        "`universe.py`).\n"
        f"- Hit rate drift {drift_pp:+.1f}pp is OUTSIDE the ±5pp tolerance, "
        "but the Industrial slice on its own posts a positive-return rate "
        "of 47.9% (essentially identical to the old 47.4% baseline). The "
        "drift is a re-emergence of the v2.1 §0.5 financial-sector "
        "exclusion's documented signal degradation — structural, not a "
        "backtest bug.\n\n"
        "**Operator decision required** before S1.4 (spec the four indicator "
        "sections):\n"
        "1. Accept this universe and run Triple confluence on it as-is "
        "(financials may behave differently for the TC pattern), OR\n"
        "2. Apply the v2.1 §0.5 financial-sector exclusion to the InvestQuest "
        "universe filter (universe shrinks to ~362 names), OR\n"
        "3. Defer the universe expansion decision until after the seed-list "
        "expansion lands, then re-baseline.\n"
    )

    text = REPORT.read_text(encoding="utf-8")
    REPORT.write_text(text + appendix, encoding="utf-8")
    print(f"appended {len(appendix):,} bytes to {REPORT}")


if __name__ == "__main__":
    main()
