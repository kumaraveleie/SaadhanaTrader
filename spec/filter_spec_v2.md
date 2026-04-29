# Saadhana Stock Filtering System — Specification v2.0

**Status:** Locked · **Owner:** Kumaravel · **Date:** 2026-04-29
**Supersedes:** filter_spec_v1.md
**Goal:** Surface Indian cash-equity long candidates with high probability
of ≥5% upside and low probability of significant drawdown, with explicit
exit rules and a self-improving forensics loop. Decisions are rule-based
— no human emotion in the loop.

---

## 0. Reading order

This is the contract. Every line of code must trace to a section here.

The system is built in three independently shippable layers:

1. **Filter brain** (Python) — indicators, signals, forensics, ledger
2. **Trader app** (Next.js on Vercel) — public/personal UI, scanner, charts
3. **Pine mirrors** (TradingView) — chart-side visualization that follows the same rules

The spec covers all three because they share definitions. Drift between
layers is caught by parity tests in CI, not by reviewers months later.

---

## 1. What this system promises (and does not)

### Promises
- **Deterministic rules.** Every BUY, HOLD, SELL, WAIT signal is computed
  from objective inputs. Same input → same output, every time.
- **Pre-validated probabilities.** Backtest-gated before live use. Hit rate,
  drawdown, days-to-target are published numbers, not assumptions.
- **Honest exits.** Every BUY ships with a paired stop, profit-target ladder,
  and trend-break exit. No position lacks a plan.
- **Forensics built-in.** Every signal is logged with full feature snapshot.
  Every loss is analyzed. Rule changes pass shadow-mode + human approval.

### Does not promise
- Stocks that go up in every market regime. A Nifty crash drags everything.
- Zero losers. Target hit rate ~60–70%; individual trades will lose.
- Intraday signals. v1 is end-of-day on daily bars only.
- F&O / options / leverage. Cash equity, long-only, v1.

---

## 2. Universe

- **Default scope:** Nifty 50 (low noise, high liquidity)
- **Optional scope:** Nifty 500 (more candidates, more noise)
- **Hard exclusions** at universe-build time:
  - Median 30-day turnover < ₹5 Cr (illiquid)
  - F&O ban list on the scan date
  - SEBI surveillance: T-group, GSM stages 3+, suspended
  - ASM long-term framework

---

## 3. The four signal states

Each stock is classified into exactly one state per scan day.

| State | Meaning | Action |
|---|---|---|
| **BUY** | All entry criteria met today, not currently held | Open new position |
| **HOLD** | Currently held, no exit triggered | Stay in, monitor |
| **SELL** | Currently held, exit triggered | Close (full or partial per ladder) |
| **WAIT** | Not held, entry criteria not met | Do nothing |

**Public-version label mapping** (see §21): BUY → "High Pattern Match",
HOLD → "Pattern Holding", SELL → "Pattern Broken", WAIT → "—".

---

## 4. Tier 1 fundamental gate (quarterly)

Refreshed once per 90 days. A stock must pass **ALL** of the following to
even enter the daily technical scan.

1. **Market cap ≥ ₹5,000 Cr** (mid-cap and above)
2. **Latest quarter EPS YoY > 0** OR **Revenue YoY > 0** (no earnings shrinkage)
3. **Promoter holding ≥ 30%** (skin in the game)
4. **Promoter pledge < 25%** (no margin-call risk)
5. **Debt-to-Equity ≤ 1.5** (excludes banks/NBFCs from this rule — they have own gate)
6. **Not in F&O ban / SEBI surveillance / T-group**

Stocks failing any of these are excluded from the scan universe until
the next quarterly refresh, regardless of how good their chart looks.

### Bank/NBFC alternate gate
If `sector ∈ {BANK, NBFC, FINANCIAL_SERVICES}`:
- Replace D/E rule with **GNPA < 4%** AND **CAR ≥ 12%**.

---

## 5. BUY entry logic — 13 technical conditions

> **Why these 13 (and not the Pine ones).** These 13 conditions are the
> system-grade signal gates — chosen for their measurable risk math
> (ATR stop, R/R ≥ 2:1, target distance) which is required by §10
> position sizing and §11 backtest validation. The Pine script in
> `pine/` is a complementary chart-side visual checklist using a
> different (chart-eyeball) 13-condition set inherited from Mashrani
> Pro-Setups; the two systems intentionally do **not** 1:1 mirror each
> other. Drift between Python and TypeScript is enforced by §16 parity
> tests; Pine is no longer in scope for that.

