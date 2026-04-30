"""Markdown report generator for ``spec/samples/backtest_report_*.md``.

Phase G1 emits a report with the §11 metric block (pass/fail per metric,
overall PASS/FAIL banner) plus a trade-level breakdown the user can
eyeball before approving the catalyst layer.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from saadhana_filter.backtest.metrics import BacktestMetrics
from saadhana_filter.backtest.replay import BacktestResult


def _yes_no(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _fmt_pct(v: float) -> str:
    return f"{v:+.2f}%"


def _fmt_days(v: float | None) -> str:
    return f"{v:.1f}" if v is not None else "—"


def render_markdown_report(
    *,
    title: str,
    phase_label: str,
    result: BacktestResult,
    metrics: BacktestMetrics,
    generated_at: date,
) -> str:
    """Render a Phase-G report as Markdown."""
    cfg = result.config
    outcomes = Counter(t.outcome for t in result.trades)

    overall_banner = (
        "**OVERALL: PASS** — technical layer has predictive value; the "
        "catalyst layer in Phase D can be confidently additive."
        if metrics.overall_passes
        else "**OVERALL: FAIL** — tighten §5 rules before adding any more layers."
    )

    lines: list[str] = []
    lines += [
        f"# {title}",
        "",
        f"**Phase:** {phase_label}",
        f"**Generated:** {generated_at.isoformat()}",
        f"**Replay window:** {cfg.start_date.isoformat()} → {cfg.end_date.isoformat()}",
        f"**Universe:** {len(cfg.universe)} symbols",
        f"**Per-trade risk:** {cfg.risk_pct_per_trade * 100:.2f}% (§10 standard tier)",
        f"**Catalyst layer:** {'on' if cfg.use_catalyst_layer else 'off (Phase G2)'}",
        f"**Conviction tiers:** {'on' if cfg.use_conviction_tiers else 'off (Phase G2)'}",
        "",
        "---",
        "",
        "## §11 Backtest Validation",
        "",
        overall_banner,
        "",
        "| Metric | Target | Observed | Verdict |",
        "|---|---|---|---|",
        f"| Hit rate (% reaching +5%) | ≥ 45% | {metrics.hit_rate_pct:.1f}% | {_yes_no(metrics.hit_rate_passes)} |",
        f"| Avg days to T1 | ≤ 25 | {_fmt_days(metrics.avg_days_to_t1)} | {_yes_no(metrics.days_to_t1_passes)} |",
        f"| Avg win | ≥ +6% | {_fmt_pct(metrics.avg_win_pct)} | {_yes_no(metrics.avg_win_passes)} |",
        f"| Avg loss | ≤ −3% | {_fmt_pct(metrics.avg_loss_pct)} | {_yes_no(metrics.avg_loss_passes)} |",
        f"| Max consecutive losses | ≤ 8 | {metrics.max_consecutive_losses} | {_yes_no(metrics.consecutive_losses_passes)} |",
        f"| Win/loss ratio | ≥ 2.0 | {metrics.win_loss_ratio:.2f} | {_yes_no(metrics.win_loss_passes)} |",
        f"| Profit Factor | ≥ 1.8 | {metrics.profit_factor:.2f} | {_yes_no(metrics.profit_factor_passes)} |",
        f"| Sharpe (annualized) | ≥ 1.5 | {metrics.sharpe_annualized:.2f} | {_yes_no(metrics.sharpe_passes)} |",
        "",
        "## Trade Outcome Distribution",
        "",
        "| Outcome | Count |",
        "|---|---|",
    ]
    for outcome, count in outcomes.most_common():
        lines.append(f"| `{outcome}` | {count} |")
    lines += [
        "",
        f"**Total trades:** {metrics.n_trades}",
        f"**Closed:** {metrics.n_wins + metrics.n_losses} ({metrics.n_wins} wins, {metrics.n_losses} losses)",
        f"**Still open at cutoff:** {metrics.n_still_open}",
        "",
    ]

    # ── Per-condition fire frequency ────────────────────────────────
    if result.total_decisions > 0:
        lines += [
            "## Per-Condition Fire Frequency",
            "",
            f"Computed across **{result.total_decisions:,}** ``classify_signal`` calls",
            "in the replay window. A condition that's almost always False is gating",
            "the system with little discrimination — that's the over-restrictive",
            "candidate to investigate.",
            "",
            "| Condition | True | False | True % |",
            "|---|---:|---:|---:|",
        ]
        for cname, true_count in sorted(
            result.condition_true_counts.items(),
            key=lambda kv: kv[1],
        ):
            false_count = result.condition_false_counts.get(cname, 0)
            total = true_count + false_count
            pct = (true_count / total * 100.0) if total else 0.0
            lines.append(f"| `{cname}` | {true_count:,} | {false_count:,} | {pct:.1f}% |")
        lines.append("")

    # ── Sector breakdown of trades + outcomes ───────────────────────
    if result.trades:
        from collections import defaultdict

        bucket: dict[str, dict] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "losses": 0, "ret_sum": 0.0}
        )
        for t in result.trades:
            b = bucket[t.sector]
            b["trades"] += 1
            b["ret_sum"] += t.return_pct
            if t.outcome == "STILL_OPEN":
                continue
            if t.return_pct > 0:
                b["wins"] += 1
            else:
                b["losses"] += 1

        lines += [
            "## Sector Breakdown",
            "",
            "| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for sector in sorted(bucket.keys(), key=lambda s: -bucket[s]["trades"]):
            b = bucket[sector]
            n_closed = b["wins"] + b["losses"]
            avg_ret = (b["ret_sum"] / b["trades"]) * 100 if b["trades"] else 0
            hit_rate = (b["wins"] / n_closed * 100) if n_closed else 0
            lines.append(
                f"| `{sector}` | {b['trades']} | {b['wins']} | "
                f"{b['losses']} | {avg_ret:+.2f}% | {hit_rate:.1f}% |"
            )
        lines.append("")

    lines += [
        "## Diagnostic Extras",
        "",
        f"- Median trade return: {_fmt_pct(metrics.median_return_pct)}",
        f"- Best trade: {_fmt_pct(metrics.best_trade_pct)}",
        f"- Worst trade: {_fmt_pct(metrics.worst_trade_pct)}",
        f"- Expectancy per trade: {_fmt_pct(metrics.expectancy_pct)}",
        "",
        "## Notes",
        "",
        "- Forward-only data discipline: each scan day sees only bars ≤ that day.",
        "- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.",
        "- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.",
        "- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.",
        "  Quarterly fundamentals refresh is a Phase G2 concern.",
        "",
    ]
    return "\n".join(lines)
