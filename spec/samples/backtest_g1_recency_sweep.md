# Phase G1 — Recency-Threshold Parameter Sweep

**Generated:** 2026-04-30
**Universe:** Nifty 500 industrial-only (`fundamentals_nifty500_excl_fin.parquet`)
**Replay window:** 2023-04-01 → 2026-04-30
**Stop distance:** 3% (spec §5.4 #9 unchanged)
**Sweep variable:** `RECENT_STRENGTH_LOOKBACK_DAYS` in `cond_recent_strength_not_extended`
**Other v2.1 amendments:** financial-sector exclusion already applied via fundamentals.

---

## Sweep results

| Threshold (days) | N | Hit rate | Avg win | Avg loss | Max consec L | W/L ratio | PF | Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A1 (v2.0)** | 95 | 41.1% | +6.19% | -2.86% | 7 | 2.16 | 1.95 | 2.81 |
| 60 | 11 | 27.3% | +5.82% | -1.98% | 4 | 2.93 | 1.67 | 2.66 |
| 90 | 16 | 43.8% | +5.94% | -2.29% | 4 | 2.59 | 2.59 | 4.98 |
| 120 | 26 | 38.5% | +6.26% | -3.09% | 4 | 2.02 | 1.74 | 2.02 |
| 150 | 28 | 35.7% | +5.38% | -3.09% | 4 | 1.74 | 1.74 | 1.99 |
| 180 | 37 | 45.9% | +5.92% | -2.80% | 4 | 2.11 | 2.77 | 3.89 |

## §11 gate reference

| Metric | Threshold |
|---|---|
| Hit rate | ≥ 60% |
| Avg win | ≥ +8% |
| Avg loss | ≤ -2.5% |
| Max consecutive losses | ≤ 5 |
| Win/loss ratio | ≥ 2.0 |
| Profit Factor | ≥ 1.8 |
| Sharpe (annualized) | ≥ 1.5 |

## Notes

- A1 baseline shown for reference; it has no recency leg (the v2.0
  `not_extended` was effectively infinite-day recency).
- The 60-day row is identical to G1d (N=11). The 60-day row may
  differ slightly from G1d if any cache changes occurred between
  runs — check date stamps if so.
- Cache is warm for all 5 sweep iterations (no yfinance pulls).
- Recommendation column intentionally blank — selection criteria
  applied by the human reviewer.