A stock receives a BUY signal **only if ALL 13 conditions are true** on
the most recent closed daily bar AND the Tier 1 gate is passed AND market
regime allows BUYs (§12).

The snake_case key in backticks after each condition is the **canonical
identifier** — used as the Python `cond_<key>` function name, the
TypeScript mirror name, and the field name in the §17 ledger schema.
Renaming a key is a spec change.

### 5.1 Trend qualification
1. **Stage 2** (Weinstein) — `stage_2` — close > 30W SMA AND 30W SMA rising
2. **Price > 50 EMA AND Price > 200 EMA** — `above_50_and_200_ema`
3. **5-EMA > 20-EMA AND 5-EMA rising bar-over-bar** — `5ema_above_20ema_rising`
4. **Higher highs / higher lows** structure on weekly chart, last 8 weeks — `weekly_hh_hl`

### 5.2 Momentum qualification
5. **RSI(14) between 50 and 70** — `rsi_50_70` (relaxable to 50–75 if forensics shows benefit)
6. **MACD histogram > 0 AND rising** — `macd_hist_rising` (momentum building, not peaking)

### 5.3 Volume / accumulation qualification
7. **Institutional Buy or Heavy Buy** in the last 5 trading days — `institutional_flow`
   (RVOL ≥ 1.5x with up-bar at least once; institutional = RVOL ≥ 2.5x)
8. **30-bar Inst. Flow Score > 0** — `inst_flow_score` (net accumulation, not distribution)
   - Score = (count of inst./heavy BUY bars) − (count of inst./heavy SELL bars)

### 5.4 Risk qualification
9. **Distance to entry stop ≤ 3%** — `distance_to_stop_le_3pct`
   (stop = max of 20-EMA OR 5-bar low − ATR×0.5)
10. **ATR-projected upside to nearest resistance ≥ 5%** — `atr_upside_ge_5pct`
    - Resistance = recent pivot high or 52-week high
    - Projection = current ATR(14) × expected days-to-target (default 20)
11. **Risk-Reward ratio ≥ 2:1** — `rr_ge_2` (target distance ≥ 2× stop distance)

### 5.5 Not-extended qualification
12. **NOT within 2% of 52-week high** unless fresh breakout from a base ≥ 5 weeks — `not_extended`
13. **Bollinger Band Width > 30-bar median** OR price has just broken out
    of consolidation in last 3 bars — `bb_width_alive`

**Pro-Setup Score** = sum of conditions met, range 0..13. Score 13 = BUY
candidate. Score 10–12 = WATCH (displayed but not actionable). <10 = WAIT.

---

## 6. Downside Resistance Score (transparency metric)

Computed for every stock, displayed alongside signal. Range 0–100.
Higher = lower historical drawdown probability.

| Component | Weight | Logic |
|---|---|---|
| Stage 2 strength | 20 | (close − 30W SMA) / 30W SMA, normalized to [0,1] |
| Distance from 52W low | 15 | (close − 52WL) / 52WL, capped at 100% |
| ATR-tightness | 15 | 1 − ATR(14) / close (lower vol = higher score) |
| Inst. Flow Score (90 bars) | 20 | Cumulative institutional accumulation |
| EMA stack quality | 15 | 5 > 20 > 50 > 200 in clean order |
| Drawdown depth (recent) | 15 | 1 − max DD(90 bars) |

**Descriptive metric, not a guarantee.** Backtest validates correlation with
realized drawdown. If correlation < 0.4, weights are re-tuned before ship.

---

## 7. Profit target ladder

3-tier exit. Honors "minimum 5% profit and wait for more."

| Tier | Trigger | Action |
|---|---|---|
| T1 | +5% from entry | Sell 33% · trail remainder · move stop to entry (breakeven) |
| T2 | +10% from entry | Sell 33% more · trail remaining 33% with 20-EMA |
| T3 | Trail remainder | Exit when close < 20-EMA |

T1 locks in the floor. T2/T3 capture upside if the trend extends.

---

## 8. SELL exit logic

A held position generates SELL if **ANY** of these triggers:

### 8.1 Hard stops (immediate full close)
- **Stop hit:** close ≤ entry stop (computed at entry, never widened)
- **Catastrophic break:** close < 50-EMA on RVOL ≥ 2.0x (heavy down volume)

### 8.2 Profit-tier triggers (partial close)
- **T1 hit:** sell 33%, move stop to breakeven
- **T2 hit:** sell 33% more, trail final 33% with 20-EMA
- **T3 trail break:** close < 20-EMA on remainder, exit final 33%

