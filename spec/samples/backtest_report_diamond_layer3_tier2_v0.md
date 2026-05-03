# Diamond Layer 3 (Sec.6.4 Tier 2 v0) — backtest validation

**Phase:** Phase 1 Step 1.4 of the Diamond stack build-out (per
`INVESTQUEST_DIAMOND_LAYERS_HANDOFF.md`).
**Generated:** 2026-05-03
**Replay window:** 2023-04-03 → 2026-05-02 (3 years)
**Universe:** 396–497 symbols (InvestQuest, MCap ≥ ₹5,000 Cr · ADV ≥ ₹5 Cr)

## §11 outcome — Tier 2 v0 hit-rate lift

Three cohorts tested, each with three layers (baseline; +Tier 2 ≥ 4 / 5;
+Tier 2 = 5 / 5).

### TC + Sector Pulse (Diamond Layer 6 baseline) — N=1083

| Layer | N | Hit% | Win% | PF | Sharpe | ₹1L 3yr final | Annual% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 baseline | 1083 | 56.6% | 47.6% | 1.35 | +2.29 | ₹93,841 | −2.10% |
| + Tier 2 v0 ≥ 4 / 5 (Layer 3) | 1083 | 56.6% | 47.6% | 1.35 | +2.29 | ₹93,841 | −2.10% |
| + Tier 2 v0 = 5 / 5 (strictest) | 1081 | 56.5% | 47.5% | 1.35 | +2.27 | ₹95,897 | −1.39% |

**Hit-rate lift @ ≥4 / 5: +0.0pp.** Hypothesis broken (< 1pp threshold).

### TC combined (no breadth) — N=2980

| Layer | N | Hit% | Win% | PF | Sharpe | ₹1L 3yr final | Annual% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 baseline | 2980 | 51.7% | 40.0% | 0.97 | −0.23 | ₹93,641 | −2.17% |
| + Tier 2 v0 ≥ 4 / 5 | 2980 | 51.7% | 40.0% | 0.97 | −0.23 | ₹93,641 | −2.17% |
| + Tier 2 v0 = 5 / 5 | 2975 | 51.7% | 40.1% | 0.97 | −0.23 | ₹91,473 | −2.93% |

**Hit-rate lift @ ≥4 / 5: +0.0pp.** Hypothesis broken.

### Pro-setup 13/13 (G1 InvestQuest baseline) — N=129

| Layer | N | Hit% | Win% | PF | Sharpe | ₹1L 3yr final | Annual% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 baseline | 129 | 34.1% | 38.8% | 1.29 | +1.65 | ₹96,717 | −1.11% |
| + Tier 2 v0 ≥ 4 / 5 | 129 | 34.1% | 38.8% | 1.29 | +1.65 | ₹96,717 | −1.11% |
| + Tier 2 v0 = 5 / 5 | 129 | 34.1% | 38.8% | 1.29 | +1.65 | ₹96,717 | −1.11% |

**Hit-rate lift: +0.0pp on both thresholds.** Hypothesis broken.

## Why the v0 score doesn't discriminate

Tier 2 v0 score distribution across the 497-symbol InvestQuest universe:

| Score | Symbols | % of universe |
|---|---:|---:|
| 5 / 5 | 496 | **99.8%** |
| 4 / 5 | 1 | 0.2% |
| 0–3 | 0 | 0.0% |

**496 of 497 symbols pass all five v0 checks.** The "filter" is a no-op
because the InvestQuest universe (MCap ≥ ₹5,000 Cr + ADV ≥ ₹5 Cr) has
already pre-selected high-quality large/mid-cap names — within that
population, the Tier-1-derived checks (eps_yoy > 0, revenue_yoy > 0,
promoter_holding ≥ 40%, promoter_pledge = 0%, D/E ≤ 1.0) are
near-uniformly true.

This is a **discrimination problem**, not a code problem. Even raising
the threshold to "5 / 5 only" filters out just 1–5 symbols out of
2980 trades, producing an immeasurable lift.

## What canonical Tier 2 (§14.1) might still find

The §14.1 canonical 6-check version uses richer signals that DO
discriminate within high-quality universes:

| Check | Why it discriminates |
|---|---|
| ROE > 15% (3y avg) | Half the InvestQuest names sustain it; the other half are mediocre compounders |
| ROCE > 18% (3y avg) | Same logic, capital-efficiency cut |
| Earnings CAGR > 15% (3y) | Separates real growth from cyclical earnings |
| FCF positive (last 4q) | Cuts asset-heavy / debt-fuelled growth |
| Promoter buying (6m) | Insider conviction signal — rare and meaningful |
| FII / DII stake rising QoQ | Smart-money flow signal — orthogonal to chart pattern |

These columns are **not in the local fundamentals snapshot.** Sourcing
them requires:

1. Screener.in scraping (free; ROE/ROCE/CAGR/FCF history) — ~2 weeks
   of data infra work
2. NSE shareholding XBRL parser (free; promoter buying + FII/DII
   stake history) — ~1 week of data infra
3. Tijori or similar paid API (alternative source for the same data)

Until one of these lands, **canonical Tier 2 cannot be tested.**

## Phase 1 checkpoint outcome

Per the operator's checkpoint criteria:
- ≥ 4pp lift → PROCEED to Phase 2
- 1–3pp lift → STOP, post results, operator decides
- **< 1pp lift → STOP, hypothesis broken** ← we are here

**Recommendation:** Don't proceed to Phase 2 on Tier 2 v0 evidence
alone. Two paths forward, operator decides:

1. **Build canonical-Tier-2 data infrastructure first** (Screener.in
   scrape ≈ 2 weeks; then re-test). Real risk: the InvestQuest
   universe is *already* curated, so even canonical Tier 2 lift may
   be smaller than expected (15–25pp on a generic Indian universe
   would compress to 5–10pp on InvestQuest).
2. **Skip Tier 2 entirely, jump to Phase 2** (catalyst layer). News-
   event signals (information class 3) are more orthogonal to TC's
   class-1 components than Tier 2 (class 2) is to TC's pre-filtered
   universe — the lift potential is plausibly higher.

The information-orthogonality principle (Sec.0.7.5) explains the v0
result: Tier 2 v0 nominally lives in class 2 (company quality), but
the InvestQuest universe filter already collapses much of that
class's discriminating power. **Within a pre-curated universe,
quality filters compound less than they would on a broader pool.**

## Files

- `filter/saadhana_filter/quality/tier2.py` — module (v0 + canonical)
- `filter/tests/test_tier2.py` — 20 tests (all pass)
- `scripts/diamond_layer3_tier2_backtest.py` — this report's runner
- `data/fundamentals_investquest_universe.parquet` — input snapshot
  (Tier 1 columns only)
