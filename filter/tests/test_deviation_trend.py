"""Tests for Sec.5.9 — Deviation Trend (faithful BigBeluga port).

Covers the 7 spec golden-fixture cases. Fixtures are synthesised
deterministically inside the tests; no I/O dependency.

Note on minimum-history budget: ATR(200) + percentile_window(500) +
slope_lag(5) means we need 506+ bars to produce any signal at all.
Most fixtures are 700 bars long.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from saadhana_filter.indicators.deviation_trend import compute_deviation_trend


def _ohlcv_from_close(close: np.ndarray) -> pd.DataFrame:
    """Wrap a close path with proportional ±0.5% high/low offsets so
    the ATR(200) computation has a non-zero true range to chew on."""
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


# ───────────────────────────────────────────────────────────────────
# 1. Insufficient history
# ───────────────────────────────────────────────────────────────────
def test_insufficient_history_returns_reason() -> None:
    df = _ohlcv_from_close(np.linspace(100.0, 130.0, 400))  # < 506
    result = compute_deviation_trend(df, on_bar=399)
    assert result["qualified"] is False
    assert result["reason"] == "insufficient_history"


# ───────────────────────────────────────────────────────────────────
# 2. Up → down → up structure produces a bullish flip in the 2nd up
#    Rationale: a single linear bear phase keeps slope_5 constant, so
#    slope_max ≡ slope_5 and slope_norm ≡ +1 throughout — no
#    crossover-from-below is ever observable. We need slope_5 to
#    visit BOTH signs during warmup so slope_norm sits below +0.1
#    before the bullish move (faithful Pine 'crossover' contract).
# ───────────────────────────────────────────────────────────────────
def test_bear_to_bull_transition_produces_bullish_flip() -> None:
    flat = np.full(50, 100.0)
    up1 = np.linspace(100.0, 110.0, 200)
    down = np.linspace(110.0, 90.0, 350)
    up2 = np.linspace(90.0, 140.0, 200)
    close = np.concatenate([flat, up1, down, up2])  # 800 bars
    df = _ohlcv_from_close(close)

    found = False
    for bar in range(605, len(df)):
        result = compute_deviation_trend(df, on_bar=bar, signal_freshness_bars=200)
        if result["qualified"] and result["direction"] == +1:
            found = True
            break
    assert found, "expected bullish flip during the second up phase"


# ───────────────────────────────────────────────────────────────────
# 3. Hysteresis — bullish trend holds through a small dip
# ───────────────────────────────────────────────────────────────────
def test_hysteresis_holds_through_small_dip() -> None:
    """After a bullish flip, slope_norm dipping into [-0.1, +0.1]
    must NOT flip to bearish — the algorithm requires a full
    crossunder of -slope_threshold to flip back. Same up→down→up
    warmup structure as the previous test, then a flat plateau."""
    flat = np.full(50, 100.0)
    up1 = np.linspace(100.0, 110.0, 200)
    down = np.linspace(110.0, 90.0, 350)
    up2 = np.linspace(90.0, 130.0, 100)
    plateau = np.full(100, 130.0)
    close = np.concatenate([flat, up1, down, up2, plateau])  # 800 bars
    df = _ohlcv_from_close(close)

    result = compute_deviation_trend(df, on_bar=len(df) - 1)
    assert result["direction"] == +1


# ───────────────────────────────────────────────────────────────────
# 4. Sustained downtrend never produces qualified=True
# ───────────────────────────────────────────────────────────────────
def test_sustained_downtrend_never_qualifies() -> None:
    close = np.linspace(140.0, 100.0, 700)
    df = _ohlcv_from_close(close)
    qualified_count = 0
    for bar in range(550, len(df), 25):
        result = compute_deviation_trend(df, on_bar=bar)
        if result["qualified"]:
            qualified_count += 1
    assert qualified_count == 0


# ───────────────────────────────────────────────────────────────────
# 5. Band ordering invariant — ATR multipliers stack correctly
# ───────────────────────────────────────────────────────────────────
def test_band_ordering_invariant() -> None:
    df = _ohlcv_from_close(np.linspace(100.0, 140.0, 700))
    r = compute_deviation_trend(df, on_bar=699)
    assert (
        r["lower_3"]
        <= r["lower_2"]
        <= r["lower_1"]
        <= r["avg"]
        <= r["upper_1"]
        <= r["upper_2"]
        <= r["upper_3"]
    )


# ───────────────────────────────────────────────────────────────────
# 6. Determinism — same input twice = identical output
# ───────────────────────────────────────────────────────────────────
def test_determinism() -> None:
    df = _ohlcv_from_close(np.linspace(100.0, 140.0, 700))
    a = compute_deviation_trend(df, on_bar=699)
    b = compute_deviation_trend(df, on_bar=699)
    assert a == b


# ───────────────────────────────────────────────────────────────────
# 7. Perfectly flat series — direction stays 0 (degenerate-flat path)
# ───────────────────────────────────────────────────────────────────
def test_perfectly_flat_series_direction_zero() -> None:
    """slope_5 = 0 everywhere → slope_max = 0 → division NaN →
    trend logic skips → direction stays 0, qualified False."""
    close = np.full(700, 100.0)
    df = _ohlcv_from_close(close)
    result = compute_deviation_trend(df, on_bar=699)
    assert result["direction"] == 0
    assert result["qualified"] is False


# ───────────────────────────────────────────────────────────────────
# Extras — band shape against ATR(200), insufficient history shape
# ───────────────────────────────────────────────────────────────────
def test_band_centerline_equals_sma_50_at_last_bar() -> None:
    """Sanity-check the centerline against its definition at the
    last bar — useful as a quick "is the math wired right" probe."""
    close = np.linspace(100.0, 140.0, 700)
    df = _ohlcv_from_close(close)
    r = compute_deviation_trend(df, on_bar=699)
    # Manual SMA(50) over the last 50 closes.
    expected_avg = float(np.mean(close[-50:]))
    assert abs(r["avg"] - expected_avg) < 1e-9


def test_insufficient_history_payload_is_minimal() -> None:
    """The early-return path on insufficient history must not
    pretend to know band values — checked explicitly so callers
    don't accidentally trust stale fields."""
    df = _ohlcv_from_close(np.linspace(100.0, 130.0, 400))
    r = compute_deviation_trend(df, on_bar=399)
    assert r.get("avg") is None
    assert r.get("atr_value") is None
    assert r.get("upper_1") is None
    assert r.get("lower_1") is None