### 8.3 Trend-deterioration triggers (full close)
- **Stage shift:** Stage 2 → Stage 3 (close < 30W SMA, SMA flat/falling)
- **Score collapse:** Pro-Setup Score ≤ 5 for 2 consecutive days
- **Institutional SELL** signal on 2 of last 5 days
- **RSI > 80 with bearish divergence** on price-vs-RSI

### 8.4 Time-based (optional)
- **No-progress exit:** position between −2% and +2% for 30 days with
  declining score → exit, free up capital

---

## 9. HOLD vs WAIT

- **HOLD:** position open, none of §8 triggers fire
- **WAIT:** no position, BUY criteria not all met today

---

## 10. Position sizing (risk-first)

Per Saadhana risk doctrine:
- **Per-trade risk:** 0.5% of portfolio (loss if stop hit) — STANDARD tier
- **HIGH conviction tier (§14):** 1.5% of portfolio
- **Position size formula:** `qty = (risk_pct × portfolio) / (entry − stop)`
- **Concurrent positions:** max 10 (≤ 5% portfolio at risk simultaneously)
- **Drawdown halt:** if portfolio down 10% peak-to-trough → no new BUYs
  until recovery to within 5% of peak

---

## 11. Backtest validation gate (must pass before live)

Replay 3 years (2023-04 to 2026-04) on Nifty 500. For every BUY signal
generated, measure these. **Must pass to ship.**

| Metric | Target | Action if missed |
|---|---|---|
| Hit rate (% reaching +5%) | ≥ 60% | Tighten entry rules |
| Average days to T1 | ≤ 25 | Add momentum filter |
| Average win | ≥ +8% | OK if hit rate compensates |
| Average loss | ≤ −2.5% | Tighten stop logic |
| Max consecutive losses | ≤ 5 | Add regime filter |
| Win/loss ratio | ≥ 2.0 | Re-tune ladder |
| Sharpe (annualized) | ≥ 1.5 | Re-evaluate edge |

If any **must-pass** metric fails, system does NOT ship. Rules are revised,
validator re-runs, decision is documented.

**Forward-only discipline:** validator uses ONLY data available on the scan
date — no lookahead. Catalyst data uses point-in-time freezes from §17.

---

## 12. Market regime filter (top-level gate)

A long-only system cannot make money in a true bear market. The regime
filter detects hostile conditions and **suspends new BUYs** until conditions
improve. Three states, evaluated daily on Nifty 50 close:

| Regime | Condition | Effect on system |
|---|---|---|
| **Risk-On** | Nifty > 50-DMA AND Nifty > 200-DMA AND 50-DMA rising | BUYs enabled, normal sizing |
| **Caution** | Nifty between 50-DMA and 200-DMA | BUYs require Score 13/13 + HIGH conviction; no STANDARD tier |
| **Risk-Off** | Nifty < 200-DMA | BUYs disabled. Existing HOLDs reviewed with tighter stops (close < 20-EMA = exit) |

This is what "any market" honestly means: in good markets we trade freely;
in bad markets we step aside. Capital preservation > FOMO.

---

## 13. Catalyst engine

For every technically-qualified candidate, search for a catalyst that
explains the institutional flow. If a real catalyst is found, conviction
multiplies. If no catalyst is found despite high RVOL, treat as suspicious
(possible manipulation OR pre-public leak — wait for confirmation).

### 13.1 Catalyst taxonomy

Each candidate gets 0..N catalyst tags. Each tag carries a `freshness_days`
field — older catalysts decay in weight (see §14).

| Tag | Source | Freshness window |
|---|---|---|
| `earnings_beat` | BSE/NSE corporate filings, EPS vs estimate | 30 days |
| `guidance_raised` | Management commentary in concall transcripts | 30 days |
| `buyback` | Board-approved corporate action | 60 days |
| `dividend_hike` | Corporate action filing | 60 days |
| `bonus_split` | Corporate action filing | 60 days |
| `management_change` | Filings + news (CEO/CFO/board change) | 90 days |
| `order_win` | Material disclosure | 30 days |
| `capacity_expansion` | Material disclosure | 90 days |
| `m_and_a` | Material disclosure | 60 days |
| `fii_increase` | Quarterly shareholding pattern delta | 90 days |
| `dii_increase` | Quarterly shareholding pattern delta | 90 days |
| `promoter_buying` | SEBI insider trading disclosures | 60 days |
| `block_deal_buy` | NSE/BSE block-deal daily data | 14 days |
| `policy_tailwind` | PIB releases, budget docs, sector mapping | 60 days |
| `sector_momentum` | Sector index outperforming Nifty by ≥3% in 20 days | 20 days |
| `unknown` | None of the above identifiable | — (cautionary flag) |

