# Path γ — orthogonality-budget diagnostic

**Phase:** Day-1 diagnostic between Phase 1 (Tier 2 broken) and Phase 2
(catalyst layer build).
**Generated:** 2026-05-03
**Sample:** 100 random (symbol, date) pairs over 2023-06 → 2026-04
**Universe:** 497 InvestQuest symbols (MCap ≥ ₹5,000 Cr · ADV ≥ ₹5 Cr)
**Seed:** 20260503

## Per-class pass-rate observations

| Class | Description | Pass-rate observed | Remaining budget | Worth building? |
|---|---|---|---|---|
| 1 | Price-pattern technicals — 3-way (RSI > 50, MACD > signal, EMA20 > EMA50) all-three-agree | **24.0%** | MEDIUM (sweet-spot range 15–30%, real discrimination) | Already built (TC, Pro-setup) |
| 2 | Company quality (Tier 2 v0) | **99.8%** | ZERO (Phase 1 confirmed) | NO — saturated by universe filter |
| 3 | Catalysts (≥ 2 active in trailing 5 days) | **0.0%** | UNKNOWN (fixture-only infra) | Conditional on Phase 2A scrapers |
| 4 | FII flow (FII_INCREASE tag count) | **0.0%** | UNKNOWN (fixture-only) | Conditional on Phase 2A |
| 5 | Sector breadth | (empirical) | HIGH (+7.2pp lift on Layer 6) | Already built |
| 6 | Market regime | Risk_On 50.8% / Caution 32.5% / Risk_Off 16.7% | HIGH (well-spread distribution) | Build alongside Adaptive Suite |

### Class 1 — discrimination is real

Per-component pass-rates: RSI > 50 = 56.0%, MACD > signal = 50.0%,
EMA20 > EMA50 = 55.0%. Each component passes ~50% (random expectation
on bull-biased Indian market). All-three-agree = 24.0% — well below
random independence (50%³ = 12.5%) but not collapsed to 100%, so the
three signals are partially correlated but still discriminating in
combination. **TC's 3-of-3 strict-AND scoring is already extracting
this class's discrimination** — explains the 55% hit-rate plateau on
TC + Sector Pulse before any further class adds.

### Class 2 — saturated, confirmed

99.8% of universe symbols pass the Tier 2 v0 5-check score. No
discrimination room. The InvestQuest universe filter (MCap ≥ ₹5K Cr +
ADV ≥ ₹5 Cr) is itself an implicit class-2 quality filter; stacking
more class-2 layers on top of an already-quality-filtered population
adds zero precision. Phase 1's empirical finding is upgraded from
"Tier 2 v0 doesn't discriminate" to a sharper rule: **same-class
filters compound less when the universe was already filtered on that
class.**

### Classes 3 & 4 — UNTESTABLE on current infrastructure

Phase D's catalyst engine is fixture-based; it ships canned
`Catalyst` records keyed on specific demonstration dates, not real
historical data. On 100 random (symbol, date) pairs the engine
returned **zero** active catalysts and **zero** FII_INCREASE tags.

This is **NOT** evidence that real catalyst coverage is low — it's
evidence that **the existing infrastructure cannot answer the
question**. Phase 2A scrapers (BSE filings, NSE shareholding, NSE
block deals, SEBI insider) are the necessary precondition for any
catalyst-layer backtest.

**γ does NOT greenlight Phase 2 on existing infrastructure.** It
also does NOT veto Phase 2 — the catalyst-layer hypothesis is still
plausible; we just can't measure it without live data.

### Class 5 — empirically validated

Layer 6 sector-breadth filter on TC 3-of-3 already produced +7.2pp
hit-rate lift in Track 3. HIGH remaining budget; existing
infrastructure (`build_tc_trace` in `run_backtest_s23` plus
`load_universe`'s sector column) supports the breadth filter
directly.

### Class 6 — well-spread, ready to build

Universe-mean-proxy regime distribution over 1,031 trading days:

| Regime | Bars | % |
|---|---:|---:|
| Risk_On | 524 | **50.8%** |
| Caution | 335 | 32.5% |
| Risk_Off | 172 | 16.7% |

No regime dominates above 85%; the 50/33/17 split has discrimination
room. Building a regime-conditional cohort gate (e.g., "only fire TC
during Risk_On / Caution, halt during Risk_Off") is plausibly
high-leverage. Earmarked for the Adaptive Strategy Suite per
`INVESTQUEST_ADAPTIVE_SUITE_HANDOFF.md`.

## Path γ checkpoint outcome

**Cannot greenlight Phase 2 on fixture-based catalyst infrastructure.**
The diagnostic confirms three things:

1. **Class 1 (technicals) is well-discriminated** by TC's existing
   3-of-3 stack — no need to add more class-1 layers.
2. **Class 2 (quality) is saturated** — Phase 1's finding generalises;
   universe pre-curation collapses class-2 lift to zero.
3. **Classes 3 + 4 (catalysts, institutional flow) are untestable**
   without live data scrapers. Phase 2A (~2 weeks) is the minimum
   work to make Phase 2's hypothesis testable.

## Operator's decision

Three paths consistent with the γ findings:

**Path β — Build Phase 2A scrapers (~2 weeks), then re-test classes 3
and 4.** Original plan. Risk: another "hypothesis broken" outcome
after the data lands. Upside: settles the question definitively, and
the scrapers themselves are useful infrastructure regardless of
catalyst-layer outcome (e.g., for the daily research feed in Sprint
3 K1.x).

**Path δ — Skip Phase 2, jump to Class 6 regime filter (~1 week).**
Build the regime-conditional cohort gate using existing Nifty/proxy
data + the existing `signals.regime.market_regime` function. Class 6
has the highest "remaining-budget × buildable-today" product among
unbuilt classes. Lower expected lift than catalysts (regime is a
binary on/off gate, not a per-symbol filter), but cheaper.

**Path ε — Pivot to a less-pre-curated universe.** The Phase 1 + γ
joint finding (universe filter saturates class-2 and likely
contributes to lower remaining budget across other classes too)
suggests testing Diamond on a broader pool — e.g., all NSE-listed
names with MCap ≥ ₹2,000 Cr and ADV ≥ ₹2 Cr. The wider net would
have more discrimination room for Tier 2 + catalysts, at the cost
of more illiquid names. Risk: signal-to-noise drops; Pro-setup G1
already documented financial-sector drag on the smaller universe.

## Recommendation

If the operator's primary goal is to validate or invalidate
catalyst-layer compounding **on the InvestQuest universe**, Path β
(scrapers first) is the right move — but commit only ~2 weeks for
Phase 2A and re-evaluate before Phase 2B (LLM classifier, also ~2
weeks).

If the operator is more time-constrained, **Path δ (regime filter)
delivers a usable Diamond-Layer-6-companion in ~1 week** without
needing live scrapers. Combined effect of regime + sector breadth
on TC's 3-of-3 scoring is testable today.

Track 2 (RPI cohort, class-4 momentum) runs in parallel either way —
its W1.1 spec is committed alongside this report.
