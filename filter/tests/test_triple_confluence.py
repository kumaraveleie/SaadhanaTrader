"""Tests for Sec.5.10 — Triple confluence scoring.

Covers the 6 spec golden-fixture cases. Component results are
faked at the boundary (the three component candidate functions
already have their own dedicated test suites — Sec.5.7/5.8/5.9 —
so we don't re-test indicator math here, just the scoring rules).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import numpy as np
import pandas as pd

from saadhana_filter.signals.triple_confluence import (
    candidate_triple_confluence,
)


def _ohlcv(close: np.ndarray) -> pd.DataFrame:
    high = close * 1.005
    low = close * 0.995
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
        }
    )


def _fake_components(
    *,
    ma: dict[str, Any],
    ast: dict[str, Any],
    dev: dict[str, Any],
):
    """Patch the three component callables to return canned dicts."""
    return (
        patch(
            "saadhana_filter.signals.triple_confluence.compute_ma_crossover",
            return_value=ma,
        ),
        patch(
            "saadhana_filter.signals.triple_confluence.compute_adaptive_supertrend",
            return_value=ast,
        ),
        patch(
            "saadhana_filter.signals.triple_confluence.compute_deviation_trend",
            return_value=dev,
        ),
    )


def _enter_all(patches):
    [p.__enter__() for p in patches]


def _exit_all(patches):
    [p.__exit__(None, None, None) for p in patches]


# ──────────────────────────────────────────────────────────────────
# 1. 3-of-3 high conviction
# ──────────────────────────────────────────────────────────────────
def test_three_of_three_yields_high_conviction() -> None:
    df = _ohlcv(np.linspace(100.0, 130.0, 200))
    patches = _fake_components(
        ma={"qualified": True, "fast_ma": 121.0, "slow_ma": 115.0, "ma_type": "TEMA"},
        ast={"qualified": True, "direction": +1, "active_cluster": "mid"},
        dev={"qualified": True, "direction": +1, "slope": 0.5},
    )
    _enter_all(patches)
    try:
        result = candidate_triple_confluence(df, on_bar=199)
    finally:
        _exit_all(patches)

    assert result["qualified"] is True
    assert result["conviction"] == "high"
    assert result["score"] == 3
    assert set(result["agreeing_components"]) == {
        "ma_crossover",
        "adaptive_st",
        "deviation_trend",
    }
    assert result["bearish_components"] == []


# ──────────────────────────────────────────────────────────────────
# 2. 2-of-3 medium conviction (slope filter rejects deviation_trend)
# ──────────────────────────────────────────────────────────────────
def test_two_of_three_yields_medium_conviction() -> None:
    df = _ohlcv(np.linspace(100.0, 130.0, 200))
    patches = _fake_components(
        ma={"qualified": True, "fast_ma": 121.0, "slow_ma": 115.0, "ma_type": "TEMA"},
        ast={"qualified": True, "direction": +1, "active_cluster": "mid"},
        dev={"qualified": False, "direction": +1, "slope": -0.1},  # slope filter rejected
    )
    _enter_all(patches)
    try:
        result = candidate_triple_confluence(df, on_bar=199)
    finally:
        _exit_all(patches)

    assert result["qualified"] is True
    assert result["conviction"] == "medium"
    assert result["score"] == 2
    assert set(result["agreeing_components"]) == {"ma_crossover", "adaptive_st"}


# ──────────────────────────────────────────────────────────────────
# 3. 1-of-3 — not a candidate
# ──────────────────────────────────────────────────────────────────
def test_one_of_three_is_not_qualified() -> None:
    df = _ohlcv(np.linspace(100.0, 130.0, 200))
    patches = _fake_components(
        ma={"qualified": True, "ma_type": "TEMA"},
        ast={"qualified": False, "direction": +1, "active_cluster": "mid"},
        dev={"qualified": False, "direction": +1, "slope": 0.0},
    )
    _enter_all(patches)
    try:
        result = candidate_triple_confluence(df, on_bar=199)
    finally:
        _exit_all(patches)

    assert result["qualified"] is False
    assert result["conviction"] == "none"
    assert result["score"] == 1


# ──────────────────────────────────────────────────────────────────
# 4. Mixed direction — bearish votes go to metadata, NOT the count
# ──────────────────────────────────────────────────────────────────
def test_mixed_direction_records_bearish_in_metadata_only() -> None:
    df = _ohlcv(np.linspace(100.0, 130.0, 200))
    patches = _fake_components(
        ma={"qualified": True, "ma_type": "TEMA"},
        ast={"qualified": True, "direction": +1, "active_cluster": "mid"},
        dev={"qualified": False, "direction": -1, "slope": -0.5},  # bearish vote
    )
    _enter_all(patches)
    try:
        result = candidate_triple_confluence(df, on_bar=199)
    finally:
        _exit_all(patches)

    assert result["score"] == 2
    assert result["conviction"] == "medium"
    assert "deviation_trend" in result["bearish_components"]
    assert "deviation_trend" not in result["agreeing_components"]


# ──────────────────────────────────────────────────────────────────
# 5. Component init shortfall caps the score at 2
# ──────────────────────────────────────────────────────────────────
def test_init_shortfall_caps_score() -> None:
    """Spec edge case: 'one component fails initialisation → score
    capped at 2 (3-of-3 impossible)'. We model this by returning
    qualified=False with an insufficient_history reason from one
    component while the other two are qualified bullish."""
    df = _ohlcv(np.linspace(100.0, 130.0, 200))
    patches = _fake_components(
        ma={"qualified": True, "ma_type": "TEMA"},
        ast={
            "qualified": False,
            "direction": 0,
            "active_cluster": "init",
            "reason": "insufficient_history",
        },
        dev={"qualified": True, "direction": +1, "slope": 0.5},
    )
    _enter_all(patches)
    try:
        result = candidate_triple_confluence(df, on_bar=199)
    finally:
        _exit_all(patches)

    assert result["score"] == 2
    assert result["conviction"] == "medium"
    assert "adaptive_st" not in result["agreeing_components"]
    # Init shortfall is NOT bearish — direction=0 must not appear
    # in bearish_components either.
    assert "adaptive_st" not in result["bearish_components"]


# ──────────────────────────────────────────────────────────────────
# 6. Determinism — same fixture twice (no mocks) = identical output
# ──────────────────────────────────────────────────────────────────
def test_determinism_no_mocks() -> None:
    rng = np.random.default_rng(20260502)
    drift = 0.4
    n = 200
    base = 100.0 * np.cumprod(1 + drift / 100 + rng.normal(0, 0.005, size=n))
    df = _ohlcv(base)

    a = candidate_triple_confluence(df, on_bar=199)
    b = candidate_triple_confluence(df, on_bar=199)
    # The component dicts themselves must be equal — float equality
    # is fine here because the math is deterministic.
    assert a["score"] == b["score"]
    assert a["conviction"] == b["conviction"]
    assert a["agreeing_components"] == b["agreeing_components"]


# ──────────────────────────────────────────────────────────────────
# 7. End-to-end sanity (no mocks) on a strong uptrend ramp
# ──────────────────────────────────────────────────────────────────
def test_end_to_end_uptrend_does_not_crash() -> None:
    """Run the full TC pipeline on real component math for a strong
    uptrend. Bar count chosen to clear deviation_trend's 506-bar
    minimum (atr_length=200, percentile_window=500, slope_lag=5).
    We don't assert a specific score — only that the scoring layer
    survives the end-to-end call without exceptions."""
    rng = np.random.default_rng(20260502)
    drift = 0.5
    n = 700
    base = 100.0 * np.cumprod(1 + drift / 100 + rng.normal(0, 0.005, size=n))
    df = _ohlcv(base)
    result = candidate_triple_confluence(df, on_bar=n - 1)
    assert result["score"] in (0, 1, 2, 3)
    assert result["conviction"] in ("none", "medium", "high")
    # All three component sub-dicts are present.
    assert "ma_crossover" in result
    assert "adaptive_st" in result
    assert "deviation_trend" in result