### 13.2 Catalyst sources by phase

**Phase D (deterministic, MVP):** filings, shareholding pattern, block deals,
insider trades, sector momentum. Covers ~70% of catalysts. NO LLM.

**Phase E (LLM-classified):** news headlines via free RSS / API. Small
local model (Qwen 7B / Phi-4) classifies each headline into the taxonomy
with confidence score. Headlines with confidence < 0.75 are dropped.

### 13.3 Catalyst card (per signal)

```jsonc
{
  "catalyst_tags": [
    {
      "type": "earnings_beat",
      "date": "2026-04-25",
      "freshness_days": 4,
      "magnitude_pct": 12,
      "source": "BSE filing",
      "source_url": "https://..."
    },
    {
      "type": "fii_increase",
      "date": "2026-03-31",
      "freshness_days": 28,
      "qoq_delta_pct": 1.4,
      "source": "NSE shareholding pattern Q4 FY26"
    }
  ],
  "narrative": "Q4 EPS beat by 12% on margin expansion; FII stake up 1.4% QoQ to 24.8%."
}
```

The `narrative` is a 1-line summary generated by the LLM Explainer (Phase E)
or templated text (Phase D fallback).

---

## 14. Convergence scoring + sizing tiers

The conviction tier multiplexes technical + catalyst + quality:

```
Conviction = ProSetupScore × CatalystWeight × QualityFactor

CatalystWeight:
  0.5  No catalyst found ("unknown story")
  1.0  Older catalyst (30–90 days), partly priced in
  1.5  Fresh catalyst (≤30 days), 1 category
  2.0  Fresh catalysts in 2+ independent categories

QualityFactor (Tier 2 fundamentals, see §4.1):
  0.8  Quality Score 0–2
  1.0  Quality Score 3–4
  1.2  Quality Score 5–6
```

### 14.1 Tier 2 Quality Score (informational booster, 0..6)

Each YES adds 1 point:
- ROE > 15% (3-year average)
- ROCE > 18% (3-year average)
- Earnings CAGR > 15% (3-year)
- Free cash flow positive (last 4 quarters)
- Promoter buying in last 6 months
- FII or DII stake rising vs 4 quarters ago

### 14.2 Tier mapping → position sizing

| Conviction | Threshold | Risk per trade | Example |
|---|---|---|---|
| **HIGH** | ≥ 22 | 1.5% portfolio | Tech 13/13 + 2 fresh catalysts + Quality 5+ |
| **STANDARD** | 15–21 | 0.5% portfolio | Tech 13/13 + 1 catalyst |
| **WATCH** | 10–14 | 0% (alert only) | Catalyst exists, technical not yet 13/13 |
| **SKIP** | < 10 | 0% | Anything else |

Same risk doctrine as §10 — system *deserves* to size up only when both
forces align; *deserves* to skip when the story is missing.

---

## 15. Scanner output format

Daily JSON written to `signals/YYYY-MM-DD.json` and Vercel Postgres
`scan_results` table. Public-version columns are a subset (see §21).

```jsonc
{
  "scan_date": "2026-04-29",
  "regime": "Risk_On",
  "universe_size": 487,
  "tier1_passed": 312,
  "candidates": [
    {
      "symbol": "DIVISLAB",
      "name": "Divi's Laboratories",
      "signal": "BUY",
      "pro_setup_score": 13,
      "stage": "Stage_2",
      "rvol": 2.6,
      "inst_flow_30d": 12,
      "downside_resistance_score": 78,
      "quality_score_t2": 5,
      "catalyst_tags": [...],
      "conviction_tier": "HIGH",
      "entry_price": 6234.50,
      "stop_loss": 6075.00,
      "target_t1": 6546.23,
      "target_t2": 6858.95,
      "risk_pct": 2.56,
      "reward_pct": 5.00,
      "rr_ratio": 1.95,
      "sector": "PHARMA",
      "sector_relative_strength_20d": 1.07,
      "narrative": "Q4 EPS beat 12% + FII +1.4% QoQ. Stage 2 + RVOL 2.6x."
    }
  ]
}
```

---

## 16. Versioning + drift protocol

