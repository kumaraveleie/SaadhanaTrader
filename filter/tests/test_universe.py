"""Tests for §2 InvestQuest universe loader."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from saadhana_filter.data.universe import (
    ADV_LOOKBACK_BARS,
    DEFAULT_MIN_ADV_CR,
    DEFAULT_MIN_MARKET_CAP_CR,
    load_universe,
)

# A path that won't exist on disk — tests pass it as ``constituents_csv``
# to skip the Nifty 500 join (we drive the seed list explicitly).
NO_CSV = Path("/__nonexistent__/nifty500_constituents.csv")


def _synth_ohlcv(close: float = 100.0, volume: int = 1_000_000, bars: int = 80) -> pd.DataFrame:
    """Synthetic OHLCV with deterministic close × volume.

    Default: 80 bars at close=100, volume=1M → daily_value = 1e8 INR per
    bar → 10 Cr ADV (above the 5 Cr threshold).
    """
    return pd.DataFrame(
        {
            "open": [close] * bars,
            "high": [close] * bars,
            "low": [close] * bars,
            "close": [close] * bars,
            "volume": [volume] * bars,
        }
    )


def _stub_fetchers(
    market_caps: dict[str, Optional[float]],
    ohlcv_data: dict[str, pd.DataFrame],
):
    """Return (cap_fetcher, ohlcv_fetcher) closures that read injected dicts."""
    def cap_fetcher(symbol: str) -> Optional[float]:
        return market_caps.get(symbol)

    def ohlcv_fetcher(symbol: str) -> pd.DataFrame:
        return ohlcv_data.get(symbol, pd.DataFrame())

    return cap_fetcher, ohlcv_fetcher


# ──────────────────────────────────────────────────────────────────────
# 1. Market-cap filter
# ──────────────────────────────────────────────────────────────────────
def test_excludes_below_mcap(tmp_path: Path):
    caps = {"BIG": 6000.0, "SMALL": 4000.0}  # threshold 5,000 Cr
    cap_f, ohlcv_f = _stub_fetchers(caps, {sym: _synth_ohlcv() for sym in caps})

    df = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=list(caps),
        market_cap_fetcher=cap_f,
        ohlcv_fetcher=ohlcv_f,
    )
    assert "BIG" in df.index
    assert "SMALL" not in df.index
    assert df.loc["BIG", "market_cap_cr"] == 6000.0


def test_below_mcap_threshold_strict_less_than(tmp_path: Path):
    """Symbols at exactly the threshold qualify (strict less-than filter)."""
    caps = {"AT_THRESHOLD": DEFAULT_MIN_MARKET_CAP_CR}
    cap_f, ohlcv_f = _stub_fetchers(caps, {"AT_THRESHOLD": _synth_ohlcv()})

    df = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=list(caps),
        market_cap_fetcher=cap_f,
        ohlcv_fetcher=ohlcv_f,
    )
    assert "AT_THRESHOLD" in df.index


# ──────────────────────────────────────────────────────────────────────
# 2. ADV filter
# ──────────────────────────────────────────────────────────────────────
def test_excludes_below_adv(tmp_path: Path):
    caps = {"LIQUID": 10000.0, "ILLIQUID": 10000.0}
    # LIQUID: close 100 × volume 1M → ADV 10 Cr (above 5 Cr threshold)
    # ILLIQUID: close 100 × volume 100k → ADV 1 Cr (below threshold)
    ohlcv = {
        "LIQUID": _synth_ohlcv(close=100, volume=1_000_000),
        "ILLIQUID": _synth_ohlcv(close=100, volume=100_000),
    }
    cap_f, ohlcv_f = _stub_fetchers(caps, ohlcv)

    df = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=list(caps),
        market_cap_fetcher=cap_f,
        ohlcv_fetcher=ohlcv_f,
    )
    assert "LIQUID" in df.index
    assert "ILLIQUID" not in df.index
    assert df.loc["LIQUID", "adv_cr"] == 10.0


def test_excludes_short_history(tmp_path: Path):
    """Symbols with fewer than the ADV lookback bars get filtered out
    — point-in-time discipline rejects symbols we can't measure."""
    caps = {"NEW_LISTING": 10000.0}
    ohlcv = {"NEW_LISTING": _synth_ohlcv(bars=ADV_LOOKBACK_BARS - 1)}
    cap_f, ohlcv_f = _stub_fetchers(caps, ohlcv)

    df = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=list(caps),
        market_cap_fetcher=cap_f,
        ohlcv_fetcher=ohlcv_f,
    )
    assert df.empty


