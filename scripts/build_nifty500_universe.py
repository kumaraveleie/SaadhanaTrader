"""Pull NSE's official Nifty 500 list + build a sector-aware fundamentals
snapshot for Phase G1's broadened backtest.

Fetches https://archives.nseindia.com/content/indices/ind_nifty500list.csv
(public, no auth, refreshed by NSE on index changes), maps the
``Industry`` column to the §4.1 sector buckets the Tier 1 gate uses
(``BANK`` / ``NBFC`` / ``FINANCIAL_SERVICES`` triggers the alternate
gate), and writes:

  data/nifty500_constituents.csv     — raw symbol + industry list
  data/fundamentals_nifty500.parquet — Tier-1-shaped fundamentals
                                       (pass-through defaults; ITC is
                                       still the explicit failure case)

The fundamentals defaults are deliberately permissive: production should
replace this with a Screener.in CSV importer per spec §20.3. Until then
the backtest exercises the §4 gate primarily through the bank/NBFC sector
branch, not through the data fields.
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

NIFTY_500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

# Map NSE's "Industry" column → §4.1 sector buckets used by the Tier 1
# gate. Anything not listed here falls through to "INDUSTRIAL" (the
# general non-financial bucket — D/E gate applies).
INDUSTRY_TO_SECTOR: dict[str, str] = {
    "Financial Services": "FINANCIAL_SERVICES",  # Many NBFCs + insurers + AMCs
    "Banking": "BANK",
    "Banks": "BANK",
}

# Some Nifty 500 names are clearly banks/NBFCs but NSE labels them under
# the broader "Financial Services" umbrella. Override here so the §4.1
# alternate gate (GNPA + CAR replacing D/E) applies correctly.
SYMBOL_BANK_NBFC_OVERRIDES: frozenset[str] = frozenset(
    {
        # Banks
        "AXISBANK",
        "BANDHANBNK",
        "BANKBARODA",
        "CANBK",
        "CUB",
        "FEDERALBNK",
        "HDFCBANK",
        "ICICIBANK",
        "IDFCFIRSTB",
        "INDIANB",
        "INDUSINDBK",
        "IOB",
        "KARURVYSYA",
        "KOTAKBANK",
        "PNB",
        "RBLBANK",
        "SBIN",
        "UCOBANK",
        "UNIONBANK",
        "YESBANK",
        # NBFCs (the largest)
        "BAJFINANCE",
        "BAJAJFINSV",
        "CHOLAFIN",
        "HDFCAMC",
        "MUTHOOTFIN",
        "L&TFH",
        "LICHSGFIN",
        "MANAPPURAM",
        "PEL",
        "PFC",
        "RECLTD",
        "SBICARD",
        "SHRIRAMFIN",
        "SUNDARMFIN",
    }
)


def _classify_sector(symbol: str, industry: str) -> str:
    if symbol.upper() in SYMBOL_BANK_NBFC_OVERRIDES:
        # Most overrides are full banks; NBFCs are the rest. Heuristic:
        # symbol ends with BANK / BARODA / BNK → BANK; otherwise NBFC.
        s = symbol.upper()
        if "BANK" in s or s in {
            "SBIN",
            "PNB",
            "CUB",
            "IOB",
            "INDIANB",
            "UCOBANK",
            "UNIONBANK",
        }:
            return "BANK"
        return "NBFC"
    return INDUSTRY_TO_SECTOR.get(industry.strip(), "INDUSTRIAL")


def fetch_nifty500() -> list[dict]:
    """Download the live Nifty 500 constituent list from NSE.

    Returns list of {Symbol, Company Name, Industry, ...} dicts. Raises
    on network failure.
    """
    req = urllib.request.Request(NIFTY_500_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(data))
    return [row for row in reader if row.get("Symbol")]


# Conservative pass-through defaults. Real production replaces this with
# a Screener.in importer (§20.3). Banks/NBFCs/FS get clean GNPA + healthy
# CAR so the §4.1 alternate gate is exercised.
PASSING_INDUSTRIAL = {
    "market_cap_cr": 25_000.0,  # well above the 5,000 floor
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
PASSING_FINANCIAL = {
    **PASSING_INDUSTRIAL,
    "debt_to_equity": 8.0,  # banks always have high D/E (gate ignored anyway)
    "gnpa": 1.5,
    "car": 16.0,
}

PER_SYMBOL_OVERRIDES: dict[str, dict] = {
    "ITC": {"promoter_holding_pct": 0.0},  # known §4 failure (no promoter)
}


def build_fundamentals(constituents: list[dict]) -> pd.DataFrame:
    rows = []
    for r in constituents:
        sym = r["Symbol"].strip()
        sector = _classify_sector(sym, r.get("Industry", ""))
        base = (
            PASSING_FINANCIAL
            if sector in {"BANK", "NBFC", "FINANCIAL_SERVICES"}
            else PASSING_INDUSTRIAL
        )
        row = {"symbol": sym, "sector": sector, **base}
        row.update(PER_SYMBOL_OVERRIDES.get(sym, {}))
        rows.append(row)
    return pd.DataFrame(rows).set_index("symbol")


def main() -> int:
    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching Nifty 500 constituents from NSE...", file=sys.stderr)
    constituents = fetch_nifty500()
    print(f"  got {len(constituents)} rows", file=sys.stderr)

    csv_path = out_dir / "nifty500_constituents.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Symbol", "Company Name", "Industry", "Series", "ISIN Code"]
        )
        writer.writeheader()
        for r in constituents:
            writer.writerow(
                {
                    k: r.get(k, "")
                    for k in [
                        "Symbol",
                        "Company Name",
                        "Industry",
                        "Series",
                        "ISIN Code",
                    ]
                }
            )
    print(f"  wrote {csv_path}", file=sys.stderr)

    fundamentals = build_fundamentals(constituents)
    fund_path = out_dir / "fundamentals_nifty500.parquet"
    fundamentals.to_parquet(fund_path, engine="pyarrow", compression="snappy")
    print(
        f"  wrote {fund_path} ({len(fundamentals)} rows)",
        file=sys.stderr,
    )

    sector_counts = fundamentals["sector"].value_counts().to_dict()
    print(f"  sectors: {sector_counts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
