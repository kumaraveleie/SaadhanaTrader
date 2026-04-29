# Saadhana Backtest — Phase G1 (technical-only)

**Phase:** G1 — diagnostic gate
**Generated:** 2026-04-30
**Replay window:** 2023-04-01 → 2026-04-30
**Universe:** 500 symbols
**Per-trade risk:** 0.50% (§10 standard tier)
**Catalyst layer:** off (Phase G2)
**Conviction tiers:** off (Phase G2)

---

## §11 Backtest Validation

**OVERALL: FAIL** — tighten §5 rules before adding any more layers.

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| Hit rate (% reaching +5%) | ≥ 60% | 29.5% | FAIL |
| Avg days to T1 | ≤ 25 | 12.7 | PASS |
| Avg win | ≥ +8% | +5.44% | FAIL |
| Avg loss | ≤ −2.5% | -3.26% | FAIL |
| Max consecutive losses | ≤ 5 | 9 | FAIL |
| Win/loss ratio | ≥ 2.0 | 1.67 | FAIL |
| Profit Factor | ≥ 1.8 | 0.91 | FAIL |
| Sharpe (annualized) | ≥ 1.5 | -0.45 | FAIL |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 107 |
| `INST_SELL_EXIT` | 55 |
| `T3_TRAIL_BREAK` | 19 |
| `SCORE_COLLAPSE_EXIT` | 15 |
| `STAGE_SHIFT_EXIT` | 7 |
| `CATASTROPHIC_BREAK` | 2 |
| `RSI_DIVERGENCE_EXIT` | 1 |
| `TIME_EXIT` | 1 |

**Total trades:** 207
**Closed:** 207 (73 wins, 134 losses)
**Still open at cutoff:** 0

## Per-Condition Fire Frequency

Computed across **255,147** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 66,170 | 188,977 | 25.9% |
| `institutional_flow` | 82,360 | 172,787 | 32.3% |
| `distance_to_stop_le_3pct` | 94,969 | 160,178 | 37.2% |
| `rr_ge_2` | 100,765 | 154,382 | 39.5% |
| `5ema_above_20ema_rising` | 102,507 | 152,640 | 40.2% |
| `weekly_hh_hl` | 117,355 | 137,792 | 46.0% |
| `rsi_50_70` | 128,769 | 126,378 | 50.5% |
| `bb_width_alive` | 130,242 | 124,905 | 51.0% |
| `above_50_and_200_ema` | 139,053 | 116,094 | 54.5% |
| `inst_flow_score` | 142,948 | 112,199 | 56.0% |
| `stage_2` | 154,642 | 100,505 | 60.6% |
| `atr_upside_ge_5pct` | 212,771 | 42,376 | 83.4% |
| `not_extended` | 241,569 | 13,578 | 94.7% |

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `INDUSTRIAL` | 161 | 61 | 100 | +0.19% | 37.9% |
| `FINANCIAL_SERVICES` | 30 | 7 | 23 | -1.89% | 23.3% |
| `NBFC` | 10 | 4 | 6 | +0.58% | 40.0% |
| `BANK` | 6 | 1 | 5 | -3.24% | 16.7% |

## Diagnostic Extras

- Median trade return: -1.94%
- Best trade: +23.81%
- Worst trade: -10.05%
- Expectancy per trade: -0.19%

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.
- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.
- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.
  Quarterly fundamentals refresh is a Phase G2 concern.
