# Saadhana — Thinking Engine

**Status:** Vision document, post-MVP roadmap
**Owner:** Kumaravel
**Date:** 2026-04-30
**Companion to:** [`spec/filter_spec_v2_1.md`](filter_spec_v2_1.md) §22

---

## 1. Why this is the edge

The Pro-Setup engine (`filter_spec_v2_1.md` §5) is **table stakes**.
Many systems do similar things — Mashrani-style 13-condition stacks,
TradingView Pine scripts, retail screeners on Chartink — and produce
roughly the same numbers (40–50% hit rate, PF 1.5–2.0, Sharpe 1.5–2.5).
That's a working swing system. It is **not a moat.**

The Thinking Engine adds two structural capabilities Pro-Setup
cannot, and which together explain why institutional desks
out-perform retail across decades:

1. **Multi-year base recognition** — the 5–10× bagger setups don't
   look like Pro-Setup signals when they trigger. They look like
   stocks that have been written off for years and just printed an
   unremarkable +3% day above a 200-week resistance level. Pro-Setup
   misses them because the conditions (RSI 50–70, 5/20-EMA rising
   bar-over-bar, MACD histogram > 0 AND rising) only fire well after
   the institutional repositioning is already underway. The Thinking
   Engine catches them at the inflection.

2. **Multi-attribute thesis synthesis** — sector strength + macro
   tailwind + fundamental turnaround + technical breakout + catalyst
   confirmation, all aligning on the *same* name in the *same* week,
   is the historical signature of multi-baggers. Pro-Setup checks one
   axis (technicals) and Catalyst (Phase D) adds a second
   (idiosyncratic news). Two axes is not "convergence". The Thinking
   Engine measures across **five or six independent axes** and only
   triggers when ≥ 4 align.

Pro-Setup is the screener. Thinking Engine is the portfolio-manager
brain on top.

---

## 2. Reference setups (historical multi-baggers)

Each setup below is the kind of trade the Thinking Engine targets.
The pattern repeats: multi-year underperformance → narrative trigger
→ sector breadth confirms → fundamental inflection → technical
breakout → 5–10× over 18–36 months.

### 2.1 PSU re-rating 2021

- **Window:** Apr 2020 trough → Q4 2022 peak.
- **Setup:** Public-sector undertakings (BEL, HAL, Concor, IRCTC,
  Coal India, BHEL) had spent the prior decade flat or down on
  privatisation overhang and capex-cycle absence. Most traded at
  P/E < 8 and dividend yield > 5%.
- **Catalysts (multiple, layered):**
  - Govt's **Atmanirbhar Bharat** push from mid-2020 (defense
    indigenisation, capex revival)
  - Multiple multi-year defense orders awarded H2-2020 onwards
  - Coal-India dividend restoration; PSU bank recap
  - Sectoral re-rating narrative shift in financial press
- **Returns:** BEL ~6×, HAL ~5×, IRCTC ~4×, Concor ~2.5× over
  18–24 months. The Pro-Setup engine would have caught these
  at the *second* leg (after the first 50–70%); the Thinking
  Engine targets entry at the breakout above the multi-year base.

### 2.2 Defense rally 2022–23

- **Window:** Q1 2022 → Q4 2023.
- **Setup:** Sub-cluster of the PSU theme but with cleaner sector
  thesis. Mazagon Dock, Bharat Dynamics, BEL led.
- **Catalysts:**
  - Russia / Ukraine conflict (Feb 2022) → global defense capex
    expectation
  - India's defense exports reaching record highs
  - Multiple ₹10,000+ Cr submarine / aircraft / missile orders
- **Returns:** Mazagon Dock 8–10× over 24 months, Bharat Dynamics
  5–7×, BEL 3–4× extending the 2021 leg.

### 2.3 Pharma COVID 2020

- **Window:** Mar 2020 → Q4 2020.
- **Setup:** Indian generics had been in a multi-year derating from
  USFDA observations and pricing pressure. Divi's, Dr Reddy's, Sun
  Pharma, Aurobindo all sub-15 P/E.
