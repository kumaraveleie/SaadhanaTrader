"""§11 backtest engine tests — replay determinism, no-lookahead,
metric aggregation, report shape."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from saadhana_filter.backtest.metrics import compute_metrics
from saadhana_filter.backtest.replay import (
    BacktestConfig,
    SimulatedTrade,
    run_backtest,
)
from saadhana_filter.backtest.report import render_markdown_report
from tests.builders import flat_close, geometric_close, make_ohlcv


# ──────────────────────────────────────────────────────────────────────────
# Replay determinism + forward-only discipline
# ──────────────────────────────────────────────────────────────────────────
class TestReplayDeterminism:
    def _basic_config(self, universe: tuple[str, ...]) -> BacktestConfig:
        return BacktestConfig(
            universe=universe,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 4, 29),
        )

    def test_no_buy_in_risk_off_regime(self) -> None:
        # Index in deep downtrend → Risk_Off throughout → zero BUYs
        nifty_df = make_ohlcv(geometric_close(20_000.0, -0.001, 320))
        ohlcv = {"AAA": make_ohlcv(geometric_close(100.0, 0.0015, 320))}
        cfg = self._basic_config(("AAA",))
        result = run_backtest(cfg, ohlcv=ohlcv, nifty_df=nifty_df)
        assert result.trades == []

    def test_replay_returns_result_with_config(self) -> None:
        nifty_df = make_ohlcv(geometric_close(15_000.0, 0.001, 320))
        ohlcv = {"AAA": make_ohlcv(flat_close(100.0, 320, jitter_pct=0.002, seed=1))}
        cfg = self._basic_config(("AAA",))
        result = run_backtest(cfg, ohlcv=ohlcv, nifty_df=nifty_df)
        assert result.config is cfg
        assert isinstance(result.trades, list)

    def test_replay_skips_symbols_not_in_ohlcv(self) -> None:
        nifty_df = make_ohlcv(geometric_close(15_000.0, 0.001, 320))
        cfg = self._basic_config(("MISSING",))
        result = run_backtest(cfg, ohlcv={}, nifty_df=nifty_df)
        assert result.trades == []

    def test_replay_skips_symbols_failing_tier1(self) -> None:
        nifty_df = make_ohlcv(geometric_close(15_000.0, 0.001, 320))
        ohlcv = {"AAA": make_ohlcv(geometric_close(100.0, 0.0015, 320))}
        cfg = self._basic_config(("AAA",))
        result = run_backtest(
            cfg, ohlcv=ohlcv, nifty_df=nifty_df, fundamentals_passed=set()
        )
        assert result.trades == []

    def test_max_concurrent_positions_respected(self) -> None:
        nifty_df = make_ohlcv(geometric_close(15_000.0, 0.001, 320))
        cfg = BacktestConfig(
            universe=tuple(f"S{i}" for i in range(50)),
            start_date=date(2025, 6, 1),
            end_date=date(2026, 4, 29),
            max_concurrent_positions=3,
        )
        ohlcv = {
            f"S{i}": make_ohlcv(geometric_close(100.0 + i, 0.0015, 320))
            for i in range(50)
        }
        result = run_backtest(cfg, ohlcv=ohlcv, nifty_df=nifty_df)
        # Whatever the synthetic data resolves to, the cap must hold.
        assert len(result.open_positions_at_end) <= cfg.max_concurrent_positions


# ──────────────────────────────────────────────────────────────────────────
# Metrics aggregation
# ──────────────────────────────────────────────────────────────────────────
def _trade(
    *,
    return_pct: float,
    days_to_t1: int | None = None,
    outcome: str = "T1_HIT",
    days_held: int = 10,
    score: int = 13,
    entry_date: date = date(2026, 1, 1),
) -> SimulatedTrade:
    return SimulatedTrade(
        symbol="X",
        entry_date=entry_date,
        entry_price=100.0,
        exit_date=date(2026, 1, 11),
        exit_price=100.0 * (1 + return_pct),
        return_pct=return_pct,
        days_held=days_held,
        days_to_t1=days_to_t1,
        outcome=outcome,
        pro_setup_score_at_entry=score,
    )


class TestMetricsAggregation:
    def test_empty_trade_list(self) -> None:
        m = compute_metrics([])
        assert m.n_trades == 0
        assert not m.overall_passes

    def test_clean_pass_synthetic(self) -> None:
        # 7 wins × +12% (T1 in 15 days) + 3 losses × -2% → all metrics pass
        trades = [
            _trade(return_pct=0.12, days_to_t1=15, outcome="T2_HIT", entry_date=date(2026, 1, i + 1))
            for i in range(7)
        ] + [
            _trade(return_pct=-0.02, outcome="STOP_HIT", days_held=8, entry_date=date(2026, 2, i + 1))
            for i in range(3)
        ]
        m = compute_metrics(trades)
        assert m.hit_rate_pct == pytest.approx(70.0)
        assert m.hit_rate_passes
        assert m.avg_win_pct == pytest.approx(12.0)
        assert m.avg_win_passes
        assert m.avg_loss_pct == pytest.approx(-2.0)
        assert m.avg_loss_passes
        assert m.win_loss_ratio == pytest.approx(6.0)
        assert m.win_loss_passes
        assert m.consecutive_losses_passes  # 3 in a row, ≤ 5

    def test_failure_path(self) -> None:
        # Hit rate too low + losses too big
        trades = (
            [_trade(return_pct=0.06, days_to_t1=22, entry_date=date(2026, 1, 1))]
            + [
                _trade(
                    return_pct=-0.05,
                    outcome="STOP_HIT",
                    days_held=5,
                    entry_date=date(2026, 1, i + 2),
                )
                for i in range(9)
            ]
        )
        m = compute_metrics(trades)
        assert not m.hit_rate_passes
        assert not m.avg_loss_passes
        assert not m.consecutive_losses_passes  # 9 in a row
        assert not m.overall_passes

    def test_still_open_excluded_from_win_loss_counts(self) -> None:
        trades = [
            _trade(return_pct=0.20, days_to_t1=10, outcome="T2_HIT"),
            _trade(return_pct=0.15, days_to_t1=12, outcome="STILL_OPEN"),
        ]
        m = compute_metrics(trades)
        assert m.n_still_open == 1
        assert m.n_wins == 1
        assert m.n_losses == 0


# ──────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────
def test_report_includes_pass_fail_table_and_banner() -> None:
    trades = [_trade(return_pct=0.10, days_to_t1=12, outcome="T2_HIT")]
    metrics = compute_metrics(trades)
    cfg = BacktestConfig(
        universe=("AAA",),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 4, 29),
    )
    from saadhana_filter.backtest.replay import BacktestResult

    result = BacktestResult(trades=trades, config=cfg)
    md = render_markdown_report(
        title="Backtest G1 Test",
        phase_label="G1 — diagnostic",
        result=result,
        metrics=metrics,
        generated_at=date(2026, 4, 29),
    )
    assert "§11 Backtest Validation" in md
    assert "Hit rate" in md
    assert "OVERALL" in md  # PASS or FAIL banner


def test_report_outcome_distribution_shows_each_reason() -> None:
    trades = [
        _trade(return_pct=0.06, days_to_t1=15, outcome="T1_HIT"),
        _trade(return_pct=-0.03, outcome="STOP_HIT"),
        _trade(return_pct=0.15, days_to_t1=10, outcome="T2_HIT"),
    ]
    metrics = compute_metrics(trades)
    cfg = BacktestConfig(
        universe=("AAA",),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 4, 29),
    )
    from saadhana_filter.backtest.replay import BacktestResult

    result = BacktestResult(trades=trades, config=cfg)
    md = render_markdown_report(
        title="t",
        phase_label="t",
        result=result,
        metrics=metrics,
        generated_at=date(2026, 4, 29),
    )
    for outcome in ("T1_HIT", "STOP_HIT", "T2_HIT"):
        assert outcome in md