Spec is single source of truth. When a rule changes:
1. Update `filter_spec_v2.md` (or open `_v3.md` for major changes)
2. Update Python `saadhana_filter/indicators/` + `signals/`
3. Update Pine `pine/saadhana_pro_setups.pine`
4. Update Next.js `trader/app/lib/indicators/`
5. Run pytest → ALL parity tests must pass
6. Re-run backtest validator → must still pass §11 gate
7. Tag spec version in next scanner output (`spec_version: "2.0"`)

CI catches drift between Pine, Python, and TypeScript via parity tests
on a fixed set of golden tickers (5 stocks × 200 bars).

---

## 17. Signal Ledger schema

The non-negotiable foundation of the learning loop. Every BUY ever issued
is frozen with full feature snapshot, immutably. Append-only, like a
financial ledger.

```jsonc
{
  "signal_id": "sig_2026_04_29_DIVISLAB_001",
  "spec_version": "2.0",
  "symbol": "DIVISLAB",
  "signal_date": "2026-04-29",
  "signal_price": 6234.50,
  "regime": "Risk_On",
  "sector": "PHARMA",

  // §5 — technical (keys match §5 canonical names exactly)
  "pro_setup_score": 13,
  "conditions": {
    "stage_2":                   {"met": true, "value": {"close": 6234.50, "sma_30w": 5612}},
    "above_50_and_200_ema":      {"met": true, "value": {"ema_50": 5832, "ema_200": 5410}},
    "5ema_above_20ema_rising":   {"met": true, "value": {"ema_5": 6189, "ema_20": 6051}},
    "weekly_hh_hl":              {"met": true},
    "rsi_50_70":                 {"met": true, "value": 64.2},
    "macd_hist_rising":          {"met": true, "value": 18.4},
    "institutional_flow":        {"met": true, "value": {"last_5d_buy_bars": 2, "max_rvol": 2.6}},
    "inst_flow_score":           {"met": true, "value": 12},
    "distance_to_stop_le_3pct":  {"met": true, "value": 0.0256},
    "atr_upside_ge_5pct":        {"met": true, "value": 0.0500},
    "rr_ge_2":                   {"met": true, "value": 2.05},
    "not_extended":              {"met": true, "value": {"dist_52wh_pct": -3.2, "fresh_breakout": false}},
    "bb_width_alive":            {"met": true, "value": {"bbw_pct": 5.8, "median_30b": 4.2}}
  },
  "stage": "Stage_2",
  "rvol_today": 2.6,
  "inst_flow_30d": 12,
  "downside_resistance_score": 78,

  // §13 — catalyst
  "catalyst_tags": [...],
  "catalyst_count_fresh": 2,
  "catalyst_narrative": "Q4 EPS beat 12% + FII +1.4% QoQ.",

  // §4 — fundamentals snapshot
  "quality_score_t2": 5,
  "promoter_holding_pct": 51.2,
  "promoter_pledge_pct": 0,
  "roe_3y_avg": 23.4,
  "earnings_cagr_3y": 18.2,
  "debt_to_equity": 0.12,

  // §14 — conviction
  "catalyst_weight": 2.0,
  "quality_factor": 1.2,
  "conviction": 31.2,
  "conviction_tier": "HIGH",

  // Risk + targets at signal time
  "calculated_stop": 6075.00,
  "target_t1": 6546.23,
  "target_t2": 6858.95,
  "risk_pct": 2.56,
  "reward_pct": 5.00,
  "rr_ratio": 1.95,

  // Indicators raw snapshot (for forensics)
  "indicators_snapshot": {
    "rsi_14": 64.2,
    "atr_14": 142.3,
    "bb_width_pct": 5.8,
    "macd_hist": 18.4,
    "ema_5": 6189, "ema_20": 6051, "ema_50": 5832, "ema_200": 5410,
    "sma_30w": 5612,
    "high_52w": 6440, "low_52w": 4373
  },

  // Outcome — populated by §18 outcome tracker after resolution
  "outcome": null,
  "outcome_date": null,
  "outcome_return_pct": null,
  "outcome_days": null,
  "outcome_max_favorable_excursion": null,
  "outcome_max_adverse_excursion": null
}
```

**Outcome enums:** `WIN_T1`, `WIN_T2`, `WIN_T3`, `STOP_HIT`,
`CATASTROPHIC_BREAK`, `STAGE_SHIFT_EXIT`, `SCORE_COLLAPSE_EXIT`,
`INST_SELL_EXIT`, `RSI_DIVERGENCE_EXIT`, `TIME_EXIT`, `STILL_OPEN`.

---