- **Catalysts:**
  - COVID-19 pandemic → global API supply concern
  - Chinese API capacity uncertainty → Indian generics demand spike
  - HCQ / favipiravir / vaccine adjuvant narrative
  - Q4 FY20 / Q1 FY21 earnings beats across the sector
- **Returns:** Divi's ~3×, Aurobindo ~3×, Sun Pharma ~1.8× over 9–12
  months. Faster cycle than the PSU re-rating (single catalyst
  cluster vs multi-year structural).

### 2.4 IT 2017–19 re-rating

- **Window:** Late 2016 → mid-2019.
- **Setup:** TCS, Infosys, Wipro had been flat 2014–16 on US-tariff
  rhetoric and digital-transition margin worry. Mid-tier (LTI,
  Mphasis, Mindtree) similarly flat.
- **Catalysts:**
  - Cloud / digital revenue inflection in deal mix
  - Buyback announcements (TCS ₹16,000 Cr, Infy ₹13,000 Cr)
  - INR weakness (60 → 70 vs USD)
  - Wage inflation easing
- **Returns:** Tier-1 names 1.5–2× over 30 months — slower-moving
  but characteristic of the larger, more-followed names. Mid-tier
  ran 3–4×.

---

## 3. Module specs (sketches)

Detailed designs come at the start of each phase. Reference
[`filter_spec_v2_1.md`](filter_spec_v2_1.md) §22 for the
operational sequencing and dependency graph.

### 3.1 M1 / Phase Q — Sector Strength Engine

Inputs: per-sector index series (NSE sub-indices), per-sector
constituent list.

Outputs (per sector, per scan day):
- `rs_5d`, `rs_20d`, `rs_60d`, `rs_252d` — relative strength vs
  Nifty 50 across multiple windows
- `breadth_above_50dma_pct`
- `breadth_above_200dma_pct`
- `breadth_stage_2_pct`
- `volume_sustainability_score` — does the sector see 1-day spikes
  or sustained accumulation?
- `tier`: one of {`lead`, `confirming`, `mature`, `fading`}

Surfaces in: the public `/research` page (`filter_spec_v2_1.md`
§21.1) renders the heatmap and the lead-tier list. Personal mode
shows the same plus tier transitions (sector flipping from
`confirming` to `lead` is itself a signal).

### 3.2 M2 / Phase R — Pattern Lifecycle Engine

For each Pro-Setup-13/13 candidate, classify the lifecycle stage
of its current breakout:
- `pre_breakout` — still consolidating below resistance, high score
  but no break yet
- `initial` — just broke out, last 1–5 bars
- `confirmed` — 6–20 bars post-break, holding above prior resistance
- `mature` — 20–60 bars post-break, late in the move
- `failed` — broke back below the breakout line within the last 10
  bars

Adds *temporal context*. A 13/13 stock in `confirmed` lifecycle is
materially higher conviction than a 13/13 stock in `initial` even
though both score the same on §5.

### 3.3 M3 / Phase S — Multi-Year Base / Turnaround Engine

The 5–10× bagger detector. Triggers when **all** of:

- Stock down ≥ 40% from prior 5-year peak OR flat (range ≤ 25%)
  for ≥ 3 years
- Last 3-month price action breaks above a 200-week SMA reclaim
  with ≥ 1.5× average volume
- Sector tier (M1) is `lead` or `confirming`
- Phase D catalyst score ≥ 1 fresh tag in `policy_tailwind`,
  `m_and_a`, `management_change`, `capacity_expansion`, or
  `earnings_beat` with magnitude ≥ 15%
- Tier 2 fundamental quality score ≥ 4 (`§14.1`)

This is a high-bar AND-gate; it's *supposed* to be rare. Expected
trigger rate: 5–15 events per decade across the Nifty 500.

### 3.4 M4 / Phase T — Thesis Score Synthesizer

Composite weighted score, range 0–100:

