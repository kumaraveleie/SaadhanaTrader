"""Act 1 of friend's-report close-out — generalize the 1% daily-loss
cap test to the Pro-setup 13/13 cohort.

Reads spec/samples/backtest_g1_investquest_universe_trades.json
(the existing 3-year Pro-setup G1 run on the InvestQuest universe).
Runs the same `_simulate` capital-curve method as scripts/daily_loss_
cap_backtest.py, comparing baseline vs 1% / 2% / 3% / 5% caps.

The Pro-setup cohort has no sector-breadth filter applied — Pro-setup
IS the cohort, not a base for further layering, so we test the cap
directly on the cohort's emitted trade list.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Reuse the same simulator as the TC test for fair apples-to-apples.
from daily_loss_cap_backtest import _simulate  # noqa: E402

PRO_SETUP_TRADES_PATH = (
    REPO_ROOT / "spec" / "samples" / "backtest_g1_investquest_universe_trades.json"
)


def main() -> int:
    trades = json.loads(PRO_SETUP_TRADES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(trades)} Pro-setup 13/13 trades from G1 InvestQuest run")

    # Trade-pool sanity: chronological span.
    dates = sorted(pd.to_datetime([t["entry_date"] for t in trades]))
    print(
        f"  trade window: {dates[0].date()} → {dates[-1].date()} "
        f"(span ≈ {(dates[-1] - dates[0]).days / 365:.1f} years)"
    )

    print()
    print("=" * 110)
    print("ACT 1 — Daily loss cap on Pro-setup 13/13 (₹1L cash, full G1 universe)")
    print("=" * 110)
    print(
        f"| {'Configuration':<35} | {'Taken':>6} | {'Cap-skipped':>11} | "
        f"{'Final ₹':>10} | {'Net P&L':>10} | {'Return%':>8} | "
        f"{'Annual%':>8} | {'MaxDD%':>7} |"
    )
    print(
        f"|{'-' * 37}|{'-' * 8}|{'-' * 13}|{'-' * 12}|{'-' * 12}|"
        f"{'-' * 10}|{'-' * 10}|{'-' * 9}|"
    )

    rows = []
    for label, cap in [
        ("Pro-setup baseline (no cap)", None),
        ("Pro-setup + 0.5% cap", 0.005),
        ("Pro-setup + 1.0% cap", 0.010),
        ("Pro-setup + 2.0% cap", 0.020),
        ("Pro-setup + 3.0% cap", 0.030),
        ("Pro-setup + 5.0% cap", 0.050),
    ]:
        r = _simulate(trades, max_daily_loss_pct=cap)
        rows.append({"label": label, "cap": cap, **r})
        print(
            f"| {label:<35} | {r['n_taken']:>6} | {r['n_skipped_cap']:>11} | "
            f"₹{r['final']:>9,.0f} | ₹{r['net_pnl']:>+9,.0f} | "
            f"{r['ret_pct']:>+7.2f}% | {r['ann_pct']:>+7.2f}% | "
            f"{r['max_dd_pct']:>6.2f}% |"
        )

    # Verdict — does the cap help, hurt, or do nothing?
    base = next(r for r in rows if r["cap"] is None)
    one_pct = next(r for r in rows if r["cap"] == 0.010)
    two_pct = next(r for r in rows if r["cap"] == 0.020)

    print()
    print("Verdict:")
    print(f"  Pro-setup baseline       : {base['ret_pct']:+.2f}% return, {base['max_dd_pct']:.2f}% maxDD")
    print(f"  Pro-setup + 1.0% cap     : {one_pct['ret_pct']:+.2f}% return, {one_pct['max_dd_pct']:.2f}% maxDD ({one_pct['n_skipped_cap']} cap-skips)")
    print(f"  Pro-setup + 2.0% cap     : {two_pct['ret_pct']:+.2f}% return, {two_pct['max_dd_pct']:.2f}% maxDD ({two_pct['n_skipped_cap']} cap-skips)")

    delta_ret = one_pct["ret_pct"] - base["ret_pct"]
    delta_dd = one_pct["max_dd_pct"] - base["max_dd_pct"]
    if delta_ret > 0.5 and delta_dd < -0.5:
        verdict = "1% cap HELPS Pro-setup (return up + drawdown down) → universal CR"
    elif delta_ret < -0.5:
        verdict = "1% cap HURTS Pro-setup (return down) → cohort-specific CR (TC only)"
    elif abs(delta_ret) <= 0.5 and abs(delta_dd) <= 0.5:
        verdict = "1% cap NEUTRAL on Pro-setup (no material change) → cohort-specific CR (TC only)"
    else:
        verdict = "1% cap MIXED on Pro-setup (some metric moves against) → cohort-specific with documented rationale"
    print(f"\n  → {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