## 18. Forensics engine

Runs weekly (Sunday). Reads closed signals from §17, generates the
weekly review, and proposes rule changes.

### 18.1 Inputs
- Closed signals from past 7 days (immediate review)
- Closed signals from past 90 days (rolling pattern detection)

### 18.2 Pipeline
1. **Outcome aggregation** — win/loss counts, win rate trend, P&L
2. **Loss clustering** — k-means on feature vectors of losing signals
3. **Hypothesis generation** — for each cluster of size ≥ 3, identify
   common features. LLM writes the hypothesis narrative.
4. **Rule proposal** — synthesize hypothesis into a candidate rule
5. **Out-of-sample preview** — replay last 90 days with proposed rule;
   measure improvement in hit rate and reduction in losers
6. **Per-rule contribution analysis** — Δ win rate when rule fires vs not,
   for every existing rule. Identifies dead-weight rules.
7. **Weekly review report** — markdown artifact saved to
   `reviews/YYYY-WW.md` and rendered on `/learning` page

### 18.3 Weekly review output

See `samples/weekly_review_example.md` for the canonical format. Key
sections: outcomes, win/loss breakdown, pattern detected, proposed rule
addition, per-rule contribution, regime commentary.

### 18.4 Disciplines
- **Sample size:** patterns from N < 5 closed signals are reported as
  "preliminary"; N < 3 are not actioned
- **No retroactive feature changes:** the ledger is append-only
- **Variance honesty:** scattered losses across regimes are flagged as
  "irreducible variance" and not actioned with new rules

---

## 19. Rule promotion pipeline

Proposed rules from §18 do not affect live signals immediately. They run
in **shadow mode** for ≥30 days, generating phantom signals tracked
alongside real ones.

### 19.1 States

| State | Meaning | Effect on live signals |
|---|---|---|
| `proposed` | Just proposed by forensics | None |
| `shadow` | Running silently for ≥30 days | None — phantom only |
| `pending_approval` | Shadow period complete, evidence collected | None |
| `live` | Approved by user, in production | Modifies signal generation |
| `retired` | Removed for poor performance | None |

### 19.2 Promotion gate (shadow → pending_approval)

A shadow rule is promoted to pending_approval if:
- ≥ 30 days in shadow
- ≥ 20 phantom decisions made
- Hit rate improvement ≥ 5 percentage points OR loss reduction ≥ 15%
- No degradation of Sharpe or max consecutive losses

### 19.3 User approval (pending_approval → live)

User reviews on `/learning` page, sees:
- Rule definition
- Shadow performance vs current rules
- Out-of-sample validation
- Recommended action

User clicks ✓ or ✗. ✓ → live (audited), ✗ → retired (audited).
**No silent rule mutation.** All changes are user-approved.

### 19.4 Trust score (per rule)

```
trust_score(R) = (win_rate_when_R_fires − win_rate_when_R_quiet) ×
                 N_observations ×
                 consistency_across_regimes
```

Rules with negative trust_score for 90+ days are flagged for retirement.
Rules with high trust_score get heavier weight in conviction calculation.

### 19.5 Known external candidate rules (parked)

The Pine chart-side checklist (`pine/saadhana_pro_setups.pine`,
`pine/saadhana_volume_v2.pine`) computes signals that are deliberately
**not** part of the §5 v2 system rules but are obvious candidates for
forensics to propose via shadow mode (§19.1) once the system is live
and has 90+ days of closed signals. These are **parked, not adopted**
— the engine may surface them as `proposed` rules; user approval (§19.3)
remains the only path to `live`.

| Candidate | Pine source | Rationale to consider |
|---|---|---|
| `dcr_ge_70` | Daily Closing Range ≥ 70% | Strong intra-day demand on the entry bar |
| `wcr_ge_70` | Weekly Closing Range ≥ 70% | Weekly close near weekly high — institutional buying tape |
| `ud_ratio_ge_1` | 21-bar up/down day ratio ≥ 1 | Net up-day pressure independent of volume |
| `ichimoku_cloud_bull` | Senkou A > Senkou B | Trend confirmation orthogonal to EMA stack |
| `near_ath` | Within 10% of all-time high | Long-term breakout candidates |
| `pvs_up` | Vol > 2.5× avg with close in top 30% of bar | Institutional accumulation tighter than §5.3 |

If any of these reach the §19.2 promotion gate (≥ 30 days shadow,
≥ 20 phantom decisions, hit-rate Δ ≥ 5pp), the user-approval flow in
§19.3 elevates them to `live`. Until then they exist only here, in this
list, as a known menu of options the engine may offer — not as latent
spec text waiting to be turned on.

