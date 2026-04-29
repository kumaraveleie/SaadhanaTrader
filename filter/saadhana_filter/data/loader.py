"""§20.3 — EOD OHLCV loader with on-disk Parquet cache.

The cache lives under ``~/.saadhana/data/eod/`` (per CLAUDE.md `.gitignore`)
and is keyed by ``<SYMBOL>.parquet``. The scanner is the only writer; UI
code never calls yfinance (Vercel 10s timeout, see CLAUDE.md gotchas).

Symbols are passed in NSE convention (e.g. ``RELIANCE``); the loader
appends ``.NS`` for yfinance and stores the canonical NSE symbol on disk.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd

OHLCV_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "volume")
"""Canonical column order. All loaders, fixtures and indicators agree on this."""

DEFAULT_CACHE_ROOT = Path.home() / ".saadhana" / "data" / "eod"
"""Where Parquet caches live. Override with ``SAADHANA_CACHE_ROOT`` env var."""


def cache_root() -> Path:
    """Return the cache root, honoring ``SAADHANA_CACHE_ROOT`` if set."""
    override = os.environ.get("SAADHANA_CACHE_ROOT")
    return Path(override) if override else DEFAULT_CACHE_ROOT


def cache_path(symbol: str) -> Path:
    """Per-symbol cache path. Symbol is NSE convention, e.g. ``RELIANCE``."""
    return cache_root() / f"{symbol.upper()}.parquet"


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case columns, keep only OHLCV, sort by date, drop dupes.

    Handles the MultiIndex column layout that yfinance ≥ 0.2.40 returns
    even for single-ticker downloads (``[(field, ticker), ...]``) by
    flattening to the field level before renaming.
    """
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    if "adj close" in df.columns and "close" not in df.columns:
        df["close"] = df["adj close"]
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV loader missing columns: {missing}")
    df = df[list(OHLCV_COLUMNS)]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def save_to_cache(symbol: str, df: pd.DataFrame) -> Path:
    """Write a normalized OHLCV DataFrame to the per-symbol Parquet cache."""
    path = cache_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    _normalize(df).to_parquet(path, engine="pyarrow", compression="snappy")
    return path


def load_from_cache(symbol: str) -> pd.DataFrame | None:
    """Return cached OHLCV for ``symbol`` or ``None`` if no cache exists."""
    path = cache_path(symbol)
    if not path.exists():
        return None
    return _normalize(pd.read_parquet(path, engine="pyarrow"))


def load_eod(
    symbol: str,
    start: str | date | datetime | None = None,
    end: str | date | datetime | None = None,
    *,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """Load EOD OHLCV for ``symbol`` (NSE convention).

    Order of operations:
      1. If ``refresh`` is False and cache exists, return cache slice.
      2. Otherwise pull from yfinance (``<symbol>.NS``), normalize, save.

    The yfinance import is deferred so unit tests can hit the cache path
    without a live network call. Forensics replay (§11) sets
    ``use_cache=True, refresh=False`` and only ever reads the frozen cache.
    """
    if use_cache and not refresh:
        cached = load_from_cache(symbol)
        if cached is not None:
            return _slice(cached, start, end)

    import yfinance as yf

    yticker = f"{symbol.upper()}.NS"
    df = yf.download(
        yticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {yticker}")
    df = _normalize(df)
    if use_cache:
        save_to_cache(symbol, df)
    return _slice(df, start, end)


def _slice(
    df: pd.DataFrame,
    start: str | date | datetime | None,
    end: str | date | datetime | None,
) -> pd.DataFrame:
    if start is None and end is None:
        return df
    s = pd.to_datetime(start) if start is not None else df.index.min()
    e = pd.to_datetime(end) if end is not None else df.index.max()
    return df.loc[(df.index >= s) & (df.index <= e)].copy()
