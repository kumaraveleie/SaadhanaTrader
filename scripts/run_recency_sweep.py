"""Phase G1 — recency-threshold parameter sweep.

Same v2.1 base (financial exclusion, condition #12 = recency AND
not-extended) but varies the recency-window cutoff in calendar days
across {60, 90, 120, 150, 180}. Outputs a single comparison table at
``spec/samples/backtest_g1_recency_sweep.md``.

The sweep is **diagnostic only** — the spec source value
(``RECENT_STRENGTH_LOOKBACK_DAYS = 60``) is patched at runtime; the
canonical contract in ``conditions.py`` is untouched per §16 drift
protocol. Same shadow-patch pattern as A2.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from saadhana_filter.backtest.metrics import compute_metrics
from saadhana_filter.backtest.replay import BacktestConfig, run_backtest
from saadhana_filter.data.loader import load_eod
from saadhana_filter.indicators import conditions as _cond
from saadhana_filter.signals.tier1 import tier1_filter

# Sweep parameters
THRESHOLDS = (60, 90, 120, 150, 180)

ROOT = Path(__file__).resolve().parent.parent
FUND_PATH = ROOT / "data" / "fundamentals_nifty500_excl_fin.parquet"
OUT_PATH = ROOT / "spec" / "samples" / "backtest_g1_recency_sweep.md"


def _load_index() -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker("^NSEI").history(period="max", auto_adjust=False)
    df = df.rename(columns=str.lower)
    if "adj close" in df.columns and "close" not in df.columns:
        df["close"] = df["adj close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["open", "high", "low", "close", "volume"]]


def _load_ohlcv(symbols: list[str], *, start: date, end: date) -> dict[str, pd.DataFrame]:
    needed_start = pd.Timestamp(start) - pd.Timedelta(days=400)
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        try:
            out[s] = load_eod(s, start=needed_start, end=end)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {s}: {exc}", file=sys.stderr)
    return out


def _run_one(
    threshold_days: int,
    *,
    universe: tuple[str, ...],
    fundamentals_passed: set[str],
    sectors: dict[str, str],
    ohlcv: dict[str, pd.DataFrame],
    nifty_df: pd.DataFrame,
    start: date,
    end: date,
) -> dict:
    """Patch the constant, run one backtest, return summary metrics."""
    print(f"\n=== threshold = {threshold_days} days ===", file=sys.stderr)
    _cond.RECENT_STRENGTH_LOOKBACK_DAYS = threshold_days

    config = BacktestConfig(
        universe=universe,
        start_date=start,
        end_date=end,
    )
    result = run_backtest(
        config,
        ohlcv=ohlcv,
        nifty_df=nifty_df,
        fundamentals_passed=fundamentals_passed,
        sectors=sectors,
        progress_every=200,  # light logging during sweep
    )
    m = compute_metrics(result.trades)
    print(
        f"  trades={m.n_trades} hit={m.hit_rate_pct:.1f}% "
        f"avg_win={m.avg_win_pct:+.2f}% avg_loss={m.avg_loss_pct:+.2f}% "
        f"PF={m.profit_factor:.2f} sharpe={m.sharpe_annualized:.2f}",
        file=sys.stderr,
    )
    return {
        "threshold_days": threshold_days,
        "n_trades": m.n_trades,
        "n_wins": m.n_wins,
        "n_losses": m.n_losses,
        "hit_rate_pct": m.hit_rate_pct,
        "avg_win_pct": m.avg_win_pct,
        "avg_loss_pct": m.avg_loss_pct,
        "max_consecutive_losses": m.max_consecutive_losses,
        "win_loss_ratio": m.win_loss_ratio,
        "profit_factor": m.profit_factor,
        "sharpe": m.sharpe_annualized,
        "expectancy_pct": m.expectancy_pct,
    }


def _render_markdown(rows: list[dict], baseline_a1: dict) -> str:
    lines: list[str] = [
        "# Phase G1 — Recency-Threshold Parameter Sweep",
        "",
        f"**Generated:** {date.today().isoformat()}",
        "**Universe:** Nifty 500 industrial-only (`fundamentals_nifty500_excl_fin.parquet`)",
        "**Replay window:** 2023-04-01 → 2026-04-30",
        "**Stop distance:** 3% (spec §5.4 #9 unchanged)",
        "**Sweep variable:** `RECENT_STRENGTH_LOOKBACK_DAYS` in `cond_recent_strength_not_extended`",
        "**Other v2.1 amendments:** financial-sector exclusion already applied via fundamentals.",
        "",
        "---",
        "",
        "## Sweep results",
        "",
        "| Threshold (days) | N | Hit rate | Avg win | Avg loss | Max consec L | W/L ratio | PF | Sharpe |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    # A1 baseline (v2.0 not_extended ≈ infinity, no recency leg)
    lines.append(
        f"| **A1 (v2.0)** | {baseline_a1['n_trades']} | "
        f"{baseline_a1['hit_rate_pct']:.1f}% | "
        f"{baseline_a1['avg_win_pct']:+.2f}% | "
        f"{baseline_a1['avg_loss_pct']:+.2f}% | "
        f"{baseline_a1['max_consecutive_losses']} | "
        f"{baseline_a1['win_loss_ratio']:.2f} | "
        f"{baseline_a1['profit_factor']:.2f} | "
        f"{baseline_a1['sharpe']:.2f} |"
    )
    for r in rows:
        lines.append(
            f"| {r['threshold_days']} | {r['n_trades']} | "
            f"{r['hit_rate_pct']:.1f}% | "
            f"{r['avg_win_pct']:+.2f}% | "
            f"{r['avg_loss_pct']:+.2f}% | "
            f"{r['max_consecutive_losses']} | "
            f"{r['win_loss_ratio']:.2f} | "
            f"{r['profit_factor']:.2f} | "
            f"{r['sharpe']:.2f} |"
        )
    lines += [
        "",
        "## §11 gate reference",
        "",
        "| Metric | Threshold |",
        "|---|---|",
        "| Hit rate | ≥ 60% |",
        "| Avg win | ≥ +8% |",
        "| Avg loss | ≤ -2.5% |",
        "| Max consecutive losses | ≤ 5 |",
        "| Win/loss ratio | ≥ 2.0 |",
        "| Profit Factor | ≥ 1.8 |",
        "| Sharpe (annualized) | ≥ 1.5 |",
        "",
        "## Notes",
        "",
        "- A1 baseline shown for reference; it has no recency leg (the v2.0",
        "  `not_extended` was effectively infinite-day recency).",
        "- The 60-day row is identical to G1d (N=11). The 60-day row may",
        "  differ slightly from G1d if any cache changes occurred between",
        "  runs — check date stamps if so.",
        "- Cache is warm for all 5 sweep iterations (no yfinance pulls).",
        "- Recommendation column intentionally blank — selection criteria",
        "  applied by the human reviewer.",
    ]
    return "\n".join(lines)


def main() -> int:
    fund = pd.read_parquet(FUND_PATH)
    if "symbol" in fund.columns:
        fund = fund.set_index("symbol")
    universe = tuple(fund.index.tolist())
    sectors = fund["sector"].astype(str).to_dict()
    fundamentals_passed = set(tier1_filter(fund).index.astype(str))
    print(
        f"Universe={len(universe)}; Tier 1 passing={len(fundamentals_passed)}",
        file=sys.stderr,
    )

    end = date(2026, 4, 30)
    start = end - timedelta(days=365 * 3 + 30)

    print("Loading index + per-symbol OHLCV (cache-warm)...", file=sys.stderr)
    nifty_df = _load_index()
    ohlcv = _load_ohlcv(list(universe), start=start, end=end)
    print(f"  loaded {len(ohlcv)} symbols", file=sys.stderr)

    rows: list[dict] = []
    for threshold in THRESHOLDS:
        rows.append(
            _run_one(
                threshold,
                universe=universe,
                fundamentals_passed=fundamentals_passed,
                sectors=sectors,
                ohlcv=ohlcv,
                nifty_df=nifty_df,
                start=start,
                end=end,
            )
        )

    # A1 baseline pulled from the existing committed file.
    baseline_path = ROOT / "spec" / "samples" / "backtest_g1_nifty500_excl_fin_metrics.json"
    a1 = json.loads(baseline_path.read_text())
    baseline_a1 = {
        "n_trades": a1["n_trades"],
        "hit_rate_pct": a1["hit_rate_pct"],
        "avg_win_pct": a1["avg_win_pct"],
        "avg_loss_pct": a1["avg_loss_pct"],
        "max_consecutive_losses": a1["max_consecutive_losses"],
        "win_loss_ratio": a1["win_loss_ratio"],
        "profit_factor": a1["profit_factor"],
        "sharpe": a1["sharpe_annualized"],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(_render_markdown(rows, baseline_a1), encoding="utf-8")
    print(f"\nWrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
