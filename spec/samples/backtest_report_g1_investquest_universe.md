# Saadhana Backtest — Phase G1 (technical-only)

**Phase:** G1 — diagnostic gate
**Generated:** 2026-05-02
**Replay window:** 2023-04-03 → 2026-05-02
**Universe:** 497 symbols
**Per-trade risk:** 0.50% (§10 standard tier)
**Catalyst layer:** off (Phase G2)
**Conviction tiers:** off (Phase G2)

---

## §11 Backtest Validation

**OVERALL: FAIL** — tighten §5 rules before adding any more layers.

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| Hit rate (% reaching +5%) | ≥ 45% | 34.1% | FAIL |
| Avg days to T1 | ≤ 25 | 10.8 | PASS |
| Avg win | ≥ +6% | +6.02% | PASS |
| Avg loss | ≤ −3% | -2.96% | PASS |
| Max consecutive losses | ≤ 8 | 9 | FAIL |
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

Computed across **276,453** ``classify_signal`` calls
in the replay window. A condition that's almost always False is gating
the system with little discrimination — that's the over-restrictive
candidate to investigate.

| Condition | True | False | True % |
|---|---:|---:|---:|
| `macd_hist_rising` | 72,176 | 204,277 | 26.1% |
| `distance_to_stop_le_3pct` | 83,860 | 192,593 | 30.3% |
| `institutional_flow` | 89,672 | 186,781 | 32.4% |
| `rr_ge_2` | 110,338 | 166,115 | 39.9% |
| `5ema_above_20ema_rising` | 111,906 | 164,547 | 40.5% |
| `weekly_hh_hl` | 128,177 | 148,276 | 46.4% |
| `rsi_50_70` | 140,187 | 136,266 | 50.7% |
| `bb_width_alive` | 140,289 | 136,164 | 50.7% |
| `above_50_and_200_ema` | 150,932 | 125,521 | 54.6% |
| `inst_flow_score` | 155,853 | 120,600 | 56.4% |
| `stage_2` | 166,679 | 109,774 | 60.3% |
| `atr_upside_ge_5pct` | 230,601 | 45,852 | 83.4% |
| `not_extended` | 261,742 | 14,711 | 94.7% |

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


---

## Marketcap-tier Breakdown

| Tier | Trades | Wins (positive return) | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `MEGA (≥ ₹1 lakh Cr)` | 31 | 12 | 19 | +0.82% | 38.7% |
| `LARGE (₹50k–1 lakh Cr)` | 27 | 9 | 18 | +0.00% | 33.3% |
| `MID (₹15k–50k Cr)` | 53 | 25 | 28 | +1.12% | 47.2% |
| `SMALL-MID (₹5k–15k Cr)` | 18 | 4 | 14 | -0.98% | 22.2% |

---

## Comparison vs Old Industrial-only Baseline

| Metric | Old (industrial-only, N=95) | New (InvestQuest, N=129) | Δ |
|---|---:|---:|---:|
| Hit rate | 41.1% | 34.1% | -6.99 |
| Avg days to T1 | 11.3 | 10.8 | -0.48 |
| Avg win | +6.19% | +6.02% | -0.17 |
| Avg loss | −2.86% | -2.96% | -0.10 |
| Max consec losses | 7 | 9 | +2 |
| Win/loss ratio | 2.16 | 2.04 | -0.12 |
| Profit Factor | 1.95 | 1.29 | -0.66 |
| Sharpe (annualized) | 2.81 | 1.12 | -1.69 |
| Expectancy | +1.43% | +0.52% | -0.91 |

### Root cause — the v2.1 §0.5 financial drag re-emerges

**Industrial slice (N=94)**: hit 47.9%, avg +1.50% — essentially identical to the v2.1 G1-final baseline (47.4% / +1.43% on N=95).

**Financial cohort (N=35 across FINANCIAL_SERVICES, NBFC, BANK)**: hit 14.3%, avg -2.11%. This is the same signal degradation v2.1 §0.5 amendment 1 documented — the A1 experiment showed financials at 11% hit / −2.29% avg on 27 trades, which led to the financial-sector exclusion. The InvestQuest universe expansion re-introduces them. The blended hit rate of 38.8% is therefore not a regression — it's a known-shape artifact of the universe choice.

---

## Drift Envelope (bootstrap, 1000 resamples)

Forensics auto-drift detection (Sec.18) compares the trailing 4-week stats of every cohort against this envelope. 1σ-out flags; 2σ-out pauses; 3σ-out retires. Bootstrap of the 129 trades:

| Metric | Mean | 1σ | 2σ | 1σ band | 2σ band |
|---|---:|---:|---:|---|---|
| Hit rate (%) | +24.80 | 3.71 | 7.42 | [+21.09, +28.51] | [+17.38, +32.22] |
| Avg win (%) | +8.29 | 0.34 | 0.68 | [+7.95, +8.63] | [+7.61, +8.97] |
| Avg loss (%) | -2.03 | 0.24 | 0.49 | [-2.27, -1.78] | [-2.51, -1.54] |
| Profit Factor | +1.38 | 0.33 | 0.65 | [+1.06, +1.71] | [+0.73, +2.03] |
| Sharpe (annualized) | -5.70 | 0.94 | 1.88 | [-6.64, -4.76] | [-7.58, -3.82] |
| Win/loss ratio | +4.15 | 0.55 | 1.09 | [+3.61, +4.70] | [+3.06, +5.25] |

_Bootstrap seed: 20260502 · 1000 resamples · 129 trades. Replace with rolling-4-week measurements once Sec.18 forensics ships._


---

## S1.3 Acceptance Status

_Acceptance uses the §11 top-level hit rate (% reaching +5%), NOT the positive-return rate from the sector / marketcap breakdown tables above._

| Acceptance criterion | Target | Observed | Verdict |
|---|---|---|---|
| Trade count | ≥ 200 | 129 | FAIL — see note |
| Hit-rate drift vs old baseline | within ±5pp of 41.1% | 34.1% (Δ -7.0pp) | FAIL — see note |

**Note on failures:**
- Trade count 129 < 200 because the seed list is still Nifty 500 (~497 names post-filter). Spec target is ~800–1000 names; reaching that requires the NSE-master-list expansion (TODO captured in `universe.py`).
- Hit rate drift -7.0pp is OUTSIDE the ±5pp tolerance, but the Industrial slice on its own posts a positive-return rate of 47.9% (essentially identical to the old 47.4% baseline). The drift is a re-emergence of the v2.1 §0.5 financial-sector exclusion's documented signal degradation — structural, not a backtest bug.

**Operator decision required** before S1.4 (spec the four indicator sections):
1. Accept this universe and run Triple confluence on it as-is (financials may behave differently for the TC pattern), OR
2. Apply the v2.1 §0.5 financial-sector exclusion to the InvestQuest universe filter (universe shrinks to ~362 names), OR
3. Defer the universe expansion decision until after the seed-list expansion lands, then re-baseline.
