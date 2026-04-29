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
| Hit rate (% reaching +5%) | ≥ 60% | 34.1% | FAIL |
| Avg days to T1 | ≤ 25 | 10.8 | PASS |
| Avg win | ≥ +8% | +6.02% | FAIL |
| Avg loss | ≤ −2.5% | -2.96% | FAIL |
| Max consecutive losses | ≤ 5 | 9 | FAIL |
| Win/loss ratio | ≥ 2.0 | 2.04 | PASS |
| Profit Factor | ≥ 1.8 | 1.29 | FAIL |
| Sharpe (annualized) | ≥ 1.5 | 1.12 | FAIL |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 67 |
| `INST_SELL_EXIT` | 29 |
| `T3_TRAIL_BREAK` | 18 |
| `SCORE_COLLAPSE_EXIT` | 10 |
| `STAGE_SHIFT_EXIT` | 3 |
| `RSI_DIVERGENCE_EXIT` | 1 |
| `CATASTROPHIC_BREAK` | 1 |

**Total trades:** 129
**Closed:** 129 (50 wins, 79 losses)
**Still open at cutoff:** 0

## Per-Condition Fire Frequency

Computed across **277,239** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 72,360 | 204,879 | 26.1% |
| `distance_to_stop_le_3pct` | 84,104 | 193,135 | 30.3% |
| `institutional_flow` | 89,843 | 187,396 | 32.4% |
| `rr_ge_2` | 110,604 | 166,635 | 39.9% |
| `5ema_above_20ema_rising` | 112,241 | 164,998 | 40.5% |
| `weekly_hh_hl` | 128,587 | 148,652 | 46.4% |
| `rsi_50_70` | 140,620 | 136,619 | 50.7% |
| `bb_width_alive` | 140,648 | 136,591 | 50.7% |
| `above_50_and_200_ema` | 151,419 | 125,820 | 54.6% |
| `inst_flow_score` | 156,189 | 121,050 | 56.3% |
| `stage_2` | 167,208 | 110,031 | 60.3% |
| `atr_upside_ge_5pct` | 231,083 | 46,156 | 83.4% |
| `not_extended` | 262,452 | 14,787 | 94.7% |

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `INDUSTRIAL` | 94 | 45 | 49 | +1.50% | 47.9% |
| `FINANCIAL_SERVICES` | 27 | 3 | 24 | -2.29% | 11.1% |
| `NBFC` | 5 | 1 | 4 | -3.09% | 20.0% |
| `BANK` | 3 | 1 | 2 | +1.08% | 33.3% |

## Diagnostic Extras

- Median trade return: -1.47%
- Best trade: +15.25%
- Worst trade: -7.91%
- Expectancy per trade: +0.52%

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.
- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.
- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.
  Quarterly fundamentals refresh is a Phase G2 concern.
