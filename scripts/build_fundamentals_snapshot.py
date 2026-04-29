"""Build a synthetic-but-realistic fundamentals snapshot for the Nifty 50.

Phase C calls for "fundamentals from disk", but we have no real Screener.in
export bundled (the spec §20.3 expects a manual quarterly export). For the
Phase C smoke test and Phase G1 backtest replay, this script writes a
plausible Parquet with conservative defaults the §4 gate will accept for
most large-cap names while still exercising the gate (a few entries are
intentionally edge-of-spec so the gate filters them).

Real production should replace this with:
    python scripts/import_screener_export.py --csv ~/Downloads/screener_2026Q4.csv

…once the Screener.in export script lands.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from saadhana_filter.scan.universe import NIFTY_50

# Sector classification used by §4.1 (banks/NBFCs use the alternate gate)
SECTOR_MAP: dict[str, str] = {
    "AXISBANK": "BANK",
    "BAJFINANCE": "NBFC",
    "BAJAJFINSV": "NBFC",
    "HDFCBANK": "BANK",
    "ICICIBANK": "BANK",
    "INDUSINDBK": "BANK",
    "KOTAKBANK": "BANK",
    "SBILIFE": "FINANCIAL_SERVICES",
    "SBIN": "BANK",
    "HDFCLIFE": "FINANCIAL_SERVICES",
    "SHRIRAMFIN": "NBFC",
    # Everything else defaults to a non-financial sector below.
}

DEFAULT_SECTOR = "INDUSTRIAL"

# Conservative pass-through defaults: all Nifty 50 names easily exceed
# ₹5,000 Cr market cap; growth assumptions are mild positives so the
# earnings gate passes; D/E and pledge are tiny. Banks/NBFCs get clean
# GNPA + healthy CAR.
PASSING_DEFAULTS = {
    "market_cap_cr": 100_000.0,
    "eps_yoy": 8.0,
    "revenue_yoy": 6.0,
    "promoter_holding_pct": 50.0,
    "promoter_pledge_pct": 0.0,
    "debt_to_equity": 0.5,
    "fno_banned": False,
    "sebi_surveillance": False,
    "gnpa": 0.0,
    "car": 0.0,
}

BANK_NBFC_DEFAULTS = {
    **PASSING_DEFAULTS,
    "debt_to_equity": 8.0,  # banks always carry high D/E (gate ignored anyway)
    "gnpa": 1.5,
    "car": 16.0,
}

# Per-symbol overrides — exercise gate failures realistically:
# - ITC: classic low-promoter-holding name (BAT holds, founders ~ 0%)
# - HDFCBANK: post-merger high promoter holding edge case (set to pass)
# - We keep failures rare so the smoke test still produces candidates.
PER_SYMBOL_OVERRIDES: dict[str, dict] = {
    "ITC": {"promoter_holding_pct": 0.0},  # Likely fails §4 gate
}


def _row_for(symbol: str) -> dict:
    sector = SECTOR_MAP.get(symbol, DEFAULT_SECTOR)
    base = (
        BANK_NBFC_DEFAULTS
        if sector in {"BANK", "NBFC", "FINANCIAL_SERVICES"}
        else PASSING_DEFAULTS
    )
    row = {"symbol": symbol, "sector": sector, **base}
    row.update(PER_SYMBOL_OVERRIDES.get(symbol, {}))
    return row


def build_snapshot() -> pd.DataFrame:
    rows = [_row_for(s) for s in NIFTY_50]
    return pd.DataFrame(rows).set_index("symbol")


def main() -> int:
    out_path = Path("data/fundamentals_2026Q4.parquet")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = build_snapshot()
    df.to_parquet(out_path, engine="pyarrow", compression="snappy")
    print(f"Wrote {len(df)} rows -> {out_path}")
    print("Sectors:", df["sector"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
