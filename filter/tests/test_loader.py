"""Tests for saadhana_filter.data.loader — Parquet roundtrip + cache layout.

We never hit yfinance from these tests; ``load_eod`` is exercised on the
cache path only by pre-seeding the cache with ``save_to_cache``. The
yfinance branch is integration-tested separately (Phase M cron).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from saadhana_filter.data.loader import (
    OHLCV_COLUMNS,
    cache_path,
    cache_root,
    load_eod,
    load_from_cache,
    save_to_cache,
)
from tests.builders import geometric_close, make_ohlcv


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the loader's cache root to a per-test ``tmp_path``."""
    monkeypatch.setenv("SAADHANA_CACHE_ROOT", str(tmp_path))
    return tmp_path


def test_cache_root_honors_env(_isolated_cache: Path) -> None:
    assert cache_root() == _isolated_cache


def test_cache_path_uppercases_symbol(_isolated_cache: Path) -> None:
    assert cache_path("reliance").name == "RELIANCE.parquet"


def test_save_then_load_roundtrip(_isolated_cache: Path) -> None:
    df = make_ohlcv(geometric_close(100.0, 0.001, 60))
    out_path = save_to_cache("RELIANCE", df)
    assert out_path.exists()
    loaded = load_from_cache("RELIANCE")
    assert loaded is not None
    pd.testing.assert_frame_equal(loaded, df, check_freq=False)


def test_load_from_cache_missing_returns_none(_isolated_cache: Path) -> None:
    assert load_from_cache("DOES_NOT_EXIST") is None


def test_normalize_lowercases_columns(_isolated_cache: Path) -> None:
    df = make_ohlcv(geometric_close(100.0, 0.001, 30))
    df = df.rename(columns=str.upper)  # simulate yfinance output
    save_to_cache("TEST", df)
    loaded = load_from_cache("TEST")
    assert list(loaded.columns) == list(OHLCV_COLUMNS)


def test_load_eod_uses_cache_when_available(_isolated_cache: Path) -> None:
    df = make_ohlcv(geometric_close(100.0, 0.001, 60))
    save_to_cache("INFY", df)
    out = load_eod("INFY", use_cache=True, refresh=False)
    pd.testing.assert_frame_equal(out, df, check_freq=False)


def test_load_eod_slices_by_date(_isolated_cache: Path) -> None:
    df = make_ohlcv(geometric_close(100.0, 0.001, 60))
    save_to_cache("INFY", df)
    cutoff = df.index[10]
    sliced = load_eod("INFY", start=cutoff, end=df.index[20])
    assert len(sliced) == 11
    assert sliced.index[0] == cutoff


def test_normalize_rejects_missing_columns(_isolated_cache: Path) -> None:
    bad = make_ohlcv(geometric_close(100.0, 0.001, 30)).drop(columns=["close"])
    with pytest.raises(ValueError, match="missing columns"):
        save_to_cache("BAD", bad)


def test_save_dedupes_and_sorts(_isolated_cache: Path) -> None:
    df = make_ohlcv(geometric_close(100.0, 0.001, 30))
    duplicated = pd.concat([df, df.iloc[[5]]])
    save_to_cache("DUPE", duplicated)
    loaded = load_from_cache("DUPE")
    assert loaded.index.is_monotonic_increasing
    assert not loaded.index.has_duplicates


def test_cache_root_default_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAADHANA_CACHE_ROOT", raising=False)
    assert cache_root().name == "eod"
    assert "saadhana" in str(cache_root()).lower()