```
ThesisScore =
  ProSetupScore  × 4         (max 52)
  + CatalystScore × 8         (max 16, fresh+aligned catalyst)
  + SectorTier   × 3         (max 12)
  + LifecycleStage × 3       (max 12, confirmed=4, initial=2, etc.)
  + MultiYearBase × 5        (boolean × 5; max 5)
  + Fundamentals  × 1        (Tier 2 quality 0–6, max 3)
```

Drives position sizing per `§10`:
- Score 0–60: STANDARD (0.5%)
- Score 60–80: HIGH (1.5%)
- Score 80–100: **THESIS** (5%) — extreme rarity, not a routine
  tier. Activated only after the §10 drawdown halt rules + a
  manual sign-off step.

---

## 4. Validation philosophy

Different from `filter_spec_v2_1.md` §11's statistical gate.

**The math problem.** With N=5–15 events per decade, classical
hit-rate / PF / Sharpe metrics fail. Standard error on hit rate at
N=10 is ±15pp; at N=30 it's ±9pp. Neither is small enough to
distinguish a true edge from regime noise. Running a 3-year
backtest on this engine and reading the resulting Sharpe is
**fitting the test to the answer** — the sample isn't large enough
to be informative.

**What replaces statistical gating:**

1. **Thesis-quality manual review.** For each historical reference
   setup in §2, the Thinking Engine must be able to:
   - Identify the setup at the right inflection (not 6 months early
     or late)
   - Surface the same catalyst attribution a contemporaneous
     investment memo would have written
   - Flag the multi-attribute convergence with timestamps that
     match historical news reporting
2. **Paper-trade-only window.** First 12 months after each module
   ships, signals fire into the §17 ledger but no real capital is
   committed. The signal-to-trade lag is wide on multi-year setups
   anyway (entry windows are weeks, not days), so a 12-month paper
   period costs little optionality.
3. **Audit trail in this file.** Each module's go-live decision
   gets a section appended to this file with the historical
   examples it caught, the contemporaneous trades that would have
   resulted, and the human approval signature.

---

## 5. Open questions

These are explicitly unresolved. Do not implement around them
without bringing the question back for explicit resolution.

1. **How do we backtest N=10 events?** Or do we accept that we
   don't, and the §4 paper-trade window IS the validation? If we
   commit to "no backtest," what's the falsifiability test that
   replaces it?
2. **Is THESIS-grade 5% sizing defensible per §10 drawdown halt?**
   §10 says "max 10% portfolio drawdown peak-to-trough → no new
   BUYs". A single THESIS-grade stop-out at 5% sizing is half the
   drawdown budget on one trade. Either §10 needs a tier-aware
   amendment or THESIS sizing needs to drop to 2–3%.
3. **Does LLM synthesis go in M4 or stay in Phase E?** Phase E
   already classifies news catalysts via a small local model
   (Qwen 7B / Phi-4). M4 needs cross-attribute reasoning — that's
   a different prompt shape and possibly a larger model. Decide
   early; the JSON schema CR-005 reserves needs to know whether
   M4 outputs structured fields or LLM-narrative blobs.
4. **Cross-attribute "convergence" minimum threshold.** Is 4-of-6
   the right bar? 3-of-6 captures more setups but admits more
   single-catalyst noise. 5-of-6 reduces N to nearly zero. Worth
   testing on the §2 reference setups — would the canonical
   multi-baggers have triggered at 4, 3, or 5?
5. **Sector taxonomy granularity.** NSE has ~16 sub-indices.
   Sector strength on those might be too coarse for the
   multi-bagger detector — defense within industrials is the real
   driver, not industrials writ large. Does M1 need a custom
   sub-sector layer (PSU-defense, PSU-banking, PSU-industrial)
   instead of NSE's standard sub-indices?

---

**Status note.** This file is **vision-stage**, not contract-stage.
None of the modules above are operational. Phase D / F land first;
Phase Q–T are sequenced after that. CR-005 in
`spec/candidate_rules.md` is the only piece of this engine that
becomes load-bearing during the v2.1 build window — it reserves the
schema fields Phase D must emit so M1–M3 don't require migration
later.
