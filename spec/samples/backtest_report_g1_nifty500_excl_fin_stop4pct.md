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
| Hit rate (% reaching +5%) | ≥ 60% | 33.3% | FAIL |
| Avg days to T1 | ≤ 25 | 12.7 | PASS |
| Avg win | ≥ +8% | +5.75% | FAIL |
| Avg loss | ≤ −2.5% | -3.22% | FAIL |
| Max consecutive losses | ≤ 5 | 11 | FAIL |
| Win/loss ratio | ≥ 2.0 | 1.78 | FAIL |
| Profit Factor | ≥ 1.8 | 1.20 | FAIL |
| Sharpe (annualized) | ≥ 1.5 | 0.83 | FAIL |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 81 |
| `INST_SELL_EXIT` | 51 |
| `T3_TRAIL_BREAK` | 23 |
| `SCORE_COLLAPSE_EXIT` | 13 |
| `STAGE_SHIFT_EXIT` | 5 |
| `CATASTROPHIC_BREAK` | 2 |
| `RSI_DIVERGENCE_EXIT` | 1 |
| `TIME_EXIT` | 1 |

**Total trades:** 177
**Closed:** 177 (71 wins, 106 losses)
**Still open at cutoff:** 0

## Per-Condition Fire Frequency

Computed across **208,305** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 54,122 | 154,183 | 26.0% |
| `institutional_flow` | 67,061 | 141,244 | 32.2% |
| `distance_to_stop_le_3pct` | 77,633 | 130,672 | 37.3% |
| `rr_ge_2` | 82,636 | 125,669 | 39.7% |
| `5ema_above_20ema_rising` | 83,749 | 124,556 | 40.2% |
| `weekly_hh_hl` | 95,458 | 112,847 | 45.8% |
| `rsi_50_70` | 105,134 | 103,171 | 50.5% |
| `bb_width_alive` | 105,856 | 102,449 | 50.8% |
| `above_50_and_200_ema` | 112,926 | 95,379 | 54.2% |
| `inst_flow_score` | 117,417 | 90,888 | 56.4% |
| `stage_2` | 125,089 | 83,216 | 60.1% |
| `atr_upside_ge_5pct` | 174,472 | 33,833 | 83.8% |
| `not_extended` | 197,516 | 10,789 | 94.8% |

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `INDUSTRIAL` | 177 | 71 | 106 | +0.38% | 40.1% |

## Diagnostic Extras

- Median trade return: -1.03%
- Best trade: +23.81%
- Worst trade: -7.13%
- Expectancy per trade: +0.38%

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.
- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.
- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.
  Quarterly fundamentals refresh is a Phase G2 concern.
