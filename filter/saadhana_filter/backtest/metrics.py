"""§11 backtest metrics aggregator.

Takes a list of ``SimulatedTrade``s from the replay engine and
computes the seven §11 must-pass metrics, plus a few diagnostic
extras used by the report generator.

Spec §11 thresholds:

| Metric                       | Target  |
|------------------------------|---------|
| Hit rate (% reaching +5%)    | ≥ 60%   |
| Average days to T1           | ≤ 25    |
| Average win                  | ≥ +8%   |
| Average loss                 | ≤ −2.5% |
| Max consecutive losses       | ≤ 5     |
| Win/loss ratio               | ≥ 2.0   |
| Profit Factor                | ≥ 1.8   |
| Sharpe (annualized)          | ≥ 1.5   |

Profit Factor = Σ(positive returns) / |Σ(negative returns)|. Catches
the case where hit rate is high but a few oversized losers wipe out
many small winners — count-based metrics (hit rate, win/loss ratio)
miss this; PF is magnitude-weighted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from saadhana_filter.backtest.replay import SimulatedTrade

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestMetrics:
    """All §11 metrics + per-pass/fail bools + diagnostic extras."""

    n_trades: int
    n_wins: int
    n_losses: int
    n_still_open: int

    hit_rate_pct: float  # % of trades that touched +5% (T1 hit at least once)
    hit_rate_passes: bool

    avg_days_to_t1: float | None  # None if no trades reached T1
    days_to_t1_passes: bool

    avg_win_pct: float
    avg_win_passes: bool

    avg_loss_pct: float
    avg_loss_passes: bool

    max_consecutive_losses: int
    consecutive_losses_passes: bool

    win_loss_ratio: float
    win_loss_passes: bool

    profit_factor: float  # gross profit / |gross loss| per §11
    profit_factor_passes: bool

    sharpe_annualized: float
    sharpe_passes: bool

    overall_passes: bool

    # Diagnostic extras (not part of §11 thresholds)
    median_return_pct: float
    best_trade_pct: float
    worst_trade_pct: float
    expectancy_pct: float


def _is_win(t: SimulatedTrade) -> bool:
    return t.return_pct > 0 and t.outcome != "STILL_OPEN"


def _is_loss(t: SimulatedTrade) -> bool:
    return t.return_pct <= 0 and t.outcome != "STILL_OPEN"


def _max_consecutive_losses(trades: list[SimulatedTrade]) -> int:
    """Walk trades in entry-date order and count the longest losing run."""
    ordered = sorted(trades, key=lambda t: t.entry_date)
    longest = current = 0
    for t in ordered:
        if t.outcome == "STILL_OPEN":
            continue
        if _is_loss(t):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _annualized_sharpe(trades: list[SimulatedTrade]) -> float:
    """Annualized Sharpe of trade returns scaled by holding period.

    For a swing system with variable holding periods, this approximates
    a daily-Sharpe by spreading each trade's return across its
    days_held and taking sigma / mu of that synthetic daily series.
    """
    closed = [t for t in trades if t.outcome != "STILL_OPEN"]
    if not closed:
        return 0.0
    daily_returns: list[float] = []
    for t in closed:
        if t.days_held > 0:
            daily_returns.extend([t.return_pct / t.days_held] * t.days_held)
    if len(daily_returns) < 2:
        return 0.0
    arr = np.asarray(daily_returns)
    mu = float(arr.mean())
    sd = float(arr.std(ddof=1))
    if sd == 0:
        return 0.0
    return float(mu / sd * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_metrics(trades: list[SimulatedTrade]) -> BacktestMetrics:
    """Compute the full §11 metric suite + diagnostic extras."""
    closed = [t for t in trades if t.outcome != "STILL_OPEN"]
    open_count = len(trades) - len(closed)
    wins = [t for t in closed if _is_win(t)]
    losses = [t for t in closed if _is_loss(t)]

    n_t1_reached = sum(1 for t in closed if t.days_to_t1 is not None)
    hit_rate = (n_t1_reached / len(closed) * 100.0) if closed else 0.0

    days_to_t1_values = [t.days_to_t1 for t in closed if t.days_to_t1 is not None]
    avg_days_to_t1 = float(np.mean(days_to_t1_values)) if days_to_t1_values else None

    avg_win = float(np.mean([t.return_pct for t in wins]) * 100.0) if wins else 0.0
    avg_loss = float(np.mean([t.return_pct for t in losses]) * 100.0) if losses else 0.0

    max_consec_losses = _max_consecutive_losses(closed)

    win_loss = (avg_win / abs(avg_loss)) if losses and avg_loss != 0.0 else float("inf")

    # §11 Profit Factor — magnitude-weighted, not count-weighted
    gross_profit = float(sum(t.return_pct for t in wins))
    gross_loss = float(abs(sum(t.return_pct for t in losses)))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    sharpe = _annualized_sharpe(closed)

    returns = [t.return_pct for t in closed]
    median_return = float(np.median(returns)) * 100.0 if returns else 0.0
    best_trade = float(max(returns)) * 100.0 if returns else 0.0
    worst_trade = float(min(returns)) * 100.0 if returns else 0.0
    win_rate = len(wins) / len(closed) if closed else 0.0
    expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss if closed else 0.0

    # Per-metric pass / fail bools
    hit_rate_passes = hit_rate >= 60.0
    days_to_t1_passes = avg_days_to_t1 is not None and avg_days_to_t1 <= 25.0
    avg_win_passes = avg_win >= 8.0
    avg_loss_passes = avg_loss >= -2.5  # avg_loss is negative; "≤ -2.5%" means abs ≤ 2.5%
    consecutive_losses_passes = max_consec_losses <= 5
    win_loss_passes = win_loss >= 2.0
    profit_factor_passes = profit_factor >= 1.8
    sharpe_passes = sharpe >= 1.5

    overall = all(
        [
            hit_rate_passes,
            days_to_t1_passes,
            avg_win_passes,
            avg_loss_passes,
            consecutive_losses_passes,
            win_loss_passes,
            profit_factor_passes,
            sharpe_passes,
        ]
    )

    return BacktestMetrics(
        n_trades=len(trades),
        n_wins=len(wins),
        n_losses=len(losses),
        n_still_open=open_count,
        hit_rate_pct=hit_rate,
        hit_rate_passes=hit_rate_passes,
        avg_days_to_t1=avg_days_to_t1,
        days_to_t1_passes=days_to_t1_passes,
        avg_win_pct=avg_win,
        avg_win_passes=avg_win_passes,
        avg_loss_pct=avg_loss,
        avg_loss_passes=avg_loss_passes,
        max_consecutive_losses=max_consec_losses,
        consecutive_losses_passes=consecutive_losses_passes,
        win_loss_ratio=win_loss,
        win_loss_passes=win_loss_passes,
        profit_factor=profit_factor,
        profit_factor_passes=profit_factor_passes,
        sharpe_annualized=sharpe,
        sharpe_passes=sharpe_passes,
        overall_passes=overall,
        median_return_pct=median_return,
        best_trade_pct=best_trade,
        worst_trade_pct=worst_trade,
        expectancy_pct=expectancy,
    )


def metrics_to_dict(m: BacktestMetrics) -> dict:
    """Serializer for JSON output / logging."""
    return asdict(m)
