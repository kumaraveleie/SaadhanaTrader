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

#### M1 v0 (ships in K1)

A deterministic v0 of the sector aggregator ships ahead of the
full Phase Q module. It groups Tier-1-passing names by NSE
Industry (`sub_industry`), and for each group ≥ 5 names emits:

- `today_pct` — mean constituent intraday % change
- `rs_5d`, `rs_20d`, `rs_60d` — sector return / Nifty return
  ratios (no 252d in v0)
- `breadth_above_50dma`, `breadth_above_200dma`
- `top_stocks` — top 5 by today's % change (symbol, today %,
  5d %, phase, inst-flow score)
- `inst_flow_total`, `inst_buy_bar_count_5d`, `rank_by_inst_flow`
- `sector_phase` — placeholder `"Confirming"` with note `"Phase Q
  M1 pending"` until the full classifier lands

**Implementation:** `filter/saadhana_filter/sectors/strength.py`,
emitted under `sector_strength` on `signals/research.json`, and
rendered as the regime-ribbon strip + inline drill-down on
`/research`. Phase Q replaces the v0 with the full module above
without changing the JSON contract — additional fields (`rs_252d`,
`breadth_stage_2_pct`, `volume_sustainability_score`, `tier`) are
purely additive. Phase D's catalyst data populates the drill-
down's "Triggers" section (currently a placeholder) once the
catalyst engine ships.

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

---

## 7. Lifecycle classification (M2 / Phase R)

> **Internal vs user-facing labels.** The bucket names below
> (`INITIAL`, `CONFIRMED`, `LATE`, `UNKNOWN`, `PRE_BREAKOUT`,
> `FAILED`) are the **internal canonical keys** used in §17 ledger,
> CR-008, and `filter/saadhana_filter/scan/research.py`. The
> user-facing equivalents — rendered everywhere on the public site
> via `trader/app/lib/labels.ts::LIFECYCLE_DISPLAY` — are:
>
> | Internal key | User label | Tone |
> |---|---|---|
> | `INITIAL` | **Breakout** | bullish |
> | `CONFIRMED` | **Trending** | info |
> | `LATE` | **Extended** | warning |
> | `UNKNOWN` | **Sideways** | muted |
>
> Translate **only** at the UI boundary; never rename the canonical
> keys (the §17 ledger is append-only and the keys are part of the
> historical record).

The full M2 lifecycle classifier uses **six markers** to place each
candidate's current breakout into one of four buckets (`PRE_BREAKOUT`,
`INITIAL`, `CONFIRMED`, `LATE`, plus a `FAILED` rollback state).
Each marker contributes directly to one or more buckets. A bucket
fires when its required markers all agree; ties resolve toward the
later bucket (more conservative — a `CONFIRMED` candidate flagged by
two `LATE` markers is classified `LATE`).

| # | Marker | Threshold | Tells us |
|---|---|---|---|
| 1 | `bars_since_pivot_break` | < 5 → `INITIAL` candidate; 5–20 → `CONFIRMED`; > 60 → `LATE` candidate | Where in the move the breakout sits — fresh, mid-cycle, or late |
| 2 | `dist_from_50dma_pct` | < 5% → `INITIAL`; 5–15% → `CONFIRMED`; > 15% → `LATE` | Distance from the rising 50-DMA — still anchored vs over-extended |
| 3 | `rsi_14` | 55–70 → `INITIAL`/`CONFIRMED`; > 80 → hard `LATE` flag | Momentum band — constructive vs exhausted |
| 4 | `bb_width_over_30b_median` | < 1.0× → consolidation (potentially `PRE_BREAKOUT`); 1.0–1.8× → healthy expansion (`CONFIRMED`); > 2.0× combined with `bars_since_pivot_break < 5` → blow-off `LATE` | Volatility regime — quiet pre-move, healthy expansion, or climax |
| 5 | `inst_flow_score_30b` | > 5 → accumulation continuing (`INITIAL`/`CONFIRMED`); ≤ 0 → distribution (`LATE` or `FAILED`) | Institutional footprint quality |
| 6 | `pct_above_recent_pivot_low` | 3–8% above prior pivot low → `CONFIRMED`; > 25% → `LATE`; back below → `FAILED` | Trend integrity vs vertical extension vs reversal |

**Bucket fire rules** (M2 design):

- **`PRE_BREAKOUT`** — markers (1) [no pivot break yet], (4) [BB width
  < 1.0× median, consolidation], (5) [inst flow ≥ 0]. Marker (3) RSI
  must be 50–60 (rising but not yet momentum band). Surfaces
  candidates whose Pro-Setup score is 10–12 in tight bases — the M3
  multi-year-base detector consumes this bucket as input.
- **`INITIAL`** — markers (1) bars-since-break < 5, (2) close < 5%
  above 50-DMA, (3) RSI 55–70, (5) inst flow > 0. Fresh strength;
  paired with CR-008 to define **ELITE** conviction tier.
- **`CONFIRMED`** — markers (1) bars-since-break 5–20, (2) close
  5–15% above 50-DMA, (3) RSI 60–75, (5) inst flow > 0. Trend
  running but not yet stretched.
- **`LATE`** — any of:
  - marker (3) RSI > 80
  - marker (2) > 15% above 50-DMA
  - marker (4) > 2× BB width AND marker (1) bars-since-break < 5
    (blow-off climax)
  - marker (6) > 25% above recent pivot low
