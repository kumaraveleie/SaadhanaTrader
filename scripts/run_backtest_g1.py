"""Phase G1 — technical-only backtest runner.

Replays the §5 v2 system on a configurable universe (default: Nifty 50)
over the most recent 3 years using whatever OHLCV the local cache
holds. Writes the report to ``spec/samples/backtest_report_g1*.md`` and
prints the §11 metric banner to stderr.

For Nifty 500 runs, pass:
    --fundamentals data/fundamentals_nifty500.parquet
    --report spec/samples/backtest_report_g1_nifty500.md
    --metrics-json spec/samples/backtest_g1_nifty500_metrics.json

…the universe symbols and sectors are derived from the fundamentals
frame's index + ``sector`` column, so the script doesn't need a separate
universe argument when fundamentals are passed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from saadhana_filter.backtest.metrics import compute_metrics, metrics_to_dict
from saadhana_filter.backtest.replay import BacktestConfig, run_backtest
from saadhana_filter.backtest.report import render_markdown_report
from saadhana_filter.data.loader import load_eod
from saadhana_filter.scan.universe import NIFTY_50

NIFTY_INDEX_TICKER = "^NSEI"


def _load_index() -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(NIFTY_INDEX_TICKER).history(period="max", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {NIFTY_INDEX_TICKER}")
    df = df.rename(columns=str.lower)
    if "adj close" in df.columns and "close" not in df.columns:
        df["close"] = df["adj close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["open", "high", "low", "close", "volume"]]


def _load_ohlcv_dict(
    symbols: list[str],
    refresh: bool,
    *,
    start: date,
    end: date,
) -> dict[str, pd.DataFrame]:
    """Load each symbol's OHLCV slice. Forces a deep history pull when
    the cache holds fewer than the replay window's bars."""
    out: dict[str, pd.DataFrame] = {}
    needed_start = pd.Timestamp(start) - pd.Timedelta(
        days=400
    )  # buffer for 252-bar lookback
    for s in symbols:
        try:
            df = load_eod(s, start=needed_start, end=end, refresh=refresh)
            # If the cache covers less than the replay window, force a refresh.
            if not refresh and df.index.min() > needed_start:
                df = load_eod(s, start=needed_start, end=end, refresh=True)
            out[s] = df
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {s}: {exc}", file=sys.stderr)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase G1 — technical-only backtest")
    parser.add_argument("--start", type=lambda s: date.fromisoformat(s))
    parser.add_argument(
        "--end", type=lambda s: date.fromisoformat(s), default=date.today()
    )
    parser.add_argument("--universe", nargs="*", default=None)
    parser.add_argument(
        "--fundamentals",
        type=Path,
        default=None,
        help="Optional Parquet at data/fundamentals_<scope>.parquet. When "
        "provided, the universe is derived from its index and the §4 "
        "Tier 1 gate is applied.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("spec/samples/backtest_report_g1.md"),
    )
    parser.add_argument(
        "--metrics-json",
        type=Path,
        default=Path("spec/samples/backtest_g1_metrics.json"),
    )
    parser.add_argument(
        "--refresh", action="store_true", help="bypass cache, re-pull from yfinance"
    )
    args = parser.parse_args(argv)

    # Derive universe + sectors + tier1-passing set from fundamentals
    # when provided; otherwise fall back to bundled Nifty 50 with the
    # legacy "all pass" assumption (matches the original Phase G1 run).
    sectors: dict[str, str] = {}
    fundamentals_passed: set[str] | None = None
    if args.fundamentals is not None:
        from saadhana_filter.signals.tier1 import tier1_filter

        fund = pd.read_parquet(args.fundamentals)
        if "symbol" in fund.columns:
            fund = fund.set_index("symbol")
        universe = tuple(args.universe or fund.index.tolist())
        sectors = fund["sector"].astype(str).to_dict()
        # Apply §4 gate up-front; only passing symbols can enter trades.
        fundamentals_passed = set(tier1_filter(fund).index.astype(str))
        print(
            f"  Tier 1 gate: {len(fundamentals_passed)}/{len(universe)} symbols pass",
            file=sys.stderr,
        )
    else:
        universe = tuple(args.universe or NIFTY_50)

    end = args.end
    start = args.start or (end - timedelta(days=365 * 3 + 30))

    print(
        f"Replaying {start} -> {end} on {len(universe)} symbols...",
        file=sys.stderr,
    )
    nifty_df = _load_index()
    ohlcv = _load_ohlcv_dict(list(universe), refresh=args.refresh, start=start, end=end)

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
    )
    metrics = compute_metrics(result.trades)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render_markdown_report(
            title="Saadhana Backtest — Phase G1 (technical-only)",
            phase_label="G1 — diagnostic gate",
            result=result,
            metrics=metrics,
            generated_at=date.today(),
        ),
        encoding="utf-8",
    )
    # Serialize the trade list alongside the metrics + report. Audit
    # scripts (A4) consume this JSON to recompute per-trade features
    # without re-running the replay.
    trades_path = args.metrics_json.with_name(
        args.metrics_json.stem.replace("_metrics", "_trades") + ".json"
    )
    trades_path.write_text(
        json.dumps(
            [
                {
                    "symbol": t.symbol,
                    "entry_date": t.entry_date.isoformat(),
                    "entry_price": t.entry_price,
                    "exit_date": t.exit_date.isoformat(),
                    "exit_price": t.exit_price,
                    "return_pct": t.return_pct,
                    "days_held": t.days_held,
                    "days_to_t1": t.days_to_t1,
                    "outcome": t.outcome,
                    "pro_setup_score_at_entry": t.pro_setup_score_at_entry,
                    "sector": t.sector,
                }
                for t in result.trades
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    args.metrics_json.write_text(
        json.dumps(metrics_to_dict(metrics), indent=2, default=str),
        encoding="utf-8",
    )

    banner = "PASS" if metrics.overall_passes else "FAIL"
    print(
        json.dumps(
            {
                "phase": "G1",
                "verdict": banner,
                "trades": metrics.n_trades,
                "wins": metrics.n_wins,
                "losses": metrics.n_losses,
                "still_open": metrics.n_still_open,
                "hit_rate_pct": round(metrics.hit_rate_pct, 1),
                "avg_win_pct": round(metrics.avg_win_pct, 2),
                "avg_loss_pct": round(metrics.avg_loss_pct, 2),
                "win_loss_ratio": round(metrics.win_loss_ratio, 2),
                "profit_factor": round(metrics.profit_factor, 2),
                "sharpe": round(metrics.sharpe_annualized, 2),
                "max_consec_losses": metrics.max_consecutive_losses,
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
