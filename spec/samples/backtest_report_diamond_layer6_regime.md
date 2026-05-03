# Diamond Layer 6 (Sec.0.7.5 Class 6 regime filter) — backtest validation

**Phase:** Path δ — cheapest empirical test of Diamond stacking on
InvestQuest before committing to the ~3-week Phase 2A scraper build.
**Generated:** 2026-05-03
**Replay window:** 2023-04-03 → 2026-05-02 (3 years)
**Universe:** 396–497 symbols (InvestQuest, MCap ≥ ₹5,000 Cr · ADV ≥ ₹5 Cr)
**Regime classifier source:** universe-mean-of-top-50 proxy (no `^NSEI`
in local cache); §12 `market_regime()` wrapper at
`filter/saadhana_filter/quality/regime_filter.py`.

## Per-cohort results

### TC + Sector Pulse (Layer 1+6 baseline) — N=1083

Entry-date regime distribution: **Risk_On 86.2% / Risk_Off 7.9% / Caution 5.8%**.

| Layer | N | Hit% | Win% | PF | Sharpe | ₹1L 3yr final | Annual% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 baseline | 1083 | 56.6% | 47.6% | 1.35 | +2.29 | ₹93,841 | −2.10% |
| + regime ∈ {Risk_On, Caution} (default) | 997 | **57.0%** | 48.1% | 1.38 | +2.47 | ₹91,776 | **−2.82%** |
| + regime == Risk_On only (strict) | 934 | **57.9%** | 49.0% | **1.43** | **+2.75** | ₹85,817 | **−4.97%** |

**Hit-rate lift @ strict: +1.3pp.** Sharpe also lifts +0.46. **But cash return DROPS** (−6.16% → −14.18%). Strict variant cuts 14% of trades and the cuts disproportionately remove winning trades during transitional regimes.

### TC combined (control, no sector breadth) — N=2980

Entry-date regime distribution: Risk_On 66.1% / Risk_Off 19.1% / Caution 14.9%.

| Layer | N | Hit% | PF | Sharpe | ₹1L 3yr final | Annual% |
|---|---:|---:|---:|---:|---:|---:|
| 0 baseline | 2980 | 51.7% | 0.97 | −0.23 | ₹93,641 | −2.17% |
| + regime default | 2412 | 52.0% | 0.99 | −0.09 | ₹81,687 | −6.52% |
| + regime strict | 1969 | **53.2%** | 1.07 | **+0.55** | ₹95,035 | **−1.68%** |

**Hit-rate lift @ strict: +1.5pp.** Cash return **improves** (−6.36% → −1.68%) on the control because removing Risk_Off + Caution entries cuts more losers than winners on the broader trade pool. Sharpe flips from −0.23 to +0.55.

### Pro-setup 13/13 (G1 generalisation) — N=129

Entry-date regime distribution: **Risk_On 98.4% / Risk_Off 0.8% / Caution 0.8%**.

| Layer | N | Hit% | PF | Sharpe | ₹1L 3yr final |
|---|---:|---:|---:|---:|---:|
| 0 baseline | 129 | 34.1% | 1.29 | +1.65 | ₹96,717 |
| + regime default | 128 | 34.4% | 1.28 | +1.62 | ₹96,590 |
| + regime strict | 127 | 34.6% | 1.30 | +1.72 | ₹97,364 |

**Hit-rate lift @ strict: +0.5pp.** Pro-setup's 13-condition strict-AND already filters out Risk_Off bars implicitly (its `weekly_hh_hl` + `above_50_and_200_ema` + `stage_2` gates rarely fire in Risk_Off regimes). The regime filter has near-zero work to do.

## Path δ checkpoint per operator's criteria

| Cohort | Best lift | Branch |
|---|---:|---|
| TC + Sector Pulse | +1.3pp | **mild compound** |
| TC combined (control) | +1.5pp | **mild compound** |
| Pro-setup 13/13 | +0.5pp | broken (already saturated) |

**Verdict: 1–3pp lift on TC variants → "Diamond stacking mild-compound on InvestQuest; proceed with measured expectations."**

## The cash-returns paradox — important nuance

Hit rate up, cash return down on TC + Sector Pulse:

| Metric | Layer 0 | + strict regime | Δ |
|---|---:|---:|---:|
| Hit rate (% reaching +5%) | 56.6% | 57.9% | **+1.3pp ✓** |
| Sharpe (annualized) | +2.29 | +2.75 | **+0.46 ✓** |
| ₹1L 3yr cash return | −6.16% | −14.18% | **−8.02pp ✗** |
| Trades taken (post 5-concurrent cap) | 189 | 169 | −20 |

**The 14% trade cut removes some big winners.** TC + Sector Pulse's Risk_Off and Caution entries (149 trades) include both losers and meaningful winners; cutting all of them removes too many compounding opportunities. **Strict regime filter trades absolute return for higher precision** — useful when shadow-mode-monitoring signal quality, harmful when chasing real-money returns.

This is a class-6-specific finding, not a Diamond-stack-wide finding: the regime filter is **selective by date** (cuts entire trading days), so it doesn't preserve the chronological structure of the original trade pool. Other Diamond layers (Tier 2 quality by symbol, catalysts by event) cut by characteristic, not by date — they preserve more compounding structure.

**Implication for Phase 2A:** if catalyst layer also cuts by-date (e.g., "no FII tags in this week"), expect a similar paradox. If it cuts by-symbol-event (e.g., "this stock has a fresh catalyst"), the structure should preserve better.

## Per-class summary so far (Phase 1 + Path δ data)

| Class | Path | Result |
|---|---|---|
| 1 — price-pattern technicals | Built (TC) | TC's 3-of-3 already extracts class-1 budget |
| 2 — company quality | Phase 1 | 0pp lift; saturated by universe filter |
| 3 — catalysts | Phase 2A pending | UNTESTABLE on fixtures |
| 4 — FII flow | Phase 2A pending | UNTESTABLE on fixtures |
| 5 — sector breadth | Layer 6 (Track 3) | +7.2pp lift on TC 3-of-3 |
| 6 — regime | **Path δ (this report)** | **+1.3pp on TC + Sector Pulse; cash-paradox** |

The strongest empirical compound found on InvestQuest is class 5 (sector breadth, +7.2pp). Class 6 contributes another +1.3pp on top — combined ~8.5pp lift over plain TC. The remaining classes (3 + 4) require Phase 2A scrapers to test.

## Recommendation per the operator's branch

**Proceed to Path β (Phase 2A scrapers, ~2 weeks)** with measured expectations:

- Class 6's mild lift is consistent with the universe-pre-curation discount; classes 3 and 4 may compound similarly mildly (1–3pp each) rather than the 5–10pp budget originally hoped.
- Phase 2A scrapers are valuable infrastructure regardless — daily research feed, ledger catalyst snapshots — even if class-3 lift turns out marginal on backtest.
- **Don't promise full Diamond.** Cumulative best case across classes 5+6+(3 if it lifts 2pp)+(4 if it lifts 1pp) = ~12pp lift over plain TC, putting hit rate around 64% — Silver-tier territory, not the original 96% Diamond target.

Operator decides whether the marginal lift justifies the 2-week scraper investment.

## Files

- `filter/saadhana_filter/quality/regime_filter.py` — wrapper module
- `filter/tests/test_regime_filter.py` — 8 unit tests (all pass)
- `scripts/diamond_layer6_regime_backtest.py` — this report's runner
