"""§5 — pro_setup_score aggregator + integration smoke tests.

The per-condition tests in ``test_conditions.py`` cover the rules in
isolation. This module asserts the aggregator's column shape, score
bounds, and *directional* behavior across the regime fixtures from
``conftest.py``: an uptrend should score visibly higher than a
sideways/downtrend on the recent tail.
"""

from __future__ import annotations

import numpy as np

from saadhana_filter.indicators.conditions import ALL_CONDITIONS, pro_setup_score
from tests.builders import geometric_close, make_ohlcv


def test_score_columns_match_all_conditions() -> None:
    df = make_ohlcv(geometric_close(100.0, 0.002, 280))
    out = pro_setup_score(df)
    expected = {name for name, _ in ALL_CONDITIONS} | {"score"}
    assert set(out.columns) == expected


def test_score_in_zero_to_thirteen_range() -> None:
    df = make_ohlcv(geometric_close(100.0, 0.002, 280))
    out = pro_setup_score(df)
    assert out["score"].min() >= 0
    assert out["score"].max() <= 13


def test_uptrend_scores_higher_than_downtrend(uptrend_fixture, downtrend_fixture) -> None:
    up = pro_setup_score(uptrend_fixture)["score"].iloc[-1]
    down = pro_setup_score(downtrend_fixture)["score"].iloc[-1]
    assert up > down
    # And the gap is meaningful — at least 3 conditions of separation
    assert (up - down) >= 3


def test_uptrend_passes_trend_block(uptrend_fixture) -> None:
    out = pro_setup_score(uptrend_fixture).iloc[-1]
    # All §5.1 trend conditions should fire on a clean uptrend tail
    assert bool(out["stage_2"])
    assert bool(out["above_50_and_200_ema"])
    assert bool(out["5ema_above_20ema_rising"])


def test_downtrend_fails_trend_block(downtrend_fixture) -> None:
    out = pro_setup_score(downtrend_fixture).iloc[-1]
    assert not bool(out["stage_2"])
    assert not bool(out["above_50_and_200_ema"])
    assert not bool(out["5ema_above_20ema_rising"])


def test_breakout_fixture_fires_volume_alive_clauses(breakout_fixture) -> None:
    # The 3-bar breakout candle on heavy volume should activate
    # institutional flow + the BB-width "alive" clause via the breakout
    # exception, even though the prior 30 bars were a tight base.
    out = pro_setup_score(breakout_fixture).iloc[-1]
    assert bool(out["institutional_flow"])
    assert bool(out["bb_width_alive"])


def test_sideways_low_score(sideways_fixture) -> None:
    s = pro_setup_score(sideways_fixture)["score"].iloc[-1]
    # Stage 2 + EMA stack + RSI band + MACD rising should all be off in
    # a flat regime; expect a low score (well below 13).
    assert s <= 7


def test_score_is_int64(uptrend_fixture) -> None:
    out = pro_setup_score(uptrend_fixture)
    assert out["score"].dtype == np.int64
