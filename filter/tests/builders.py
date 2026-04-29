"""Inline OHLCV builders for targeted condition tests.

The conftest fixtures cover regime-level smoke tests; these helpers let
each condition test express the *exact* shape it needs (e.g., a 14-bar
window with RSI sitting at 60.5, or a 30-bar tight base ending in a
breakout candle) without contorting a multi-purpose fixture.

Every builder returns a frame with columns ``open, high, low, close,
volume`` and a business-day ``DatetimeIndex`` ending on
``end="2026-04-29"`` by default — matching the spec's locked date so
test failures cite a stable timeline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_END = "2026-04-29"


def make_ohlcv(
    close: np.ndarray | list[float],
    *,
    end: str = DEFAULT_END,
    intrabar_pct: float | np.ndarray = 0.010,
    volume: np.ndarray | list[float] | float = 1_000_000.0,
    open_override: np.ndarray | None = None,
) -> pd.DataFrame:
    """Build an OHLCV DataFrame from a close path.

    - Open is yesterday's close (gapless), unless ``open_override`` is given.
    - Intrabar range expands symmetrically about the open–close midpoint.
    - Volume can be a scalar (broadcast) or an array of the same length.
    """
    close = np.asarray(close, dtype=float)
    n = len(close)
    idx = pd.bdate_range(end=end, periods=n)

    if open_override is not None:
        open_ = np.asarray(open_override, dtype=float)
    else:
        open_ = np.empty(n)
        open_[0] = close[0] * 0.999
        open_[1:] = close[:-1]

    if np.isscalar(intrabar_pct):
        intrabar = np.full(n, float(intrabar_pct))
    else:
        intrabar = np.asarray(intrabar_pct, dtype=float)

    half = (intrabar * close) / 2.0
    high = np.maximum.reduce([np.maximum(open_, close) + half, open_, close])
    low = np.minimum.reduce([np.minimum(open_, close) - half, open_, close])

    if np.isscalar(volume):
        vol_arr = np.full(n, float(volume))
    else:
        vol_arr = np.asarray(volume, dtype=float)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": vol_arr.astype("int64"),
        },
        index=idx,
    )


def linear_close(start: float, end: float, n: int) -> np.ndarray:
    """``n`` linearly-spaced closes from ``start`` to ``end`` (inclusive)."""
    return np.linspace(start, end, n)


def geometric_close(start: float, daily_pct: float, n: int) -> np.ndarray:
    """Geometric path: ``close[t] = start × (1 + daily_pct)**t``."""
    return start * np.power(1.0 + daily_pct, np.arange(n))


def flat_close(level: float, n: int, *, jitter_pct: float = 0.0, seed: int = 0) -> np.ndarray:
    """Flat path with optional deterministic jitter."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, jitter_pct, size=n) if jitter_pct > 0 else np.zeros(n)
    return level * (1.0 + noise)
