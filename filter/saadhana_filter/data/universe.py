"""§2 InvestQuest tradeable-universe loader.

Filters every candidate symbol against MCap ≥ ₹5,000 Cr AND trailing
60-bar ADV ≥ ₹5 Cr. Caches the per-day snapshot to
``~/.saadhana/data/universe/<YYYY-MM-DD>.parquet`` so subsequent calls
on the same date return identical population (point-in-time replay
discipline — required by Sec.11 backtest envelope and Sec.18
forensics drift detection).

Replaces the industrial-only Nifty 500 universe used in v2.1 G1. See
``spec/filter_spec_v2_1.md`` §0.6 (section reservations) and
``investquest-architecture-review.html`` v1.2.

Architecture notes:
- **Fetcher seams** — ``market_cap_fetcher`` and ``ohlcv_fetcher`` are
  injectable callables. Default fetchers use yfinance + the existing
  Parquet OHLCV cache; tests substitute deterministic stubs.
- **Append-only cache** — once a day's snapshot lands on disk,
  subsequent calls (without ``refresh=True``) return it untouched.
  This is what makes "rebaseline G1 on the new universe" reproducible.
- **Seed list** — v1 uses Nifty 500 constituents as the candidate
  pool. Expanding to the full NSE master list (target ~800–1000
  qualifying names) lands in a follow-up; tracked in the
  prioritization matrix.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

DEFAULT_CACHE_DIR = Path.home() / ".saadhana" / "data" / "universe"
DEFAULT_MIN_MARKET_CAP_CR = 5000.0
DEFAULT_MIN_ADV_CR = 5.0
ADV_LOOKBACK_BARS = 60

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONSTITUENTS_CSV = REPO_ROOT / "data" / "nifty500_constituents.csv"

UNIVERSE_COLUMNS = ("market_cap_cr", "adv_cr", "sector", "is_in_nifty500")

# Test-time seams — caller can replace to avoid the network.
MarketCapFetcher = Callable[[str], Optional[float]]   # symbol → ₹ Crore
OhlcvFetcher = Callable[[str], pd.DataFrame]          # symbol → OHLCV DataFrame

# ──────────────────────────────────────────────────────────────────────
# TODO(yfinance-gap): TATAMOTORS and LTIM consistently 404 from
# yfinance Ticker.info as of 2026-05-02 (retried in fresh session,
# both .NS and .BO suffixes; info dict returns just trailingPegRatio
# with no marketCap key). Mega-cap fallback dict below prevents silent
# drops on the CAP side. Expand to ~top-50 by market cap and refresh
# quarterly.
#
# IMPORTANT scope: this fallback only covers the market-cap fetch.
# TATAMOTORS is also absent from the local OHLCV Parquet cache (the
# original cache build hit yfinance gaps too), so ADV gating still
# drops it even with the cap fallback active. LTIM has cached OHLCV
# and passes once the cap fallback applies. A complete fix needs an
# OHLCV-side fallback as well — likely sourced from Stooq or NSE
# bhavcopy for symbols where yfinance is permanently broken.
#
# Long-term fix: switch the market-cap source to an NSE-master-list-
# driven Parquet snapshot AND add an OHLCV secondary source — both
# eliminate the yfinance dependency for affected symbols. Tracked in
# the prioritization matrix.
#
# Each value is a CONSERVATIVE FLOOR — "this name is at least this
# large", not a precise market cap.
# ──────────────────────────────────────────────────────────────────────
MEGA_CAP_FALLBACK_CR: dict[str, float] = {
    "TATAMOTORS": 250000.0,   # Tata Motors — actual ~₹3 lakh Cr (Apr 2026)
    "LTIM":       100000.0,   # LTIMindtree — actual ~₹1.3 lakh Cr (Apr 2026)
}


def _yf_market_cap_cr(symbol: str) -> Optional[float]:
    """Default market-cap fetcher: yfinance ``Ticker.info["marketCap"]``,
    falling back to ``MEGA_CAP_FALLBACK_CR`` when yfinance has a gap.

    yfinance returns market cap in INR; we divide by 1e7 to convert to
    ₹ Crore. Returns ``None`` only when both the live fetch fails AND
    the symbol is not in the mega-cap fallback list — at which point
    caller treats it as "skip this symbol".
    """
    try:
        import yfinance as yf
    except ImportError:
        return MEGA_CAP_FALLBACK_CR.get(symbol)
    try:
        info = yf.Ticker(f"{symbol}.NS").info
        cap = info.get("marketCap")
        if cap is not None and cap != 0:
            return float(cap) / 1e7
    except Exception:  # noqa: BLE001 — best-effort per symbol
        pass
    # yfinance gap — fall back to the hardcoded mega-cap floor when
    # known. See MEGA_CAP_FALLBACK_CR for the rationale.
    return MEGA_CAP_FALLBACK_CR.get(symbol)


def _default_ohlcv_fetcher(symbol: str) -> pd.DataFrame:
    """Default OHLCV fetcher: reads from the existing Parquet cache via
    :func:`saadhana_filter.data.loader.load_eod`."""
    from saadhana_filter.data.loader import load_eod
    return load_eod(symbol)


def _adv_cr(ohlcv: pd.DataFrame, lookback: int = ADV_LOOKBACK_BARS) -> Optional[float]:
    """Trailing N-bar ADV (close × volume mean) in ₹ Crore.

    Returns ``None`` when OHLCV is missing, empty, or shorter than the
    lookback — same "skip this symbol" semantic as the cap fetcher.
    """
    if ohlcv is None or ohlcv.empty:
        return None
    if "close" not in ohlcv.columns or "volume" not in ohlcv.columns:
        return None
    if len(ohlcv) < lookback:
        return None
    tail = ohlcv.tail(lookback)
    daily_value_inr = (tail["close"] * tail["volume"]).mean()
    if pd.isna(daily_value_inr):
        return None
    return float(daily_value_inr) / 1e7


def _load_constituents(constituents_csv: Path) -> dict[str, dict]:
    """Read the Nifty 500 constituents CSV → ``{symbol: {sector, is_nifty500}}``.

    The CSV's ``Industry`` column is what we surface as ``sector`` —
    finer-grained than the broad fundamentals-parquet sector bucket.
    """
    if not constituents_csv.exists():
        return {}
    df = pd.read_csv(constituents_csv)
    return {
        str(row["Symbol"]).strip(): {
            "sector": str(row["Industry"]).strip(),
            "is_nifty500": True,
        }
        for _, row in df.iterrows()
    }


def load_universe(
    *,
    min_market_cap_cr: float = DEFAULT_MIN_MARKET_CAP_CR,
    min_adv_cr: float = DEFAULT_MIN_ADV_CR,
    as_of_date: pd.Timestamp | date | str | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    constituents_csv: Path = DEFAULT_CONSTITUENTS_CSV,
    symbols: Iterable[str] | None = None,
    market_cap_fetcher: MarketCapFetcher | None = None,
    ohlcv_fetcher: OhlcvFetcher | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load InvestQuest tradeable universe for ``as_of_date``.

    Returns DataFrame indexed by symbol, sorted by market cap desc::

        market_cap_cr   float   (₹ Crore)
        adv_cr          float   (₹ Crore, trailing 60-bar mean of
                                 close × volume)
        sector          str     (NSE Industry from constituents CSV;
                                 "Unknown" when symbol is outside the
                                 seed list)
        is_in_nifty500  bool

    Parameters
    ----------
    min_market_cap_cr
        Lower-bound market cap (₹ Crore). Strict-less filters.
    min_adv_cr
        Lower-bound trailing 60-bar ADV (₹ Crore). Strict-less filters.
    as_of_date
        Snapshot date. Default: today (UTC). When ``cache_dir`` already
        has ``<date>.parquet`` and ``refresh=False``, the cached frame
        is returned unchanged — this is the point-in-time replay path.
    refresh
        Force recompute even when the cache hits. Use only when
        upstream data has changed and the snapshot needs to be
        rewritten for the same date.
    constituents_csv
        Path to the Nifty 500 constituents CSV. v1 seed list. Tests
        pass a non-existent path to skip the join.
    symbols
        Override the seed list. ``None`` = use the constituents CSV.
    market_cap_fetcher / ohlcv_fetcher
        Test-time injection seams. ``None`` = production yfinance +
        Parquet cache.
    """
    today = pd.Timestamp(as_of_date or date.today()).normalize()
    cache_path = cache_dir / f"{today.date().isoformat()}.parquet"

    if cache_path.exists() and not refresh:
        return pd.read_parquet(cache_path)

    market_cap_fetcher = market_cap_fetcher or _yf_market_cap_cr
    ohlcv_fetcher = ohlcv_fetcher or _default_ohlcv_fetcher
    constituents = _load_constituents(constituents_csv)

    if symbols is None:
        # TODO(universe-seed-expansion): v1 seed list = Nifty 500
        # constituents (~500 names from data/nifty500_constituents.csv).
        # Spec target is ~800-1000 qualifying names — the gap is mid-cap
        # NSE-not-in-Nifty500 names where RPI cohort signals live.
        # Expand BEFORE Wave 1 (cohort #2 = RPI spurt + crossover) lands,
        # otherwise RPI signals will be starved of mid-cap candidates.
        # Path: add NSE master-list ingestion (CSV from NSE site, or
        # Vercel Postgres table once Sec.17 ledger ships).
        symbols = list(constituents.keys())

    rows: list[dict] = []
    for symbol in symbols:
        cap = market_cap_fetcher(symbol)
        if cap is None or cap < min_market_cap_cr:
            continue
        try:
            ohlcv = ohlcv_fetcher(symbol)
        except Exception:  # noqa: BLE001 — best-effort per symbol
            continue
        adv = _adv_cr(ohlcv)
        if adv is None or adv < min_adv_cr:
            continue
        meta = constituents.get(symbol, {})
        rows.append(
            {
                "symbol": symbol,
                "market_cap_cr": round(cap, 2),
                "adv_cr": round(adv, 4),
                "sector": meta.get("sector", "Unknown"),
                "is_in_nifty500": bool(meta.get("is_nifty500", False)),
            }
        )

    if rows:
        df = pd.DataFrame(rows).set_index("symbol")
    else:
        # Empty result — keep the schema stable so downstream
        # consumers don't have to special-case empty universes.
        df = pd.DataFrame(
            {col: pd.Series(dtype="object" if col == "sector" else "float64")
             for col in UNIVERSE_COLUMNS},
            index=pd.Index([], name="symbol"),
        )
        df["is_in_nifty500"] = df["is_in_nifty500"].astype("bool")

    df = df.sort_values("market_cap_cr", ascending=False)

    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path)
    return df