- **`FAILED`** — marker (6) close drops back below the breakout
  level within 10 bars of the break. Triggers the §8.2 stop-loss
  re-evaluation.

Bucket transitions are tracked over time — a stock entering
`CONFIRMED` then deteriorating to `LATE` is a different signal from
a stock entering `LATE` directly (the former is exhaustion of an
otherwise-good trade; the latter is a chase).

### 7.1 K1 v1 placeholder

The /research page in K1 ships a **simplified 4-bucket classifier**
(`INITIAL` / `CONFIRMED` / `LATE` / `UNKNOWN`) implemented in
`filter/saadhana_filter/scan/research.py::_classify_lifecycle`. This
is intentionally less rigorous than the M2 design above:

- Uses only markers 1, 2, 3, 4, 5 (skips marker 6 pivot-low context)
- No `PRE_BREAKOUT` bucket — those candidates resolve to `UNKNOWN`
  at K1 since the M3 multi-year-base detector that consumes them
  doesn't exist yet
- No `FAILED` bucket — exit-side classification is not surfaced on
  /research at K1
- Thresholds are blunter (RSI 55–70 instead of 60–75 etc.)

The K1 classifier is good enough to power the `/research` Strength
Despite Weakness panel (the user can already act on "is this stock
fresh, running, or extended?"). When M2 ships, the
`research.py::_classify_lifecycle` function gets replaced by the
full 6-marker version; the bucket names stay identical so the UI
side does not need to change.

### 7.2 Validation strategy for M2

Per `§4` validation philosophy of this document — different from
the §11 statistical gate. M2's classifier validates against the
historical reference setups in `§2`:

- For each multi-bagger window, the M2 classifier should label the
  inflection bar (or the bar after) as `INITIAL`, NOT `LATE`.
- For exhaustion bars (the local top of each PSU/Defense run), M2
  should label them `LATE`, NOT `CONFIRMED`.
- Bucket transitions during the multi-bagger run should be
  monotonic-with-noise (`PRE_BREAKOUT` → `INITIAL` → `CONFIRMED` →
  optional `LATE` near the top → `FAILED` at trend break), not
  oscillating.

If the classifier mislabels the inflection bar in any of the four
reference setups, M2 doesn't ship — re-tune thresholds first.

### 7.5 User-facing phase guidance

The /research page surfaces phase information through three layers
so casual readers and serious users get the right depth at the right
time. The action rules below are the canonical wording — the UI
implementation in `trader/app/lib/labels.ts::PHASE_HELP`,
`trader/app/components/phase-tooltip.tsx`,
`trader/app/components/phase-drawer.tsx`, and
`trader/app/about/phases/page.tsx` mirrors this verbatim. If this
section changes, the four files must be updated in the same commit.

**Layer 1 — hover tooltip (per phase tag)**

Every phase tag in any /research table or sector drill-down wraps in
a `<PhaseTooltip>` that, on hover, surfaces:

| Phase | Summary | Action lines |
|---|---|---|
| **Breakout** (`INITIAL`) | Fresh strength · just emerged from base | ► Best entry: highest reward, slightly lower hit rate <br/> ► Stop: tight (close to base support) |
| **Trending** (`CONFIRMED`) | Trend running · momentum confirmed | ► Solid entry: higher hit rate, less upside left <br/> ► Stop: ATR-based, slightly wider than Breakout |
| **Extended** (`LATE`) | Stretched · stop chasing | ► Avoid new entries — late-stage exhaustion risk <br/> ► Hold-only: tighten stops if already in position |
| **Sideways** (`UNKNOWN`) | No clear direction yet | ► Wait for the stock to declare — Breakout or breakdown <br/> ► No system signal in this phase |

Each tooltip ends with a "Learn more →" link routing to Layer 2 (or
Layer 3 if the user is already on a non-/research page).

**Layer 2 — `?` icon → side drawer**

A small `?` icon (14px, `t.text2`) sits at two places on /research:
next to the PHASE column header in each panel table, and next to the
distribution chip strip header. Click → right-side slide-in drawer
(~480px), titled "How to read phases", containing the comparison
table, practical rules ("Pattern Match + Breakout → take it"), the
phase-progression narrative, and a CTA routing to Layer 3.

The drawer is keyboard-accessible (ESC closes), backdrop click
closes, and is layout-agnostic (renders above any /research panel).

**Layer 3 — `/about/phases` reference page**

Same content as the drawer, expanded with the underlying phase
classifier rules (per §7 thresholds), a worked example using the
day's distribution, and the "phase vs Pro-Setup score" distinction.
Linked from: the drawer CTA, the Layer 1 tooltip "Learn more →",
the footer disclaimer area, and the /about page main content.

**Practical rule (canonical, do not soften without spec edit):**

- Pattern Match + **Breakout** → take it (best risk/reward)
- Pattern Match + **Trending** → take it (highest probability)
- Pattern Match + **Extended** → the system shouldn't fire here
  (the §5 `not_extended` condition prevents it)
- No match but stock shows **Trending** on /research → information,
  not action

**Coming in Phase F (CR-008):** when conviction-tier sizing ships,
phase will drive risk allocation directly — Breakout 1.5%, Trending
0.5%, Extended downgraded to WATCH. Until then, all matches are
STANDARD-sized and phase is informational on /research only.
