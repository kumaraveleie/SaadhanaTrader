# Saadhana Backtest — Phase G1 (technical-only)

**Phase:** G1 — diagnostic gate
**Generated:** 2026-04-29
**Replay window:** 2023-03-31 → 2026-04-29
**Universe:** 50 symbols
**Per-trade risk:** 0.50% (§10 standard tier)
**Catalyst layer:** off (Phase G2)
**Conviction tiers:** off (Phase G2)

---

## §11 Backtest Validation

**OVERALL: FAIL** — tighten §5 rules before adding any more layers.

| Metric | Target | Observed | Verdict |
|---|---|---|---|
| Hit rate (% reaching +5%) | ≥ 60% | 38.9% | FAIL |
| Avg days to T1 | ≤ 25 | 10.9 | PASS |
| Avg win | ≥ +8% | +5.91% | FAIL |
| Avg loss | ≤ −2.5% | -3.15% | FAIL |
| Max consecutive losses | ≤ 5 | 3 | PASS |
| Win/loss ratio | ≥ 2.0 | 1.88 | FAIL |
| Profit Factor | ≥ 1.8 | 1.50 | FAIL |
| Sharpe (annualized) | ≥ 1.5 | 1.71 | PASS |

## Trade Outcome Distribution

| Outcome | Count |
|---|---|
| `STOP_HIT` | 8 |
| `T3_TRAIL_BREAK` | 4 |
| `INST_SELL_EXIT` | 2 |
| `SCORE_COLLAPSE_EXIT` | 2 |
| `STAGE_SHIFT_EXIT` | 2 |

**Total trades:** 18
**Closed:** 18 (8 wins, 10 losses)
**Still open at cutoff:** 0

## Diagnostic Extras

- Median trade return: -1.25%
- Best trade: +8.85%
- Worst trade: -6.09%
- Expectancy per trade: +0.88%

## Notes

- Forward-only data discipline: each scan day sees only bars ≤ that day.
- Position sizing fixed at the §10 STANDARD tier (0.5%); no §14 conviction escalation.
- §13 catalyst weighting is **off** in Phase G1 — that layer is validated in Phase G2.
- Tier 1 fundamental gate (§4) is treated as a static input for the replay window.
  Quarterly fundamentals refresh is a Phase G2 concern.
