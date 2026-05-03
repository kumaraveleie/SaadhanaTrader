"""Class 6 regime filter — Path δ wrapper around §12 market_regime.

Per §0.7.5 information-orthogonality, Class 6 (market regime) is
orthogonal to Class 1 (price-pattern technicals — TC components,
Pro-setup conditions) and Class 5 (cross-symbol — sector breadth).
This module wraps the existing ``signals.regime.market_regime`` so
cohort candidate functions can call ``regime_qualified()`` to gate
new entries on the broad-market state.

The wrapper auto-loads the Nifty index OHLCV (``^NSEI`` from local
yfinance cache); when the cache misses it falls back to a
universe-mean proxy (top-50 InvestQuest names by mcap), the same
fallback used in scripts/bull_month_replay.py and
scripts/orthogonality_budget_diagnostic.py.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from saadhana_filter.data.loader import load_eod
from saadhana_filter.data.universe import load_universe
from saadhana_filter.signals.regime import Regime, market_regime

DEFAULT_ALLOWED_REGIMES: tuple[str, ...] = ("Risk_On", "Caution")


def _load_nifty_proxy() -> pd.DataFrame:
    """Return a Nifty-shaped OHLCV DataFrame from local cache.

    Tries ``^NSEI`` / ``NIFTY`` / ``NIFTY50`` first; falls back to a
    universe-mean proxy when no Nifty index is cached. The proxy
    normalises each top-50-by-mcap symbol to a 100-base before
    averaging, so the resulting close path tracks broad-market drift
    even though it isn't the real Nifty.
    """
    for ticker in ("^NSEI", "NIFTY", "NIFTY50"):
        try:
            df = load_eod(ticker)
        except Exception:  # noqa: BLE001
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df

    # Fallback — universe-mean proxy.
    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))
    closes: list[pd.Series] = []
    for sym in list(universe.head(50).index):
        try:
            df = load_eod(sym)
        except Exception:  # noqa: BLE001
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if "close" not in df.columns or len(df) < 200:
            continue
        norm = df["close"] / df["close"].iloc[0] * 100.0
        closes.append(norm.rename(sym))
    if not closes:
        return pd.DataFrame()
    proxy_close = pd.concat(closes, axis=1, sort=True).mean(axis=1)
    return pd.DataFrame({"close": proxy_close.dropna()})


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────
_REGIME_CACHE: pd.Series | None = None


def _get_regime_series() -> pd.Series:
    """Cached per-process market_regime series. Built lazily on first
    call; subsequent ``regime_qualified()`` lookups are O(log n)."""
    global _REGIME_CACHE
    if _REGIME_CACHE is None:
        nifty_df = _load_nifty_proxy()
        if nifty_df.empty:
            _REGIME_CACHE = pd.Series(dtype=str)
        else:
            _REGIME_CACHE = market_regime(nifty_df)
    return _REGIME_CACHE


def reset_regime_cache() -> None:
    """Clear the cached regime series — used by tests that inject a
    different proxy or that need a deterministic fresh build."""
    global _REGIME_CACHE
    _REGIME_CACHE = None


def _normalise_dt(ts: pd.Timestamp, series: pd.Series) -> pd.Timestamp:
    """Coerce ``ts`` to the same datetime unit as the series index so
    ``searchsorted`` doesn't trip on lossy unit conversions."""
    if isinstance(series.index, pd.DatetimeIndex):
        ts = pd.Timestamp(ts).tz_localize(None).normalize()
        try:
            return ts.as_unit(series.index.unit)
        except Exception:  # noqa: BLE001 — older pandas / non-DatetimeIndex
            return ts
    return ts


def regime_qualified(
    as_of_date: pd.Timestamp,
    *,
    allowed_regimes: tuple[str, ...] | list[str] = DEFAULT_ALLOWED_REGIMES,
) -> bool:
    """Return True if the market regime at ``as_of_date`` is in the
    allowed-regime set.

    Default allowed regimes: Risk_On + Caution. Pass
    ``allowed_regimes=("Risk_On",)`` for the strict variant that
    halts entries during Caution as well as Risk_Off.

    When the regime cache is empty (no Nifty proxy available),
    returns ``True`` (fail-open) — better to take a TC + Sector
    Pulse signal without a regime gate than to mistakenly halt all
    entries due to a data outage.
    """
    series = _get_regime_series()
    if series.empty:
        return True
    ts = _normalise_dt(as_of_date, series)
    idx = series.index.searchsorted(ts)
    if idx >= len(series):
        idx = len(series) - 1
    elif series.index[idx] != ts:
        idx = max(0, idx - 1)
    regime_at = str(series.iloc[idx])
    return regime_at in allowed_regimes


def get_regime(as_of_date: pd.Timestamp) -> str | None:
    """Read-only: return the regime label at ``as_of_date``. Useful
    for forensics + reporting (Sec.0.7.5 Layer 6 audit). Returns
    ``None`` when the proxy is unavailable."""
    series = _get_regime_series()
    if series.empty:
        return None
    ts = _normalise_dt(as_of_date, series)
    idx = series.index.searchsorted(ts)
    if idx >= len(series):
        idx = len(series) - 1
    elif series.index[idx] != ts:
        idx = max(0, idx - 1)
    return str(series.iloc[idx])


__all__ = [
    "DEFAULT_ALLOWED_REGIMES",
    "Regime",
    "regime_qualified",
    "get_regime",
    "reset_regime_cache",
]
