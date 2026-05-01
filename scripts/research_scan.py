"""Generate ``signals/research.json`` for the public /research page.

Independent pipeline from ``scripts/daily_scan.py``. Computes a per-
symbol indicator snapshot for every Tier-1-passing symbol (regardless
of whether the symbol is a §5 BUY candidate), classifies a K1 v1
lifecycle tag, and emits the data the /research three panels consume.

Same fundamentals + universe + cache contract as daily_scan.py:

    python scripts/research_scan.py \\
        --fundamentals data/fundamentals_nifty500_excl_fin.parquet \\
        --output signals/research.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from saadhana_filter import __spec_version__
from saadhana_filter.catalysts.daily import build_all_catalysts
from saadhana_filter.data.loader import load_eod
from saadhana_filter.scan.research import build_research_snapshot, snapshot_to_dict
from saadhana_filter.sectors.strength import build_sector_strength, sector_to_dict
from saadhana_filter.signals.tier1 import tier1_filter

NIFTY_INDEX_TICKER = "^NSEI"

DEFAULT_CONSTITUENTS_CSV = Path("data/nifty500_constituents.csv")


def _load_industries(constituents_csv: Path) -> dict[str, str]:
    """Read symbol→NSE Industry mapping from the constituents CSV.

    Industry is finer-grained than the coarse `sector` bucket on the
    fundamentals parquet — surfaces sub-sector ("Capital Goods",
    "Power", "Pharmaceuticals") for the /research table column.
    """
    if not constituents_csv.exists():
        return {}
    df = pd.read_csv(constituents_csv)
    return {str(r["Symbol"]): str(r["Industry"]) for _, r in df.iterrows()}


def _load_index() -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker(NIFTY_INDEX_TICKER).history(period="2y", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {NIFTY_INDEX_TICKER}")
    df = df.rename(columns=str.lower)
    if "adj close" in df.columns and "close" not in df.columns:
        df["close"] = df["adj close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    # yfinance occasionally returns a partial/blank row for the current
    # session before close — drop those so the pct-change computation
    # doesn't propagate NaN into the JSON output.
    df = df.dropna(subset=["close"])
    return df[["open", "high", "low", "close", "volume"]]


def _build_provider(refresh: bool):
    def provider(symbol: str) -> pd.DataFrame:
        return load_eod(symbol, refresh=refresh)

    return provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Saadhana research-snapshot generator.")
    parser.add_argument("--fundamentals", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("signals/research.json"),
    )
    parser.add_argument(
        "--scan-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today(),
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--constituents",
        type=Path,
        default=DEFAULT_CONSTITUENTS_CSV,
        help="CSV of symbol→Industry mapping (default: data/nifty500_constituents.csv)",
    )
    args = parser.parse_args(argv)

    fund = pd.read_parquet(args.fundamentals)
    if "symbol" in fund.columns:
        fund = fund.set_index("symbol")
    universe = tuple(fund.index.astype(str).tolist())
    sectors = fund["sector"].astype(str).to_dict()
    industries = _load_industries(args.constituents)
    fundamentals_passed = set(tier1_filter(fund).index.astype(str))

    print(
        f"Universe={len(universe)}; Tier 1 passing={len(fundamentals_passed)}",
        file=sys.stderr,
    )

    nifty_df = _load_index()
    provider = _build_provider(refresh=args.refresh)

    # §13 Phase D — load catalysts via every active source.
    catalysts = build_all_catalysts(today=args.scan_date)

    snap = build_research_snapshot(
        scan_date=args.scan_date,
        spec_version=__spec_version__,
        universe=universe,
        fundamentals_passed=fundamentals_passed,
        sectors=sectors,
        industries=industries,
        catalysts=catalysts,
        nifty_df=nifty_df,
        ohlcv_provider=provider,
    )

    # M1 v0 — sector strength aggregator (see thinking_engine.md §3.1)
    sector_aggs = build_sector_strength(
        rows=snap.rows,
        nifty_df=nifty_df,
        ohlcv_provider=provider,
    )
    snap.sector_strength = [sector_to_dict(s) for s in sector_aggs]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot_to_dict(snap), indent=2, default=str)
    tmp = args.output.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(args.output)

    summary = {
        "scan_date": snap.scan_date,
        "rows": len(snap.rows),
        "nifty_pct_change_today": round(snap.nifty_pct_change_today * 100, 2),
        "lifecycle_distribution": {
            tag: sum(1 for r in snap.rows if r.lifecycle == tag)
            for tag in ("INITIAL", "CONFIRMED", "LATE", "UNKNOWN")
        },
        "sector_count": len(snap.sector_strength),
        "top_3_sectors": [
            f"{s['sector_label']} {s['today_pct'] * 100:+.2f}%"
            for s in snap.sector_strength[:3]
        ],
        "catalysts_attached": sum(1 for r in snap.rows if r.catalysts),
        "high_conviction_catalysts": sum(
            1 for r in snap.rows if r.has_high_conviction_catalyst
        ),
    }
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
