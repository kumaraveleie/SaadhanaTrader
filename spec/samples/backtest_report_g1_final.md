# Saadhana Backtest — Phase G1 (technical-only)

**Phase:** G1 — diagnostic gate
**Generated:** 2026-04-30
**Replay window:** 2023-04-01 → 2026-04-30
**Universe:** 399 symbols
**Per-trade risk:** 0.50% (§10 standard tier)
**Catalyst layer:** off (Phase G2)
**Conviction tiers:** off (Phase G2)

---

## §11 Backtest Validation

**OVERALL: FAIL** — tighten §5 rules before adding any more layers.

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| Hit rate (% reaching +5%) | ≥ 45% | 41.1% | FAIL |
| Avg days to T1 | ≤ 25 | 11.3 | PASS |
| Avg win | ≥ +6% | +6.19% | PASS |
| Avg loss | ≤ −3% | -2.86% | PASS |
| Max consecutive losses | ≤ 8 | 7 | PASS |
| Win/loss ratio | ≥ 2.0 | 2.16 | PASS |
| Profit Factor | ≥ 1.8 | 1.95 | PASS |
| Sharpe (annualized) | ≥ 1.5 | 2.81 | PASS |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 41 |
| `INST_SELL_EXIT` | 24 |
| `T3_TRAIL_BREAK` | 17 |
| `SCORE_COLLAPSE_EXIT` | 10 |
| `STAGE_SHIFT_EXIT` | 1 |
| `RSI_DIVERGENCE_EXIT` | 1 |
| `CATASTROPHIC_BREAK` | 1 |

**Total trades:** 95
**Closed:** 95 (45 wins, 50 losses)
**Still open at cutoff:** 0

## Per-Condition Fire Frequency

Computed across **221,222** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 57,542 | 163,680 | 26.0% |
| `distance_to_stop_le_3pct` | 66,448 | 154,774 | 30.0% |
| `institutional_flow` | 71,576 | 149,646 | 32.4% |
| `rr_ge_2` | 87,790 | 133,432 | 39.7% |
| `5ema_above_20ema_rising` | 88,894 | 132,328 | 40.2% |
| `weekly_hh_hl` | 101,854 | 119,368 | 46.0% |
| `rsi_50_70` | 111,400 | 109,822 | 50.4% |
| `bb_width_alive` | 112,666 | 108,556 | 50.9% |
| `above_50_and_200_ema` | 119,540 | 101,682 | 54.0% |
| `inst_flow_score` | 124,747 | 96,475 | 56.4% |
| `stage_2` | 132,376 | 88,846 | 59.8% |
| `atr_upside_ge_5pct` | 185,312 | 35,910 | 83.8% |
| `not_extended` | 209,794 | 11,428 | 94.8% |

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `INDUSTRIAL` | 95 | 45 | 50 | +1.43% | 47.4% |

## Diagnostic Extras

- Median trade return: -0.38%
- Best trade: +15.25%
- Worst trade: -6.31%
- Expectancy per trade: +1.43%

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.
- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.
- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.
  Quarterly fundamentals refresh is a Phase G2 concern.
