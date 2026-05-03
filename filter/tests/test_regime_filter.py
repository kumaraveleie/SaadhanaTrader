"""Tests for the Class 6 regime filter wrapper (quality/regime_filter.py).

Tests use mocked market_regime series to avoid dependence on the
local OHLCV cache; the universe-fallback path is covered separately
by an integration-style test that's marked skipif when the proxy
data is unavailable.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from saadhana_filter.quality import regime_filter as rf


def _mock_regime_series() -> pd.Series:
    """A simple regime series spanning Jan-Mar 2025."""
    return pd.Series(
        ["Risk_On"] * 5 + ["Caution"] * 5 + ["Risk_Off"] * 5 + ["Risk_On"] * 5,
        index=pd.date_range("2025-01-01", periods=20, freq="B"),
    )


@pytest.fixture(autouse=True)
def _reset_cache():
    """Each test starts with a clean cache; restore after."""
    rf.reset_regime_cache()
    yield
    rf.reset_regime_cache()


def test_regime_qualified_default_allowed_set():
    """Default allowed = (Risk_On, Caution). Risk_Off should NOT
    qualify; everything else should."""
    series = _mock_regime_series()
    with patch.object(rf, "_get_regime_series", return_value=series):
        # Risk_On day
        assert rf.regime_qualified(pd.Timestamp("2025-01-01")) is True
        # Caution day
        assert rf.regime_qualified(pd.Timestamp("2025-01-08")) is True
        # Risk_Off day
        assert rf.regime_qualified(pd.Timestamp("2025-01-15")) is False


def test_regime_qualified_strict_risk_on_only():
    """When allowed_regimes=('Risk_On',), Caution should NOT qualify."""
    series = _mock_regime_series()
    with patch.object(rf, "_get_regime_series", return_value=series):
        assert rf.regime_qualified(
            pd.Timestamp("2025-01-01"), allowed_regimes=("Risk_On",)
        ) is True
        assert rf.regime_qualified(
            pd.Timestamp("2025-01-08"), allowed_regimes=("Risk_On",)
        ) is False
        assert rf.regime_qualified(
            pd.Timestamp("2025-01-15"), allowed_regimes=("Risk_On",)
        ) is False


def test_regime_qualified_fail_open_when_cache_empty():
    """When no Nifty proxy is available, the wrapper fails OPEN
    (returns True) — better to take a TC signal without a regime
    gate than to mistakenly halt everything on a data outage."""
    with patch.object(rf, "_get_regime_series", return_value=pd.Series(dtype=str)):
        assert rf.regime_qualified(pd.Timestamp("2025-01-01")) is True


def test_regime_qualified_uses_prior_bar_on_off_calendar_dates():
    """Saturday → use Friday's regime (sticky on weekends)."""
    series = _mock_regime_series()
    # 2025-01-04 is a Saturday; Friday 2025-01-03 is a Risk_On bar.
    with patch.object(rf, "_get_regime_series", return_value=series):
        assert rf.regime_qualified(pd.Timestamp("2025-01-04")) is True


def test_regime_qualified_past_last_bar_uses_last_regime():
    """Date past the proxy's last bar — use the most recent regime."""
    series = _mock_regime_series()
    with patch.object(rf, "_get_regime_series", return_value=series):
        # Last bar is Risk_On at 2025-01-28 (assuming default freq=B).
        # Way past last bar — should still resolve to Risk_On.
        assert rf.regime_qualified(pd.Timestamp("2030-01-01")) is True


def test_get_regime_returns_label_or_none():
    series = _mock_regime_series()
    with patch.object(rf, "_get_regime_series", return_value=series):
        assert rf.get_regime(pd.Timestamp("2025-01-01")) == "Risk_On"
        assert rf.get_regime(pd.Timestamp("2025-01-08")) == "Caution"
        assert rf.get_regime(pd.Timestamp("2025-01-15")) == "Risk_Off"

    with patch.object(rf, "_get_regime_series", return_value=pd.Series(dtype=str)):
        assert rf.get_regime(pd.Timestamp("2025-01-01")) is None


def test_default_allowed_regimes_constant():
    """The default allowed-regime tuple matches the spec —
    Risk_On + Caution. Risk_Off is the cohort-halt state."""
    assert "Risk_On" in rf.DEFAULT_ALLOWED_REGIMES
    assert "Caution" in rf.DEFAULT_ALLOWED_REGIMES
    assert "Risk_Off" not in rf.DEFAULT_ALLOWED_REGIMES


def test_reset_regime_cache_clears_global():
    """After a forced cache build, reset_regime_cache() should clear
    the global so the next call rebuilds."""
    series = _mock_regime_series()
    with patch.object(rf, "_load_nifty_proxy") as mock_load:
        mock_load.return_value = pd.DataFrame(
            {"close": pd.Series(range(200, 250), index=series.index.append(
                pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=30, freq="B")
            ))}
        )
        rf._get_regime_series()
        assert rf._REGIME_CACHE is not None
        rf.reset_regime_cache()
        assert rf._REGIME_CACHE is None