---

## 20. Compute architecture

### 20.1 Topology

```
┌──────────────────────────────────────────────────────┐
│ FRONTEND (Vercel free)                                │
│ Next.js · NextAuth · API routes (read-only) · charts │
└─────────────────────┬────────────────────────────────┘
                      ↓ reads
┌──────────────────────────────────────────────────────┐
│ STORAGE (Vercel Postgres free 256 MB)                 │
│ scan_results · signals · outcomes · rule_versions     │
│ users · sessions · paper_trades                       │
└─────────────────────┬────────────────────────────────┘
                      ↑ writes nightly
┌──────────────────────────────────────────────────────┐
│ COMPUTE (GitHub Actions cron)                         │
│ 17:00 IST  pull OHLCV (yfinance + bhavcopy)           │
│ 17:30 IST  run 13 conditions across universe          │
│ 18:00 IST  catalyst engine (deterministic)            │
│ 18:30 IST  signal generation + ledger write           │
│ Sun 09:00  forensics weekly review + shadow eval      │
│ Quarterly  fundamentals refresh                       │
└──────────────────────────────────────────────────────┘
                      +
┌──────────────────────────────────────────────────────┐
│ LLM (Hugging Face Space free, Phase E only)           │
│ Qwen 7B / Phi-4 — news classification + narrative gen │
└──────────────────────────────────────────────────────┘
                      +
┌──────────────────────────────────────────────────────┐
│ PERSONAL (your laptop, optional)                      │
│ Local Streamlit · full BUY/SELL signals · paper book  │
│ Reads same Postgres                                   │
└──────────────────────────────────────────────────────┘
```

### 20.2 Cost: ₹0/month at all expected scales

Free tier limits:
- Vercel: 100 GB bandwidth, unlimited builds
- Vercel Postgres: 256 MB (years of data)
- GitHub Actions: 2000 min/month private (need ~150)
- Hugging Face Spaces: 16 GB CPU
- Yahoo Finance: free for personal use, rate-limited for high traffic

### 20.3 Data sources

| Source | Use | Cost |
|---|---|---|
| yfinance | EOD OHLCV, last 5 years | free |
| NSE bhavcopy | Cross-validation, official EOD | free |
| BSE/NSE corporate filings | Catalyst — material disclosures, results | free, structured |
| NSE shareholding pattern | Catalyst — FII/DII/promoter deltas | free, quarterly |
| NSE block/bulk deals | Catalyst — institutional deals | free, daily |
| SEBI insider trading | Catalyst — promoter buying | free |
| Screener.in | Tier 1 fundamental gate | free, manual quarterly export |
| Sector indices (NSE) | Sector momentum, regime | free |
| Google News RSS / NewsAPI free | Phase E catalyst classification | free tier |

---

## 21. Public/Personal split + compliance labeling

Two views on the same codebase, gated by auth.

### 21.1 Saadhana Trader (PUBLIC)

- **Audience:** registered users (free, login-walled)
- **Framing:** research and pattern-detection tool, NOT investment advice
- **Labeling map:**

| Internal | Public-version label |
|---|---|
| BUY | "High Pattern Match" |
| HOLD | "Pattern Holding" |
| SELL | "Pattern Broken" |
| Stop-loss | "Technical risk level" |
| Profit target | "Technical projection" |
| Position size | (not displayed) |
| Recommendation | "Pattern detection" |
| "We recommend..." | "The system has identified..." |

- **Required disclaimers** (every page):
  - Banner: "Saadhana Trader is a research and pattern-detection tool.
    Information only. Not investment advice. We are not registered with
    SEBI as an Investment Advisor or Research Analyst. Do your own
    research and consult a SEBI-registered advisor before making
    investment decisions."
  - Footer: short disclaimer on every page
  - ToS: explicit indemnity, "no advice," past-performance language
  - Data badge: "EOD · 15-min delayed where applicable"

### 21.2 Saadhana Personal (PRIVATE)

- **Audience:** owner only (later: explicitly invited friends)
- **Framing:** full trading system, no language softening
- **Labels:** internal (BUY/HOLD/SELL/stop/target)
- **Features public lacks:**
  - Position sizing display
  - Paper-trade portfolio
  - Approval queue for forensics-proposed rules
  - Trust-score dashboard
- **Access control:** Vercel auth + role-based routing; or local-only
  Streamlit dashboard

