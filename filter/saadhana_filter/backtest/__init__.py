"""§11 — backtest validator (Phases G1 / G2).

The backtest replays the §5 v2 system day-by-day under strict
forward-only data discipline (no lookahead) and tracks every BUY
signal through to outcome resolution per §8. Phase G1 runs the
**technical-only** subsystem: spec §5 conditions, §10 standard 0.5%
sizing, no catalyst weight, no conviction-tier escalation. Phase G2
adds the §13/§14 layers and is the official capital-deployment gate.

Modules:
- ``replay``   — day-by-day simulator with point-in-time slicing
- ``metrics``  — §11 aggregator (hit rate, days-to-T1, Sharpe, etc.)
- ``report``   — markdown generator for ``spec/samples/backtest_report_*.md``
"""

from saadhana_filter.backtest.metrics import BacktestMetrics, compute_metrics
from saadhana_filter.backtest.replay import (
    BacktestConfig,
    BacktestResult,
    SimulatedTrade,
    run_backtest,
)
from saadhana_filter.backtest.report import render_markdown_report

__all__ = [
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestResult",
    "SimulatedTrade",
    "compute_metrics",
    "render_markdown_report",
    "run_backtest",
]
