"""§11 backtest replay engine.

Walks the calendar one trading day at a time. On each day we slice
every per-symbol OHLCV frame to ``[<= scan_date]`` so the engine
sees only data that was available at the time. New BUY signals open
positions (using the §5.4 entry stop and §7 ladder); existing
positions are evaluated against §8 SELL triggers. Every closed
position is recorded as a ``SimulatedTrade`` whose return / duration
/ outcome feed §11 metrics.

Phase G1 wiring: ``catalyst_weight`` and ``conviction_tier`` are not
used. Sizing is fixed at 0.5% per trade per §10 standard tier. A
position stays open until §8 fires; the partial-close ladder (T1/T2/T3)
is consolidated into a single closing event using a weighted return
so we can score the trade with one row instead of three.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from saadhana_filter.signals.engine import classify_signal
from saadhana_filter.signals.regime import Regime, latest_regime
from saadhana_filter.signals.risk import risk_levels
from saadhana_filter.signals.sell import (
    SCORE_COLLAPSE_CONSECUTIVE_DAYS,  # noqa: F401  re-exported for tests
    Position,
    SellReason,
    evaluate_sell,
)
from saadhana_filter.signals.state import SignalState

# §10 — standard tier per-trade risk.
STANDARD_RISK_PCT = 0.005

# §7 ladder weights. T1 sells 33%, T2 sells 33% more, the trailing
# 33% closes when price breaks below the 20-EMA after T2.
T1_PARTIAL_FRACTION = 1.0 / 3.0
T2_PARTIAL_FRACTION = 1.0 / 3.0
T3_PARTIAL_FRACTION = 1.0 / 3.0


@dataclass(frozen=True)
class BacktestConfig:
    """Parameters that gate replay behavior. Phase G1 ignores catalyst
    and conviction; G2 will populate the corresponding hooks."""

    universe: tuple[str, ...]
    start_date: date
    end_date: date
    risk_pct_per_trade: float = STANDARD_RISK_PCT
    max_concurrent_positions: int = 10
    use_catalyst_layer: bool = False  # Phase G2 flips this to True
    use_conviction_tiers: bool = False  # Phase G2 flips this to True


@dataclass
class SimulatedTrade:
    """One round-trip BUY → exit, in the units §11 cares about.

    ``sector`` is captured at entry-time from the fundamentals frame and
    persisted on the trade so the report can break outcomes down by
    sector without a separate join.
    """

    symbol: str
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    return_pct: float  # weighted across the §7 ladder
    days_held: int
    days_to_t1: int | None  # bars from entry to first T1 hit
    outcome: str  # SellReason value (or "STILL_OPEN" at the cutoff)
    pro_setup_score_at_entry: int
    sector: str = "UNKNOWN"


@dataclass
class BacktestResult:
    """Replay summary — feeds the §11 metrics aggregator."""

    trades: list[SimulatedTrade]
    config: BacktestConfig
    open_positions_at_end: list[Position] = field(default_factory=list)
    daily_regime: dict[date, Regime] = field(default_factory=dict)
    # Per-condition fire counters across every classify_signal call in the
    # replay. ``true_count`` = times the condition was met; ``false_count``
    # = times it failed. These let the report identify over-restrictive
    # gates (a condition that's always False is not adding signal — it's
    # blocking).
    condition_true_counts: dict[str, int] = field(default_factory=dict)
    condition_false_counts: dict[str, int] = field(default_factory=dict)
    # Total ``classify_signal`` calls — denominator for the per-condition
    # frequency stats.
    total_decisions: int = 0


# ──────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────
def _slice_to_date(df: pd.DataFrame, scan_date: pd.Timestamp) -> pd.DataFrame:
    """Return rows where ``index <= scan_date``. Forward-only — never
    returns bars from the future relative to the scan day."""
    return df.loc[df.index <= scan_date]


def _trade_from_position(
    *,
    position: Position,
    exit_bar: pd.Series,
    exit_reason: SellReason | str,
    days_held: int,
    days_to_t1: int | None,
    weighted_return: float,
    pro_setup_score_at_entry: int,
    sector: str = "UNKNOWN",
) -> SimulatedTrade:
    return SimulatedTrade(
        symbol=position.symbol,
        entry_date=position.entry_date,
        entry_price=position.entry_price,
        exit_date=exit_bar.name.date(),
        exit_price=float(exit_bar["close"]),
        return_pct=weighted_return,
        days_held=days_held,
        days_to_t1=days_to_t1,
        outcome=exit_reason if isinstance(exit_reason, str) else exit_reason.value,
        pro_setup_score_at_entry=pro_setup_score_at_entry,
        sector=sector,
    )


# ──────────────────────────────────────────────────────────────────────────
# Replay loop
# ──────────────────────────────────────────────────────────────────────────
def run_backtest(
    config: BacktestConfig,
    *,
    ohlcv: Mapping[str, pd.DataFrame],
    nifty_df: pd.DataFrame,
    fundamentals_passed: set[str] | None = None,
    sectors: Mapping[str, str] | None = None,
    progress_every: int | None = 50,
) -> BacktestResult:
    """Replay the §5 v2 engine day-by-day across ``config.universe``.

    Parameters
    ----------
    config
        Replay window, universe, sizing tier.
    ohlcv
        ``{symbol: DataFrame}`` of full-history per-symbol OHLCV. The
        replay slices each frame to the current ``scan_date`` before
        passing it into ``classify_signal`` so no future bar leaks in.
    nifty_df
        Full-history Nifty 50 index OHLCV used to compute §12 regime
        on each scan day (also sliced to the scan date).
    fundamentals_passed
        Set of symbols that pass the §4 Tier 1 gate for the replay
        window. Phase G1 treats Tier 1 as a static input — re-running
        the gate quarterly is a Phase G2 concern (catalyst-aware).
        ``None`` means "all universe symbols pass".
    """
    if fundamentals_passed is None:
        fundamentals_passed = set(config.universe)
    if sectors is None:
        sectors = {}

    from saadhana_filter.indicators.conditions import ALL_CONDITIONS, pro_setup_score
    from saadhana_filter.signals.regime import market_regime

    open_positions: dict[str, Position] = {}
    # Per-position bookkeeping needed for ladder + days-to-T1 reporting.
    bookkeeping: dict[str, dict] = {}
    trades: list[SimulatedTrade] = []
    daily_regime: dict[date, Regime] = {}
    # Per-condition counters — incremented every time we evaluate a
    # candidate (Tier-1-passing, regime-allows-BUY, has lookback).
    condition_true_counts: dict[str, int] = {name: 0 for name, _ in ALL_CONDITIONS}
    condition_false_counts: dict[str, int] = {name: 0 for name, _ in ALL_CONDITIONS}
    total_decisions = 0

    # ── Precomputation pass (the speedup) ─────────────────────────────
    # Conditions are point-in-time / backward-looking; pro_setup_score
    # over the full history is mathematically identical to slicing per
    # scan day and recomputing. Doing it once collapses an O(n²) loop
    # into O(n) — for Nifty 500 × 757 days this is 100×+ faster.
    #
    # No lookahead bias is introduced as long as we *index into* the
    # precomputed frame at the scan day (not look forward).
    if progress_every:
        import sys

        print(
            f"  [precompute] computing per-symbol score panels...",
            file=sys.stderr,
            flush=True,
        )
    score_panels: dict[str, pd.DataFrame] = {}
    for symbol in config.universe:
        if symbol not in ohlcv:
            continue
        df_full = ohlcv[symbol]
        if df_full.empty:
            continue
        score_panels[symbol] = pro_setup_score(df_full)
    regime_series = market_regime(nifty_df)
    if progress_every:
        print(
            f"  [precompute] done — {len(score_panels)} symbol panels cached",
            file=sys.stderr,
            flush=True,
        )

    # Build a master calendar from the index — every bar with a Nifty
    # close is a candidate scan day; intersect with the replay window.
    calendar = nifty_df.index[
        (nifty_df.index.date >= config.start_date) & (nifty_df.index.date <= config.end_date)
    ]

    for i, scan_ts in enumerate(calendar):
        if progress_every and i and i % progress_every == 0:
            import sys

            print(
                f"  [replay] day {i}/{len(calendar)} {scan_ts.date().isoformat()} "
                f"open={len(open_positions)} closed_trades={len(trades)}",
                file=sys.stderr,
                flush=True,
            )
        scan_date = scan_ts.date()
        if scan_ts not in regime_series.index:
            continue
        regime = Regime(regime_series.loc[scan_ts])
        daily_regime[scan_date] = regime

        # ── 1. Evaluate every open position ────────────────────────
        for symbol in list(open_positions.keys()):
            if symbol not in ohlcv:
                continue
            df = _slice_to_date(ohlcv[symbol], scan_ts)
            if df.empty or scan_ts not in df.index:
                continue

            position = open_positions[symbol]
            book = bookkeeping[symbol]

            sell_reason = evaluate_sell(df, position)
            last_bar = df.iloc[-1]

            # Track when T1 first hits — even partials count as "first
            # +5% reached" for the §11 ``avg days to T1`` metric.
            if book["days_to_t1"] is None and float(last_bar["close"]) >= position.entry_price * (
                1 + 0.05
            ):
                book["days_to_t1"] = (scan_date - position.entry_date).days

            if sell_reason is None:
                continue

            # T1/T2 advance the ladder but don't close the position;
            # T3/STOP/etc. close it fully and record the trade.
            if sell_reason == SellReason.T1_HIT and not position.t1_hit:
                book["weighted_return"] += T1_PARTIAL_FRACTION * 0.05  # locked
                open_positions[symbol] = Position(
                    symbol=position.symbol,
                    entry_date=position.entry_date,
                    entry_price=position.entry_price,
                    initial_stop=position.initial_stop,
                    current_stop=position.entry_price,  # → breakeven
                    t1_hit=True,
                    t2_hit=False,
                )
                continue

            if sell_reason == SellReason.T2_HIT and not position.t2_hit:
                book["weighted_return"] += T2_PARTIAL_FRACTION * 0.10
                open_positions[symbol] = Position(
                    symbol=position.symbol,
                    entry_date=position.entry_date,
                    entry_price=position.entry_price,
                    initial_stop=position.initial_stop,
                    current_stop=position.current_stop,  # spec: trail 20-EMA
                    t1_hit=True,
                    t2_hit=True,
                )
                continue

            # Final close — compute the residual return from the
            # remainder of the position.
            residual_return = (
                float(last_bar["close"]) - position.entry_price
            ) / position.entry_price
            remaining_fraction = 1.0
            if position.t1_hit:
                remaining_fraction -= T1_PARTIAL_FRACTION
            if position.t2_hit:
                remaining_fraction -= T2_PARTIAL_FRACTION
            book["weighted_return"] += remaining_fraction * residual_return

            trades.append(
                _trade_from_position(
                    position=position,
                    exit_bar=last_bar,
                    exit_reason=sell_reason,
                    days_held=(scan_date - position.entry_date).days,
                    days_to_t1=book["days_to_t1"],
                    weighted_return=book["weighted_return"],
                    pro_setup_score_at_entry=book["entry_score"],
                    sector=book.get("sector", "UNKNOWN"),
                )
            )
            del open_positions[symbol]
            del bookkeeping[symbol]

        # ── 2. Look for new BUY entries ─────────────────────────────
        if regime == Regime.RISK_OFF:
            continue
        if len(open_positions) >= config.max_concurrent_positions:
            continue

        for symbol in config.universe:
            if symbol in open_positions:
                continue
            if symbol not in fundamentals_passed:
                continue
            if symbol not in score_panels:
                continue
            panel = score_panels[symbol]
            if scan_ts not in panel.index:
                continue
            row = panel.loc[scan_ts]
            score = int(row["score"])

            # Per-condition fire counter — same semantics as before, just
            # sourced from the precomputed panel instead of a fresh
            # classify_signal call.
            total_decisions += 1
            for cname, _ in ALL_CONDITIONS:
                if bool(row[cname]):
                    condition_true_counts[cname] += 1
                else:
                    condition_false_counts[cname] += 1

            # §12 / §3 BUY logic — mirrors classify_signal exactly:
            # Risk_Off → no BUY. Caution → score==13 downgrades to WATCH
            # (Phase F adds conviction; until then no BUY in Caution).
            # Risk_On + score==13 → BUY.
            if regime != Regime.RISK_ON or score < 13:
                continue

            df_slice = _slice_to_date(ohlcv[symbol], scan_ts)
            if df_slice.empty or len(df_slice) < 252:
                continue
            risk = risk_levels(df_slice)
            position = Position(
                symbol=symbol,
                entry_date=scan_date,
                entry_price=risk.entry_price,
                initial_stop=risk.stop_loss,
                current_stop=risk.stop_loss,
            )
            open_positions[symbol] = position
            bookkeeping[symbol] = {
                "entry_score": score,
                "weighted_return": 0.0,
                "days_to_t1": None,
                "sector": sectors.get(symbol, "UNKNOWN"),
            }
            if len(open_positions) >= config.max_concurrent_positions:
                break  # done with new entries today

    # ── 3. Mark-to-market unclosed positions at the cutoff ─────────
    last_ts = calendar[-1] if len(calendar) else None
    for symbol, position in open_positions.items():
        if last_ts is None or symbol not in ohlcv:
            continue
        df = _slice_to_date(ohlcv[symbol], last_ts)
        if df.empty:
            continue
        last_bar = df.iloc[-1]
        residual_return = (float(last_bar["close"]) - position.entry_price) / position.entry_price
        book = bookkeeping[symbol]
        remaining_fraction = 1.0
        if position.t1_hit:
            remaining_fraction -= T1_PARTIAL_FRACTION
        if position.t2_hit:
            remaining_fraction -= T2_PARTIAL_FRACTION
        weighted = book["weighted_return"] + remaining_fraction * residual_return
        trades.append(
            _trade_from_position(
                position=position,
                exit_bar=last_bar,
                exit_reason="STILL_OPEN",
                days_held=(last_bar.name.date() - position.entry_date).days,
                days_to_t1=book["days_to_t1"],
                weighted_return=weighted,
                pro_setup_score_at_entry=book["entry_score"],
                sector=book.get("sector", "UNKNOWN"),
            )
        )

    return BacktestResult(
        trades=trades,
        config=config,
        open_positions_at_end=list(open_positions.values()),
        daily_regime=daily_regime,
        condition_true_counts=condition_true_counts,
        condition_false_counts=condition_false_counts,
        total_decisions=total_decisions,
    )
