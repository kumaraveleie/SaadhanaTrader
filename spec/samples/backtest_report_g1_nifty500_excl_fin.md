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
| Hit rate (% reaching +5%) | ≥ 60% | 41.1% | FAIL |
| Avg days to T1 | ≤ 25 | 11.3 | PASS |
| Avg win | ≥ +8% | +6.19% | FAIL |
| Avg loss | ≤ −2.5% | -2.86% | FAIL |
| Max consecutive losses | ≤ 5 | 7 | FAIL |
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

Computed across **221,300** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 57,548 | 163,752 | 26.0% |
| `distance_to_stop_le_3pct` | 66,456 | 154,844 | 30.0% |
| `institutional_flow` | 71,599 | 149,701 | 32.4% |
| `rr_ge_2` | 87,808 | 133,492 | 39.7% |
| `5ema_above_20ema_rising` | 88,910 | 132,390 | 40.2% |
| `weekly_hh_hl` | 101,899 | 119,401 | 46.0% |
| `rsi_50_70` | 111,459 | 109,841 | 50.4% |
| `bb_width_alive` | 112,682 | 108,618 | 50.9% |
| `above_50_and_200_ema` | 119,551 | 101,749 | 54.0% |
| `inst_flow_score` | 124,793 | 96,507 | 56.4% |
| `stage_2` | 132,381 | 88,919 | 59.8% |
| `atr_upside_ge_5pct` | 185,336 | 35,964 | 83.7% |
| `not_extended` | 209,871 | 11,429 | 94.8% |

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