# ──────────────────────────────────────────────────────────────────────
# 3. Caching
# ──────────────────────────────────────────────────────────────────────
def test_caches_by_date(tmp_path: Path):
    """Second call on the same date returns the cached snapshot — no
    refetch — even when the underlying fetcher would now return
    different data."""
    cap_f1, ohlcv_f1 = _stub_fetchers({"AAA": 10000.0}, {"AAA": _synth_ohlcv()})
    df1 = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["AAA"],
        market_cap_fetcher=cap_f1,
        ohlcv_fetcher=ohlcv_f1,
    )
    assert "AAA" in df1.index

    fetch_count = {"calls": 0}

    def cap_f2(symbol: str) -> Optional[float]:
        fetch_count["calls"] += 1
        # Would fail filter if used — but cache should prevent this.
        return 1.0

    def ohlcv_f2(symbol: str) -> pd.DataFrame:
        fetch_count["calls"] += 1
        return pd.DataFrame()

    df2 = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["AAA"],
        market_cap_fetcher=cap_f2,
        ohlcv_fetcher=ohlcv_f2,
    )
    assert fetch_count["calls"] == 0, "expected zero fetches on cache hit"
    pd.testing.assert_frame_equal(df1, df2)


def test_refresh_bypasses_cache(tmp_path: Path):
    """``refresh=True`` forces recompute even when a cache exists
    (used when upstream data is corrected after the daily snapshot)."""
    cap_f1, ohlcv_f1 = _stub_fetchers({"AAA": 10000.0}, {"AAA": _synth_ohlcv()})
    df1 = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["AAA"],
        market_cap_fetcher=cap_f1,
        ohlcv_fetcher=ohlcv_f1,
    )
    assert df1.index.tolist() == ["AAA"]

    cap_f2, ohlcv_f2 = _stub_fetchers(
        {"AAA": 10000.0, "BBB": 8000.0},
        {"AAA": _synth_ohlcv(), "BBB": _synth_ohlcv()},
    )
    df2 = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["AAA", "BBB"],
        market_cap_fetcher=cap_f2,
        ohlcv_fetcher=ohlcv_f2,
        refresh=True,
    )
    assert "BBB" in df2.index


# ──────────────────────────────────────────────────────────────────────
# 4. Point-in-time replay
# ──────────────────────────────────────────────────────────────────────
def test_point_in_time_replay(tmp_path: Path):
    """Different ``as_of_date`` values produce independent snapshots,
    and each historical date keeps its frozen population on re-load
    — required by §11 backtest replay + §18 forensics envelope."""
    cap_f1, ohlcv_f1 = _stub_fetchers(
        {"DAY1_ONLY": 10000.0}, {"DAY1_ONLY": _synth_ohlcv()}
    )
    df_day1 = load_universe(
        as_of_date=date(2026, 5, 1),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["DAY1_ONLY"],
        market_cap_fetcher=cap_f1,
        ohlcv_fetcher=ohlcv_f1,
    )

    cap_f2, ohlcv_f2 = _stub_fetchers(
        {"DAY2_ONLY": 10000.0}, {"DAY2_ONLY": _synth_ohlcv()}
    )
    df_day2 = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["DAY2_ONLY"],
        market_cap_fetcher=cap_f2,
        ohlcv_fetcher=ohlcv_f2,
    )

    assert df_day1.index.tolist() == ["DAY1_ONLY"]
    assert df_day2.index.tolist() == ["DAY2_ONLY"]

    # Re-loading day 1 returns DAY1's frozen snapshot — even when we
    # provide fetchers that would return entirely different data.
    df_day1_replay = load_universe(
        as_of_date=date(2026, 5, 1),
        cache_dir=tmp_path,
        constituents_csv=NO_CSV,
        symbols=["WHATEVER"],
        market_cap_fetcher=cap_f2,
        ohlcv_fetcher=ohlcv_f2,
    )
    pd.testing.assert_frame_equal(df_day1, df_day1_replay)


# ──────────────────────────────────────────────────────────────────────
# 5. Constituents enrichment
# ──────────────────────────────────────────────────────────────────────
def test_sector_and_is_in_nifty500_from_constituents_csv(tmp_path: Path):
    """When the constituents CSV is present, ``sector`` and
    ``is_in_nifty500`` are populated from it. Symbols outside the CSV
    fall back to ``Unknown`` / ``False``."""
    csv_path = tmp_path / "constituents.csv"
    csv_path.write_text(
        "Symbol,Company Name,Industry,Series,ISIN Code\n"
        "DIVISLAB,Divi's Laboratories,Healthcare,EQ,INE361B01024\n",
        encoding="utf-8",
    )

    caps = {"DIVISLAB": 100000.0, "OUTSIDE_NIFTY": 8000.0}
    ohlcv = {sym: _synth_ohlcv() for sym in caps}
    cap_f, ohlcv_f = _stub_fetchers(caps, ohlcv)

    df = load_universe(
        as_of_date=date(2026, 5, 2),
        cache_dir=tmp_path,
        constituents_csv=csv_path,
        symbols=list(caps),
        market_cap_fetcher=cap_f,
        ohlcv_fetcher=ohlcv_f,
    )
    assert df.loc["DIVISLAB", "sector"] == "Healthcare"
    assert bool(df.loc["DIVISLAB", "is_in_nifty500"]) is True
    assert df.loc["OUTSIDE_NIFTY", "sector"] == "Unknown"
    assert bool(df.loc["OUTSIDE_NIFTY", "is_in_nifty500"]) is False
