# Saadhana Backtest — Sprint 2.3 (Triple confluence cohort)

**Phase:** S2.3 — Triple confluence go/no-go decision
**Generated:** 2026-05-03
**Replay window:** 2023-04-03 → 2026-05-02
**Universe:** 396 symbols (InvestQuest, MCap ≥ ₹5,000 Cr · ADV ≥ ₹5 Cr)
**Cohort:** `triple_confluence` (Sec.5.10)
**Sector exclusions:** `[]` (v1 default per Sec.5.10; revisit if financial drag re-emerges)
**Per-trade risk:** §10 STANDARD (medium conviction) / HIGH (3-of-3 conviction)

---

## §11 Backtest Validation

**OVERALL: FAIL**

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| Hit rate (% reaching +5%) | ≥ 45% | 51.7% | PASS |
| Avg days to T1 | ≤ 25 | 6.6 | PASS |
| Avg win | ≥ +6% | +8.44% | PASS |
| Avg loss | ≤ −3% | -5.81% | PASS |
| Max consecutive losses | ≤ 8 | 34 | FAIL |
| Win/loss ratio | ≥ 2.0 | 1.45 | FAIL |
| Profit Factor | ≥ 1.8 | 0.97 | FAIL |
| Sharpe (annualized) | ≥ 1.5 | -0.23 | FAIL |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 1695 |
| `WIN_T3` | 1088 |
| `TIME_EXIT` | 186 |
| `WIN_T1` | 9 |
| `WIN_T2` | 2 |

**Total trades:** 2980
**Closed:** 2980 (1193 wins, 1787 losses)

## Conviction-tier split

| Conviction | N | Hit rate (% reaching +5%) | Avg win | Avg loss | Profit Factor | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| 2-of-3 medium (STANDARD sizing) | 2376 | 50.9% | +8.44% | -5.79% | 0.94 | -0.48 |
| 3-of-3 high (HIGH sizing) | 604 | 55.0% | +8.44% | -5.87% | 1.10 | 0.74 |

The tier split tests whether 3-of-3 conviction justifies the §10 HIGH sizing differential (2.0% vs 0.5% per trade). If the high-tier hit rate is materially higher than medium, sizing escalation is earned; if not, the spec keeps both at STANDARD for v1.

## Sector Breakdown

| Sector | Trades | Wins | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `Capital Goods` | 511 | 228 | 283 | +0.64% | 44.6% |
| `Healthcare` | 326 | 130 | 196 | -0.15% | 39.9% |
| `Automobile and Auto Components` | 266 | 112 | 154 | +0.32% | 42.1% |
| `Chemicals` | 229 | 84 | 145 | -0.53% | 36.7% |
| `Fast Moving Consumer Goods` | 178 | 71 | 107 | -0.17% | 39.9% |
| `Information Technology` | 177 | 67 | 110 | -0.32% | 37.9% |
| `Consumer Services` | 160 | 57 | 103 | -0.57% | 35.6% |
| `Metals & Mining` | 159 | 75 | 84 | +0.80% | 47.2% |
| `Oil Gas & Consumable Fuels` | 144 | 55 | 89 | -0.39% | 38.2% |
| `Power` | 136 | 55 | 81 | +0.06% | 40.4% |
| `Consumer Durables` | 123 | 49 | 74 | -0.08% | 39.8% |
| `Services` | 109 | 39 | 70 | -0.74% | 35.8% |
| `Realty` | 97 | 40 | 57 | -0.22% | 41.2% |
| `Construction` | 95 | 32 | 63 | -1.40% | 33.7% |
| `Construction Materials` | 86 | 26 | 60 | -1.70% | 30.2% |
| `Telecommunication` | 70 | 31 | 39 | +0.49% | 44.3% |
| `Textiles` | 49 | 20 | 29 | -0.14% | 40.8% |
| `Diversified` | 34 | 13 | 21 | -0.61% | 38.2% |
| `Media Entertainment & Publication` | 31 | 9 | 22 | -2.04% | 29.0% |

## Marketcap-tier Breakdown

| Tier | Trades | Wins (positive return) | Losses | Avg Return | Hit Rate |
|---|---:|---:|---:|---:|---:|
| `MEGA (≥ ₹1 lakh Cr)` | 621 | 270 | 351 | +0.33% | 43.5% |
| `LARGE (₹50k–1 lakh Cr)` | 473 | 194 | 279 | +0.02% | 41.0% |
| `MID (₹15k–50k Cr)` | 1200 | 478 | 722 | -0.12% | 39.8% |
| `SMALL-MID (₹5k–15k Cr)` | 686 | 251 | 435 | -0.55% | 36.6% |

## Diagnostic Extras

- Median trade return: -6.00%
- Best trade: +9.00%
- Worst trade: -6.00%
- Expectancy per trade: -0.10%

## Drift Envelope (bootstrap, 1000 resamples · seed 20260503)

| Metric | Mean | 1σ | 2σ | 1σ band | 2σ band |
|---|---:|---:|---:|---|---|
| Hit rate (%) | +51.76 | 0.91 | 1.81 | [+50.86, +52.67] | [+49.95, +53.58] |
| Avg win (%) | +8.44 | 0.06 | 0.11 | [+8.38, +8.49] | [+8.33, +8.55] |
| Avg loss (%) | -5.80 | 0.02 | 0.04 | [-5.83, -5.78] | [-5.85, -5.76] |
| Profit Factor | +0.97 | 0.04 | 0.08 | [+0.94, +1.01] | [+0.90, +1.05] |
| Sharpe (annualized) | -0.22 | 0.30 | 0.59 | [-0.51, +0.08] | [-0.81, +0.38] |
| Win/loss ratio | +1.45 | 0.01 | 0.02 | [+1.44, +1.47] | [+1.43, +1.48] |

---

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing differential (medium = STANDARD 0.5% / high = HIGH 2.0% per §10)
  is captured in the conviction-tier split table above; the blended §11 metrics
  combine both tiers without size-weighting (each trade counted once for hit-rate
  purposes).
- §13 catalyst weighting is **off** in S2.3 — that layer is validated in Phase G2
  / S2.4 forensics.
- Sec.5.10 v1 ships `sector_exclusions = []` (sector-agnostic). If the sector
  breakdown shows the v2.1 §0.5 financial-cohort drag re-emerging on the TC
  pattern, a Sec.19 candidate rule proposes the exclusion with this report's
  evidence — same discipline as the original §0.5 amendment.
- Indicator code is faithful to Pine source post-Cycles 1/2/3 (commits 20ec0f0,
  b28d402, f02abd4). Cross-validation against the parallel verifier
  (`scripts/parallel_backtest/parallel_backtest_trades.csv`) is in the
  comparison post that follows this report.
