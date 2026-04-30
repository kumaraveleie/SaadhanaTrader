"""Daily scan CLI — Phase C end-to-end runner.

Usage::

    python scripts/daily_scan.py \\
        --fundamentals data/fundamentals_2026Q4.parquet \\
        --output signals/2026-04-29.json

The CLI does three jobs the unit-tested ``run_scan`` cannot do:
  1. Pull / refresh the Nifty 50 OHLCV cache from yfinance
  2. Pull the index OHLCV (^NSEI)
  3. Read the fundamentals snapshot from disk
…and then hands a callable ``ohlcv_provider`` plus the index frame to
``saadhana_filter.scan.daily.run_scan``.

The Phase M cron eventually wraps this script in a GitHub Actions
workflow.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from saadhana_filter.data.loader import load_eod
from saadhana_filter.scan.daily import run_scan, scan_to_json
from saadhana_filter.scan.universe import NIFTY_50

NIFTY_INDEX_TICKER = "^NSEI"


def _build_provider(refresh: bool) -> callable:
    def provider(symbol: str) -> pd.DataFrame:
        return load_eod(symbol, refresh=refresh)

    return provider


def _load_index(refresh: bool) -> pd.DataFrame:
    """Pull the Nifty 50 index frame separately — yfinance treats the
    index ticker (``^NSEI``) outside the ``.NS`` convention. Uses
    ``Ticker.history`` which always returns flat columns (unlike
    ``yf.download`` which returns MultiIndex on recent versions)."""
    import yfinance as yf

    df = yf.Ticker(NIFTY_INDEX_TICKER).history(period="2y", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {NIFTY_INDEX_TICKER}")
    df = df.rename(columns=str.lower)
    if "adj close" in df.columns and "close" not in df.columns:
        df["close"] = df["adj close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["open", "high", "low", "close", "volume"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Saadhana daily scan (Phase C).")
    parser.add_argument(
        "--fundamentals",
        required=True,
        type=Path,
        help="Path to a Parquet/CSV with the §4 Tier 1 columns (symbol-indexed).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination path for the §15 JSON output.",
    )
    parser.add_argument(
        "--scan-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today(),
        help="Override the scan date (default: today, UTC).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Bypass the Parquet cache and re-pull from yfinance.",
    )
    parser.add_argument(
        "--universe",
        nargs="*",
        default=list(NIFTY_50),
        help="Override the universe symbol list (default: bundled Nifty 50).",
    )
    args = parser.parse_args(argv)

    fundamentals_path = Path(args.fundamentals)
    if fundamentals_path.suffix.lower() == ".csv":
        fundamentals = pd.read_csv(fundamentals_path).set_index("symbol")
    else:
        fundamentals = pd.read_parquet(fundamentals_path)
        if "symbol" in fundamentals.columns:
            fundamentals = fundamentals.set_index("symbol")

    nifty_df = _load_index(refresh=args.refresh)
    provider = _build_provider(refresh=args.refresh)

    result = run_scan(
        scan_date=args.scan_date,
        universe=tuple(args.universe),
        fundamentals=fundamentals,
        nifty_df=nifty_df,
        ohlcv_provider=provider,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = scan_to_json(result)
    args.output.write_text(payload, encoding="utf-8")

    # Also write signals/latest.json next to the dated file so the
    # Next.js trader app has a stable filename to read. Atomic via
    # write-temp-then-rename so a partial write never serves stale-and-
    # corrupted JSON to the public scanner page.
    latest_path = args.output.parent / "latest.json"
    tmp_path = latest_path.with_suffix(".json.tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(latest_path)

    summary = {
        "scan_date": result["scan_date"],
        "regime": result["regime"],
        "universe_size": result["universe_size"],
        "tier1_passed": result["tier1_passed"],
        "candidates": len(result["candidates"]),
    }
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