### 21.3 Pre-launch legal step

Before public launch: ₹15–25k consultation with Indian securities law
firm. Obtain written opinion that the public framing complies with
research-analyst safe harbor. File the letter.

---

## 22. What v2 deliberately excludes (parked for v3+)

- Sector rotation overlay (beyond regime filter)
- Earnings/event calendar avoidance window
- Intraday timing within the day
- Short-side signals
- Options overlay (covered calls on HOLDs, protective puts)
- Pair trading
- Real-time data (live tick) — v2 is EOD only
- Mobile-native app (web-responsive only)
- Multi-user paper trading leaderboard
- Telegram bot integration (proposed for v2.1)

---

## 23. Build phases

| Phase | Scope | Definition of done |
|---|---|---|
| **A** | Spec v2 (THIS DOC) + project scaffold + CLAUDE.md | Repo created, README, scaffold committed |
| **B** | Python data loader + 13 technical conditions + tests | All conditions pass golden-fixture tests |
| **C** | Python signal engine (BUY/HOLD/SELL/WAIT) + Tier 1 gate | End-to-end scan on Nifty 50 produces JSON |
| **D** | Catalyst engine v1 (deterministic sources) | Catalyst tags appear in scan output |
| **E** | LLM news classification on HF Space | News headlines tagged with confidence |
| **F** | Convergence scoring + sizing tiers | Conviction tier in output, sizing computed |
| **G1** | Backtest validator — **technical-only** | Replay 3 years on Nifty 500 using §5 v2 13 conditions only (no catalyst, no conviction tier, standard 0.5% sizing); §11 metrics reported. **Diagnostic gate** — confirms the technical layer alone has predictive value before catalyst / conviction sit on top of it. |
| **G2** | Backtest validator — **full system** (official GO/NO-GO) | Same 3-year replay with §13 catalyst weighting + §14 conviction tiers + §10 risk-tier sizing. **Capital deployment gate per spec §11.** |
| **H** | Signal Ledger + Outcome Tracker | Every BUY logged, outcomes resolved nightly |
| **I** | Forensics engine + weekly review | First weekly review generated |
| **J** | Rule promotion pipeline + shadow mode | Proposed rule runs in shadow, evidence accrues |
| **K** | Next.js Trader app on Vercel + auth | Public scanner + stock detail live |
| **L** | /learning page + approval workflow | Personal-only forensics dashboard live |
| **M** | GitHub Actions cron + Vercel Postgres wired | Full nightly pipeline runs unattended |
| **N** | Pine-side overlay of v2 risk-leg metrics (optional) | ATR stop, R/R targets, target-T1/T2 levels render as chart annotations on the Pine `saadhana_pro_setups` script; Pine condition checklist stays unchanged (Mashrani 13, see §5 note) |

Each phase is independently shippable. **Phase G2 is the official
go/no-go gate** for live (paper) trading per §11. Phase G1 is a
diagnostic split: it validates the §5 v2 technical layer in isolation
(no catalyst, no conviction tier) so we know whether the catalyst
work in phases D/E and the conviction tiers in phase F are improving
a system that already has edge, or papering over a broken core. If
G1 fails its §11 thresholds, tighten §5 rules before doing any of D/E/F.

Phase N is **optional** — the system is fully functional without Pine
parity since §5 v2 is the canonical gate; the overlay only exists to
make on-chart eyeballing match the Python-computed risk levels.

---

## 24. Glossary

- **OHLCV:** Open, High, Low, Close, Volume
- **EMA / SMA:** Exponential / Simple Moving Average
- **RVOL:** Relative volume (today / 50-bar average)
- **ATR:** Average True Range
- **BB:** Bollinger Band
- **Stage 2:** Weinstein Stage Analysis — confirmed uptrend
- **PVS:** Price Volume Spurt
- **52WH / 52WL:** 52-week high / low
- **Inst. Flow Score:** Net institutional accumulation over N bars
- **DCR / WCR:** Daily / Weekly Closing Range
- **U/D ratio:** Up-volume / Down-volume ratio
- **Tier 1 / Tier 2:** Fundamental quality gate / booster (§4, §14.1)
- **Convergence:** Technical + Catalyst + Quality alignment (§14)
- **Shadow mode:** Rule runs silently, no live effect (§19)
- **Trust score:** Per-rule predictive contribution (§19.4)

---

**End of spec v2.0** — this document is the contract. Every line of code
written for the filter must trace back to a section here. Drift from spec
is caught by parity tests and forensics — not by reviewers months later.
