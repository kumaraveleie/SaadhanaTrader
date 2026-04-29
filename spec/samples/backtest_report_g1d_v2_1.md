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
| Hit rate (% reaching +5%) | ≥ 60% | 27.3% | FAIL |
| Avg days to T1 | ≤ 25 | 15.7 | PASS |
| Avg win | ≥ +8% | +5.82% | FAIL |
| Avg loss | ≤ −2.5% | -1.98% | PASS |
| Max consecutive losses | ≤ 5 | 4 | PASS |
| Win/loss ratio | ≥ 2.0 | 2.93 | PASS |
| Profit Factor | ≥ 1.8 | 1.67 | FAIL |
| Sharpe (annualized) | ≥ 1.5 | 2.66 | PASS |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 4 |
| `T3_TRAIL_BREAK` | 3 |
| `SCORE_COLLAPSE_EXIT` | 2 |
| `INST_SELL_EXIT` | 2 |

**Total trades:** 11
**Closed:** 11 (4 wins, 7 losses)
**Still open at cutoff:** 0

## Per-Condition Fire Frequency

Computed across **226,841** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 59,269 | 167,572 | 26.1% |
| `distance_to_stop_le_3pct` | 68,659 | 158,182 | 30.3% |
| `institutional_flow` | 74,055 | 152,786 | 32.6% |
| `recent_strength_not_extended` | 84,272 | 142,569 | 37.2% |
| `rr_ge_2` | 90,517 | 136,324 | 39.9% |
| `5ema_above_20ema_rising` | 92,491 | 134,350 | 40.8% |
| `weekly_hh_hl` | 106,188 | 120,653 | 46.8% |
| `rsi_50_70` | 115,134 | 111,707 | 50.8% |
| `bb_width_alive` | 115,793 | 111,048 | 51.0% |
| `above_50_and_200_ema` | 124,081 | 102,760 | 54.7% |
| `inst_flow_score` | 128,801 | 98,040 | 56.8% |
| `stage_2` | 136,737 | 90,104 | 60.3% |
| `atr_upside_ge_5pct` | 189,004 | 37,837 | 83.3% |

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `INDUSTRIAL` | 11 | 4 | 7 | +0.85% | 36.4% |

## Diagnostic Extras

- Median trade return: -0.55%
- Best trade: +8.27%
- Worst trade: -3.47%
- Expectancy per trade: +0.85%

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.
- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.
- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.
  Quarterly fundamentals refresh is a Phase G2 concern.
