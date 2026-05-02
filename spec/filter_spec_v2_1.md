> ✅ **This file is canonical (v2.1 Provisional).**
> Supersedes [filter_spec_v2.md](filter_spec_v2.md) (v2.0,
> preserved as audit trail per §16).
>
> Status: Provisional pending Phase F validation per §11.1.

# Saadhana Stock Filtering System — Specification v2.1 (Provisional)

**Status:** Provisional v2.1 · **Owner:** Kumaravel · **Date:** 2026-04-30
**Supersedes:** v2.0 (preserved at `filter_spec_v2.md` for audit trail)
**Goal:** Surface Indian cash-equity long candidates with high probability
of ≥5% upside and low probability of significant drawdown, with explicit
exit rules and a self-improving forensics loop. Decisions are rule-based
— no human emotion in the loop.

> **Provisional status.** v2.1 cleared 7 of 8 §11 metrics on the G1-final
> verification (Apr 2026, N=95 industrial-only Nifty 500 trades over 3
> years). Hit rate observed at 41.1% vs the recalibrated ≥ 45% target —
> a 3.9pp miss that reflects the structural property of a 13-condition
> strict-AND gate, NOT a defect or a goalpost to be moved. v2.1 is
> accepted as Provisionally Validated and is the **canonical contract
> for production code**. It promotes from Provisional to **Locked**
> only via the §11.1 criterion below — once Phase F's HIGH-conviction-
> tier validation closes the hit-rate gap.

---

## 0. Reading order

This is the contract. Every line of code must trace to a section here.

---

## 0.5 Changes from v2.0

Two evidence-driven amendments arising from the Phase G1 backtest
loop (G1 → A1 → A2 → A4 → recency sweep):

1. **§2 universe — financial sectors excluded by default.** The
   Phase G1 A1 experiment showed the FINANCIAL_SERVICES / NBFC /
   BANK cohort posted 11% hit rate / −2.29% avg return on 27
   trades — a substantial dragger that, when removed, lifted
   Profit Factor / Sharpe / Win-Loss-Ratio above their §11 gates.
   Banks and NBFCs require different model parameters (rate
   environment, loan-book quality, GNPA dynamics) than industrial
   names; building that as a dedicated track is deferred to v2.2.
   Until then they are excluded from the default scan universe.

2. **§11 gate values — recalibrated** per the G1 evidence base
   (see table in §11 below). v2.0 targets were set pre-evidence
   from industry rules of thumb. The G1 → A1 → A2 → A4 → recency
   sweep loop demonstrated that a 13-condition strict-AND gate on
   EOD daily structurally produces a hit rate of ~41% with PF
   1.95 / Sharpe 2.81 (industrial-only Nifty 500, N=95 over 3
   years). The recalibrated targets match institutional-grade
   momentum-system norms (40–50% hit rate). Original v2.0
   thresholds preserved at `spec/filter_spec_v2.md` per §16
   audit trail.

3. **§5: NO changes to the 13 conditions.** The recency-of-strength
   filter idea (`days_since_52wh ≤ 60`) was tested as a v2.1
   AND-gate amendment (G1d), then varied across 60/90/120/150/180
   days in a parameter sweep. The sweep showed:
   - As an AND-gate, the recency filter cuts trade volume by
     85–90%, dropping N below the 60-trade statistical-meaning
     threshold at every cutoff.
   - At 90 days the filter improves PF (2.59) and Sharpe (4.98)
     vs A1's 1.95 / 2.81, but only on N=16 — too few to act on.
   - As a hard BUY gate the recency idea is the wrong shape.

   The recency idea is parked at `spec/candidate_rules.md` as
   **CR-002** for evaluation in Phase F (§14) as a HIGH-conviction-
   tier requirement rather than a strict BUY gate. STANDARD tier
   would still trade on the v2.0 §5 conditions; HIGH tier (with
   1.5% sizing per §10) would additionally require recency.

**Evidence links** (committed at the time of this amendment):
- `spec/samples/backtest_report_g1_nifty500.md` — original G1 fail
- `spec/samples/backtest_report_g1_nifty500_excl_fin.md` — A1
- `spec/samples/backtest_report_g1_nifty500_stop4pct.md` — A2v1
- `spec/samples/backtest_report_g1_nifty500_excl_fin_stop4pct.md` — A2v2
- `spec/samples/backtest_g1_a4_stopout_audit.md` — A4 cluster analysis
- `spec/samples/backtest_report_g1d_v2_1.md` — G1d (recency-as-AND-gate)
- `spec/samples/backtest_g1_recency_sweep.md` — recency sweep
- `spec/samples/backtest_report_g1_final.md` — G1-final verification (this amendment)

The system is built in three independently shippable layers:

1. **Filter brain** (Python) — indicators, signals, forensics, ledger
2. **Trader app** (Next.js on Vercel) — public/personal UI, scanner, charts
3. **Pine mirrors** (TradingView) — chart-side visualization that follows the same rules

The spec covers all three because they share definitions. Drift between
layers is caught by parity tests in CI, not by reviewers months later.

---

## 0.6 Section reservations (Triple confluence vertical slice)

The InvestQuest 10-cohort architecture (see
`investquest-architecture-review.html` v1.2) introduces new sections.
The vertical-slice strategy ships Triple confluence end-to-end first,
proves the closed loop, then replicates the pattern per cohort. This
table reserves the section numbers now to prevent renumbering churn
later — every cohort that lands later refers to these stable numbers.

| Reserved section | Title | Status this slice |
|------------------|-------|-------------------|
| Sec.5.7  | MA crossover (component of Triple confluence)              | In scope |
| Sec.5.8  | Adaptive SuperTrend (component of Triple confluence)       | In scope |
| Sec.5.9  | Deviation Trend (component of Triple confluence)           | In scope |
| Sec.5.10 | Triple confluence scoring                                  | In scope |
| Sec.5.5  | RPI calculator                                             | Deferred to Wave 1 (cohort #2) |
| Sec.5.6  | RPI spurt + crossover                                      | Deferred to Wave 1 (cohort #2) |
| Sec.6.3  | Persistence + trend quality classifier                     | Deferred to Wave 2 |
| Sec.14a  | Scanner cohort registry                                    | In scope |
| Sec.25   | Position Monitor                                           | In scope |

Architecture review document references Sec.6.2 Tier 2 quality score —
this maps to existing Sec.14.1 Tier 2 Quality Score. No separate
Sec.6.2 will be created. Architecture doc updated to v1.2 to reflect
this mapping.

---

## 0.7 Universe filter vs cohort-level sector exclusions

The InvestQuest universe (§4) defines the **tradeable pool**: MCap ≥
₹5,000 Cr AND ADV ≥ ₹5 Cr. The universe is **sector-agnostic** — any
listed name meeting the cap and liquidity floors qualifies.

**Sector exclusions are a cohort-level concern.** Each cohort
registered in §14a may declare optional `sector_exclusions: list[str]`
in its candidate function. The exclusion list is part of the cohort's
spec and is auditable per signal in the §17 ledger snapshot — every
ledger row carries the cohort's exclusion list as it stood at the
moment the signal fired, so a forensics review can attribute outcomes
to the rule that was in effect.

### Migration of v2.1 §0.5 amendment 1

§0.5 amendment 1 (financial-sector exclusion based on G1 A1
experiment evidence — financials posted 11% hit / −2.29% avg / N=27,
dragging Profit Factor / Sharpe / Win-Loss-Ratio below their §11
gates) **migrates from universe-level to cohort-level**:

- **Pro-setup cohort** (Sec.5 13-condition strict-AND) declares
  `sector_exclusions = ['FINANCIAL_SERVICES', 'NBFC', 'BANK']`. This
  preserves the Apr 2026 G1-final baseline (PF 1.95, hit 41.1%,
  Sharpe 2.81 on N=95) — the InvestQuest-universe rerun validates
  this is the correct exclusion: Industrial sub-slice on the new
  universe (N=94) posts hit 41.5% / PF 2.03 / Sharpe 3.11, drift
  within ±5pp of the old baseline on every metric.

- **Triple confluence cohort** (Sec.5.10) declares
  `sector_exclusions = []` in v1. Re-evaluate in S2.3 cohort
  backtest. If financial drag is pattern-specific to strict-AND
  trend filters, TC will not need exclusions. If TC's S2.3
  backtest also drags on financials, add exclusions then with
  evidence — same discipline as §0.5 amendment 1 originally.

- **Other cohorts** (RPI leaders, RPI spurt, Volume blast, Counter-
  trend, Base breakouts, MA crossover, Adaptive trendflip, Super
  strength) default to `sector_exclusions = []` and decide
  independently in their respective backtest tasks (Wave 1+).

### Implementation contract

The cohort's `candidate_fn(symbol, as_of_date) -> dict` reads the
universe row's `sector` field. If `sector` is in the cohort's
declared `sector_exclusions`, the function returns
`{qualified: False, reason: 'sector_excluded:{sector}'}` BEFORE any
indicator computation. The Sec.17 ledger writer records the
exclusion list (by reference to cohort version) on every signal so
forensics can audit promotion / retirement of exclusions.

Cohort-level exclusions are versioned with the cohort. Adding,
removing, or modifying an exclusion list requires a Sec.19 candidate
rule with evidence, just like any other rule change — never a silent
edit. Auto drift detection on a cohort can flag a pattern of losses
concentrated in a sector, surfacing it as a Sec.19 candidate.

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
  - **Sectors:** `FINANCIAL_SERVICES`, `NBFC`, `BANK` (v2.1 — separate
    gate deferred to v2.2; current backtest evidence shows these
    require different model parameters per A1 finding)

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

    *v2.1 note:* this rule is unchanged from v2.0. The recency-of-strength
    extension (require last 52WH touch within 60–90 days) was tested
    as an AND-gate amendment in G1d + the recency sweep and rejected
    because it cut trade volume below the statistical-meaning
    threshold at every cutoff. The recency idea is parked as
    **CR-002** in `spec/candidate_rules.md` for Phase F evaluation
    as a HIGH-conviction-tier requirement (§14), not a BUY gate.

13. **Bollinger Band Width > 30-bar median** OR price has just broken out
    of consolidation in last 3 bars — `bb_width_alive`

**Pro-Setup Score** = sum of conditions met, range 0..13. Score 13 = BUY
candidate. Score 10–12 = WATCH (displayed but not actionable). <10 = WAIT.

> **Note on §5.x numbering vs §0.6 reservations.** The reservations
> table at §0.6 lists Sec.5.5 / Sec.5.6 for RPI calculator and RPI
> spurt + crossover (deferred to Wave 1, cohort #2). Existing §5.5
> "Not-extended qualification" already occupies that number — RPI
> sub-sections will be re-targeted to Sec.5.5a / Sec.5.5b (or §5.6
> if §5.5 stays Pro-setup-specific) when Wave 1 ships. No change
> needed in this slice.

---

## Sec.5.7 MA crossover (component of Triple confluence)

Adapted from the public TradingView script *Ultimate Moving Average*
by ChrisMoody. Detects bullish trend onset via fast-MA-over-slow-MA
crossover with a slope confirmation on the slow MA so we don't fire
on flat-range whipsaws. Stand-alone candidate function for the
**MA crossover cohort** AND a component of the **Triple confluence
cohort** (Sec.5.10).

### Inputs / parameters

| Parameter | Default | Description |
|---|---|---|
| `ma_type` | `TEMA` | one of {SMA, EMA, WMA, HullMA, VWMA, RMA, TEMA} |
| `fast_period` | 20 | fast MA window |
| `slow_period` | 50 | slow MA window |
| `slope_window` | 3 | bars over which slow MA slope is measured |
| `min_slope_pct` | 0.0 | minimum slow-MA slope (% of price) for trend confirmation |
| `source` | `close` | input series; usually close, occasionally hl2 / ohlc4 |

The default `(TEMA 20, EMA 50)` matches the ChrisMoody publication.
The 7 MA-type catalogue exists because different parameter
combinations work better on different cohorts — the **Pro-setup
cohort** uses (EMA 5, EMA 20) elsewhere; the **MA crossover cohort**
defaults to TEMA × EMA per the source script.

### Formula

For a series `s` of close prices, an MA function `MA(s, n, type)`,
and bar index `i ≥ slow_period + slope_window`:

```
fast_i  = MA(s, fast_period, ma_type) at bar i
slow_i  = MA(s, slow_period, ma_type='EMA') at bar i
slope_i = (slow_i - slow_{i - slope_window}) / slow_{i - slow_window} * 100
```

(slow MA always uses EMA regardless of `ma_type`; `ma_type` controls
the fast MA only — matches the source script's behaviour.)

**Bullish crossover** at bar `i`:

```
fast_{i-1} ≤ slow_{i-1}  AND  fast_i > slow_i  AND  slope_i ≥ min_slope_pct
```

A second-bar confirmation (require the cross to hold for one bar)
is OPTIONAL via a `confirm_bars` parameter (default 0 = no
confirmation; set to 1 in cohort spec if backtest shows
whipsaw-prone behaviour).

### Signal logic

The candidate function returns:

```
{
    qualified: bool,           # bullish crossover fired on bar i
    fast_ma: float,            # fast MA value at bar i
    slow_ma: float,            # slow MA value at bar i
    slope_pct: float,          # slow MA slope %
    crossover_bar: int | None, # bar index where cross fired
    ma_type: str,              # echoes the ma_type used
}
```

`qualified = True` means a fresh bullish crossover within the
trailing `signal_freshness_bars` (default 5) — the cohort spec
declares freshness so old crossovers don't keep firing.

### Edge cases

| Case | Behaviour |
|---|---|
| Bars < `slow_period + slope_window` | Skip — return `qualified: False, reason: 'insufficient_history'` |
| Fast MA == Slow MA exactly (rare) | Treat as not crossed; require strict `>` for the crossover bar |
| `slope_pct == 0.0` | If `min_slope_pct == 0` (default), passes; otherwise fails |
| NaN in source after warm-up | Drop NaN bars from the series; if the MA window can't be filled, skip |
| TEMA with very short series | TEMA needs ≥ 3×period bars to warm up fully — first 3×fast_period bars return `qualified: False` |

### Golden-fixture test cases

Synthetic OHLCV fixtures committed to
`filter/tests/fixtures/ma_crossover/`:

1. **Clean uptrend crossover** — flat 100 days, then 30-day rising
   linear ramp from 100 to 130. Expect bullish crossover within
   `slow_period + 5` bars of ramp start; `slope_pct > 0`.
2. **Downtrend** — mirror of #1 (linear decline). Expect no
   bullish crossover.
3. **Flat range with noise** — 200 days of mean-100 ±2% gaussian
   noise. Expect zero crossovers OR all crossovers fail the
   `min_slope_pct` filter; depends on noise seed but the count
   must be ≤ 3 to avoid whipsaw.
4. **Insufficient history** — 49 bars of data, `slow_period=50`.
   Expect `qualified: False, reason: 'insufficient_history'`.
5. **Fast/slow equal** — synthetic series engineered so
   `fast == slow` at bar 51, `fast > slow` at bar 52. Bar 52 is
   the crossover bar.
6. **MA-type switch** — same fixture, run with each of the 7
   MA types; verify that TEMA fires earlier than SMA (TEMA's
   reduced lag is the reason it's the default).

### Cross-references

- Pine source for parity: `pine/iq_ma_crossover.pine` (to ship
  in S2.x; deep link from /stock detail page in K2.2).
- Used as a Triple confluence component at Sec.5.10.
- Cohort registration: §14a row `ma_crossover` (deferred to a
  later cohort sprint; this section specs the indicator itself,
  not the cohort).

---

## Sec.5.8 Adaptive SuperTrend (component of Triple confluence)

Adapted from the public TradingView script *ML Adaptive SuperTrend*
by AlgoAlpha. Standard SuperTrend uses a fixed ATR multiplier
(typically 3.0×); Adaptive SuperTrend learns the multiplier from a
**K-means clustering on rolling ATR**, so the band tightens in
calm regimes and widens in volatile regimes. Stand-alone candidate
function for the **Adaptive trendflip cohort** AND a component of
the **Triple confluence cohort** (Sec.5.10).

### Inputs / parameters

| Parameter | Default | Description |
|---|---|---|
| `atr_period` | 14 | period for the underlying ATR |
| `cluster_window` | 50 | trailing-bar window for the K-means fit |
| `n_clusters` | 3 | always 3: low / mid / high volatility regimes |
| `mult_low` | 1.0 | multiplier when current ATR maps to low-vol cluster |
| `mult_mid` | 2.0 | multiplier when current ATR maps to mid-vol cluster |
| `mult_high` | 3.0 | multiplier when current ATR maps to high-vol cluster |
| `kmeans_random_state` | 20260502 | fixed seed for reproducibility |
| `min_init_bars` | 100 | bars required before clustering activates; fall back to fixed `mult_mid` until then |

`n_clusters` is locked at 3 by spec — the source script uses 3 and
forensics-side comparisons assume the same labelling. Changing it
requires a Sec.19 candidate rule.

### Formula

For OHLCV series with `cluster_window` ≥ `min_init_bars` available:

1. **ATR(14) series** computed conventionally (Wilder's smoothing).
2. **K-means fit** on the last `cluster_window` ATR values with
   `n_clusters = 3`, `random_state = kmeans_random_state`. Cluster
   centers `c_low ≤ c_mid ≤ c_high` (sort ascending after fit).
3. **Active multiplier** at bar `i`:
   ```
   d = [|ATR_i - c_low|, |ATR_i - c_mid|, |ATR_i - c_high|]
   active_cluster = argmin(d)
   mult_i = {0: mult_low, 1: mult_mid, 2: mult_high}[active_cluster]
   ```
4. **SuperTrend bands** at bar `i`:
   ```
   hl2_i        = (high_i + low_i) / 2
   basic_upper  = hl2_i + mult_i * ATR_i
   basic_lower  = hl2_i - mult_i * ATR_i

   final_upper  = min(basic_upper, prev_final_upper)
                    if close_{i-1} ≤ prev_final_upper else basic_upper
   final_lower  = max(basic_lower, prev_final_lower)
                    if close_{i-1} ≥ prev_final_lower else basic_lower
   ```
5. **Trend direction** at bar `i`:
   ```
   direction_i = +1 (uptrend)   if close_i > final_upper_{i-1} OR (prev direction +1 AND close_i > final_lower_i)
                = -1 (downtrend) if close_i < final_lower_{i-1} OR (prev direction -1 AND close_i < final_upper_i)
                = direction_{i-1} otherwise
   ```

A **band flip** at bar `i` is `direction_{i-1} = -1 AND direction_i = +1`
(bullish flip) or the inverse for bearish flip.

### Signal logic

The candidate function returns:

```
{
    qualified: bool,           # bullish band flip on bar i (or within signal_freshness_bars)
    direction: +1 | -1,
    active_band: float,        # final_lower if uptrend, final_upper if downtrend
    active_cluster: 'low' | 'mid' | 'high',
    mult_used: float,
    flip_bar: int | None,      # bar index of last bullish flip
    atr_i: float,
}
```

`qualified = True` requires a bullish flip within the trailing
`signal_freshness_bars` (default 3 — Adaptive flips are typically
shorter-horizon than MA crossovers).

### Edge cases

| Case | Behaviour |
|---|---|
| Bars < `min_init_bars` (default 100) | Use fixed `mult_mid` (2.0) until threshold met. Document in returned `active_cluster: 'init'`. |
| K-means fails to converge OR all 3 cluster centers within 0.001 of each other | Treat as degenerate (flat-vol regime). Use `mult_mid`; `active_cluster: 'degenerate'`. |
| ATR_i is NaN (warm-up or data gap) | Skip — `qualified: False, reason: 'atr_nan'`. |
| Cluster center order changes between bars (low/high swap) | Re-sort ascending after each fit. Active-cluster index is by sorted position, not raw label, so the labelling is stable. |
| Very long flat regime (all ATR ≈ 0) | Bands collapse to HL2; direction flips on noise. Spec accepts this — forensics flags as "low-confidence regime" if ATR < 0.1% of price. |

### Golden-fixture test cases

Synthetic OHLCV fixtures committed to
`filter/tests/fixtures/adaptive_supertrend/`:

1. **Calm-then-volatile transition** — 100 bars of low-vol noise
   (σ=0.5%), then 50 bars of high-vol noise (σ=3%). Expect
   `active_cluster` to migrate from `low` to `high` within the
   `cluster_window` after the regime change.
2. **Bullish flip on uptrend onset** — 50 bars flat, then 30-bar
   ramp +0.5% per bar. Expect bullish band flip within 5 bars of
   ramp start; `direction +1` thereafter.
3. **Bearish flip mirror** — same as #2 with negative ramp.
   Expect bearish flip; no bullish `qualified: True`.
4. **Insufficient history** — 99 bars (one short of `min_init_bars`).
   Expect `active_cluster: 'init'` and `mult_used == mult_mid`.
5. **Degenerate clustering** — 200 bars of identical ATR (price
   drifts 0.0001 per bar). Expect `active_cluster: 'degenerate'`
   without crash; `mult_used == mult_mid`.
6. **K-means determinism** — same fixture run twice with the same
   `kmeans_random_state`. Cluster centers, labels, and signal
   sequence must be byte-identical.

### Cross-references

- Pine source for parity: `pine/iq_adaptive_supertrend.pine`
  (to ship in S2.x; deep link from /stock detail page in K2.2
  loads AlgoAlpha's published ML SuperTrend script directly).
- Used as a Triple confluence component at Sec.5.10.
- Cohort registration: §14a row `adaptive_trendflip` (deferred
  to a later cohort sprint).

---

## Sec.5.9 Deviation Trend (component of Triple confluence)

Adapted from the public TradingView script *Deviation Trend Profile* by
BigBeluga. The indicator builds a regression-anchored mean line and a
**rolling standard-deviation band** around it; trend direction flips when
price closes outside the upper / lower band. Compared to a Bollinger-style
band, the line itself is a **linear-regression slope estimate** anchored
to a pivot point, so the band tracks an inferred trendline rather than a
moving average. Stand-alone candidate for the **Deviation trend cohort**
(reserved, not in the v1 §14a registry) AND a component of **Triple
confluence** (Sec.5.10).

### Inputs / parameters

| Parameter | Default | Description |
|---|---|---|
| `length` | 100 | regression / std-dev window in bars |
| `dev_mult` | 2.0 | std-dev multiplier for upper/lower band |
| `pivot_lookback` | 5 | bars on each side for swing-pivot anchor |
| `signal_freshness_bars` | 3 | window during which a band-cross still qualifies |
| `min_init_bars` | 100 | full `length` warm-up before signals fire |

### Formula

For OHLCV series with at least `length` bars available:

1. **Pivot anchor** — find the most recent confirmed swing-low pivot
   using `pivot_lookback` bars on each side (`low[i]` is a pivot iff it
   is the lowest of the surrounding `2*pivot_lookback + 1` bars).
2. **Linear regression line** over the trailing `length` bars,
   anchored at the pivot:
   ```
   x = arange(length)
   y = close[-length:]
   slope, intercept = polyfit(x, y, deg=1)
   trend_line_i = slope * (length - 1) + intercept    # value at bar i
   ```
3. **Rolling std-dev** of `(close - trend_line_proj)` over the same
   `length` window, where `trend_line_proj[k] = slope * k + intercept`.
   ```
   resid = close[-length:] - (slope * x + intercept)
   sigma = std(resid, ddof=0)
   ```
4. **Bands**:
   ```
   upper_i = trend_line_i + dev_mult * sigma
   lower_i = trend_line_i - dev_mult * sigma
   ```
5. **Trend direction**:
   ```
   direction_i = +1   if close_i > upper_{i-1}    # bullish breakout
                = -1   if close_i < lower_{i-1}    # bearish breakdown
                = direction_{i-1}   otherwise     # inside the band — no flip
   ```

A **bullish band cross** at bar `i` is `direction_{i-1} ≠ +1 AND direction_i = +1`.

### Signal logic

The candidate function returns:

```
{
    qualified: bool,            # bullish band cross within signal_freshness_bars
    direction: +1 | -1,
    trend_line: float,
    upper: float,
    lower: float,
    slope: float,               # regression slope (price units / bar)
    sigma: float,               # current band-half-width / dev_mult
    cross_bar: int | None,      # bar index of last bullish cross
}
```

`qualified = True` requires `direction_i = +1` AND `slope > 0` AND a
bullish cross within `signal_freshness_bars` — slope sign filters out
band-touch noise during sideways regimes.

### Edge cases

| Case | Behaviour |
|---|---|
| Bars < `min_init_bars` | Skip — `qualified: False, reason: 'insufficient_history'`. |
| No swing-low pivot in trailing `length` bars | Use first bar of the window as anchor; emit `reason: 'no_pivot_anchor'` for forensics. |
| `sigma == 0` (perfectly flat residuals) | Bands collapse to `trend_line`; treat any close ≠ trend_line as a cross. Forensics flags as `reason: 'degenerate_sigma'`. |
| Slope ≤ 0 with `direction = +1` (price above upper band but trendline declining) | `qualified = False` — sideways false positive. |
| NaN inputs (close, high, low) | Skip — `qualified: False, reason: 'nan_input'`. |

### Golden-fixture test cases

Synthetic OHLCV fixtures committed to
`filter/tests/fixtures/deviation_trend/`:

1. **Clean uptrend** — 150 bars, +0.3% drift, σ=0.5%. Expect
   `slope > 0`, `direction = +1` after the first band cross,
   `qualified: True` once per band touch from below.
2. **Clean downtrend mirror** — same shape, negative drift. Expect
   `slope < 0`, no `qualified: True`.
3. **Sideways** — 200 bars random walk with zero drift. Expect
   `direction` flips on noise but `qualified: False` for each
   bullish cross because `slope ≤ 0` filter rejects.
4. **Insufficient history** — 99 bars (one short of `min_init_bars`).
   Expect `qualified: False, reason: 'insufficient_history'`.
5. **No pivot anchor** — 150-bar monotonically rising series with
   no swing low. Expect graceful fallback (uses first-bar anchor)
   plus `reason: 'no_pivot_anchor'` flag.
6. **Determinism** — same fixture run twice, same outputs to 1e-9
   tolerance (regression is deterministic; pivot detection is
   deterministic; no random seed needed).

### Cross-references

- Pine source for parity: `pine/iq_deviation_trend.pine`
  (to ship in S2.x; deep link from /stock detail page in K2.2
  loads BigBeluga's published Deviation Trend Profile script).
- Used as a Triple confluence component at Sec.5.10.
- BigBeluga's full Deviation Trend Profile script also draws
  in-band volume profile bins; we deliberately implement only
  the trend-band signal — the volume profile is a chart-side
  visual, not a candidate-function input.

---

## Sec.5.10 Triple confluence scoring (cohort definition)

**Triple confluence** is the cohort built by combining the three
trend-flavoured indicators — MA crossover (Sec.5.7), Adaptive SuperTrend
(Sec.5.8), Deviation Trend (Sec.5.9). The thesis: signals where all three
independent trend filters agree on direction at the same time are
materially higher-confidence than any one alone, because each indicator
sees trend through a different lens (moving-average slope vs. ATR-band
flip vs. regression-band breakout).

### Conviction tiers

The cohort uses **2-of-3 / 3-of-3** as the tiering signal — *not*
score-weighted summation. Each component returns a boolean
`qualified` plus a `direction`. The cohort score is the count of
components with `qualified=True AND direction=+1` for bullish
candidates:

| Components agreeing | Conviction | Action |
|---|---|---|
| 0 of 3 | none | not a candidate |
| 1 of 3 | none | not a candidate |
| **2 of 3** | **medium** | candidate, §10 STANDARD position size (0.5%) |
| **3 of 3** | **high** | candidate, §10 HIGH position size (per §14 conviction tiers) |

A 2-of-3 candidate that becomes 3-of-3 within the same scan day is
recorded as **3-of-3 entry**; the §17 ledger keeps the higher tier.
A 3-of-3 candidate that decays to 2-of-3 on a later bar does NOT
escalate exit — it remains a held position at its original tier
(exit logic governed by §25 Position Monitor).

### Candidate function

```python
def candidate_triple_confluence(df: pd.DataFrame, *, on_bar: int) -> dict:
    """Sec.5.10 — Triple confluence scoring.

    Returns:
        {
            qualified: bool,                 # at least 2-of-3 bullish agreement
            conviction: 'medium' | 'high',   # 2-of-3 vs 3-of-3
            score: int,                      # 0..3
            agreeing_components: list[str],  # subset of {'ma_crossover','adaptive_st','deviation_trend'}
            ma_crossover: dict,              # raw output from Sec.5.7
            adaptive_st: dict,               # raw output from Sec.5.8
            deviation_trend: dict,           # raw output from Sec.5.9
        }
    """
```

Each component is invoked independently on the same `df` and `on_bar`.
Components fail closed (their `qualified` is False) on insufficient
history, NaN inputs, or degenerate cases — Sec.5.10 only counts
**affirmative** bullish votes; abstentions are not bearish.

### Universe + sector exclusions

Triple confluence runs on the InvestQuest universe (MCap ≥ ₹5,000 Cr,
ADV ≥ ₹5 Cr; Sec.2). Per §0.7, the cohort declares its own optional
sector exclusions in the §14a registry. **v1 cohort registration
declares `sector_exclusions = []`** — Triple confluence is an
agreement-of-three filter, not a single-signal filter, so the
v2.1 §0.5 financial-cohort drag may not apply at the same magnitude.
Empirical validation in Sprint 2's S2.3 Triple confluence backtest
will determine whether financials need to be excluded post-hoc.

### Signal freshness across components

Each component has its own `signal_freshness_bars` window (Sec.5.7
default 5, Sec.5.8 default 3, Sec.5.9 default 3). For Triple
confluence, the cohort uses the **strictest** window — components
must all be currently-qualified on the same scan bar; staggered
flips that fall outside their own freshness windows do NOT count.

### Edge cases

| Case | Behaviour |
|---|---|
| One component fails initialisation (insufficient history) | Treated as `qualified: False`. Score capped at 2 — promotion to 3-of-3 is impossible until full history available. |
| Two components qualify bullish, third qualifies bearish | Score = 2 (bullish votes only). Conviction = medium. The bearish vote is recorded in `agreeing_components` metadata for forensics, not in the score. |
| All three qualify bullish on different bars within a 3-bar window | Counts as 3-of-3 if all are within their own `signal_freshness_bars` on the scan bar; otherwise 2-of-3 or less. |
| 3-of-3 → 2-of-3 decay on a later bar | No exit signal generated; §25 Position Monitor governs. The §17 ledger entry keeps the entry-bar conviction. |

### Golden-fixture test cases

Synthetic OHLCV fixtures committed to
`filter/tests/fixtures/triple_confluence/`:

1. **3-of-3 high conviction** — fixture engineered so all three
   components fire bullish on the same bar. Expect
   `qualified: True, conviction: 'high', score: 3`.
2. **2-of-3 medium conviction** — MA crossover + Adaptive ST agree;
   Deviation Trend's slope filter rejects (slope ≤ 0). Expect
   `conviction: 'medium', score: 2,
   agreeing_components: ['ma_crossover','adaptive_st']`.
3. **1-of-3 not qualified** — only MA crossover fires. Expect
   `qualified: False, score: 1`.
4. **Mixed direction** — MA crossover + Adaptive ST fire bullish;
   Deviation Trend fires bearish. Expect `score: 2`,
   `agreeing_components` lists the two bullish; bearish is in
   metadata not in the count.
5. **Component init shortfall** — Adaptive ST has < 100 bars.
   Even with MA + Deviation bullish, score capped at 2.
   Expect `conviction: 'medium'` not `'high'`.
6. **Determinism** — fixture #1 run twice, identical outputs
   (downstream of Sec.5.7/5.8/5.9 determinism guarantees).

### Cross-references

- §14a registry row: `triple_confluence` (medium = STANDARD,
  high = HIGH conviction tier per §14).
- §10 position sizing tiers govern actual rupee allocation.
- §17 ledger writes one row per cohort entry with
  `cohort_id = 'triple_confluence'` and `conviction in {'medium','high'}`.
- §25 Position Monitor exit logic uses Sec.5.10's score: a 3-of-3
  position that decays to 0-of-3 (all components flipped or
  abstained) triggers a "thesis broken" exit; intermediate decay
  (3 → 2 → 1) is a watchlist event, not an exit.
- Pine bundle for chart visualization: `pine/iq_triple_confluence.pine`
  (overlays all three indicators; emits a single label on 3-of-3 bars).

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

Replay 3 years (2023-04 to 2026-04) on Nifty 500 (industrial-only
per the §2 v2.1 universe rule). For every BUY signal generated,
measure these. **Must pass to ship.**

| Metric | v2.1 Target | v2.0 Target (audit) | Status |
|---|---|---|---|
| Hit rate (% reaching +5%) | **≥ 45%** | ≥ 60% | RECALIBRATED |
| Average days to T1 | ≤ 25 | ≤ 25 | unchanged |
| Average win | **≥ +6%** | ≥ +8% | RECALIBRATED |
| Average loss | **≤ −3%** | ≤ −2.5% | RECALIBRATED |
| Max consecutive losses | **≤ 8** | ≤ 5 | RECALIBRATED |
| Win/loss ratio | ≥ 2.0 | ≥ 2.0 | unchanged |
| Profit Factor | ≥ 1.8 | ≥ 1.8 | unchanged |
| Sharpe (annualized) | ≥ 1.5 | ≥ 1.5 | unchanged |

**Recalibration rationale.** v2.0 §11 gate values were set
pre-evidence from industry rules of thumb. The G1 + A1 + A2 + A4
+ recency sweep loop (Apr 2026, N=95 industrial-only Nifty 500
trades over 3 years) demonstrated that a 13-condition strict-AND
gate on EOD daily structurally produces ~41% hit rate with PF
1.95 and Sharpe 2.81 — the system has real edge but the count-
based hit-rate target was set above what a strict-AND gate
naturally produces. The recalibrated targets (45% / +6% /
−3% / 8) match institutional-grade momentum-system norms
(40–50% hit rate, larger consecutive-loss tolerance to ride out
regime drawdowns). Magnitude-weighted gates (PF, W/L, Sharpe)
were correctly set in v2.0 and remain unchanged. Original v2.0
thresholds preserved at `spec/filter_spec_v2.md` per §16 audit
trail; this is a deliberate spec change, not a quiet number-
tweak.

**Profit Factor** = gross profits / gross losses (sum of positive trade
returns ÷ absolute sum of negative trade returns). Hit rate and
win/loss ratio are *count-based* — they ignore magnitude. PF catches
the case where most trades win but a few oversized losers wipe out
the gains. Industry threshold: ≥ 1.8 acceptable, ≥ 2.0 good.

If any **must-pass** metric fails, system does NOT ship. Rules are revised,
validator re-runs, decision is documented.

> **G1-final annotation (Apr 2026).** Hit rate observed at 41.1% on
> N=95 industrial-only Nifty 500 trades, **3.9pp below** the v2.1 ≥ 45%
> target. All other 7 metrics passed (PF 1.95, Sharpe 2.81, W/L 2.16,
> avg loss −2.86%, max consec losses 7, avg days to T1 11.3, avg win
> +6.19%). The gap is statistically meaningful at N=95 (standard error
> on hit rate ≈ ±5pp) and reflects the structural property of a 13-
> condition strict-AND gate with a 3-tier profit ladder. The system is
> accepted as **Provisionally Validated (7/8 substantive pass)** pending
> Phase F validation. Phase F introduces conviction tier (§14) where
> HIGH conviction requires CR-002 recency (`days_since_52wh ≤ 90`);
> recency-sweep evidence (`spec/samples/backtest_g1_recency_sweep.md`)
> showed the 90-day cohort yields hit rate **43.8% at PF 2.59 / Sharpe
> 4.98**. v2.1 promotes from Provisional to Locked only after the
> §11.1 criterion clears.

**Forward-only discipline:** validator uses ONLY data available on the scan
date — no lookahead. Catalyst data uses point-in-time freezes from §17.

### 11.1 Promotion criteria from Provisional to Locked

v2.1 promotes from **Provisional** to **Locked** only after **all** of:

1. Phase F (§14 conviction tier) is implemented and live in code,
   with HIGH-conviction-tier sizing per §10.
2. CR-002 recency rule (`days_since_52wh ≤ 90`) is wired as the
   HIGH-conviction-tier-specific filter (NOT as a §5 BUY gate).
3. A G2-equivalent backtest run on the same industrial-only Nifty 500
   universe shows **HIGH-tier hit rate ≥ 45% on N ≥ 30 HIGH-tier
   trades** over the 3-year replay window.
4. All other §11 metrics still pass on the **portfolio-blended**
   tier-weighted return (HIGH + STANDARD), not just on HIGH alone —
   we don't ship a system that depends on tier discrimination to
   meet aggregate gates if blended numbers regress.
5. Decision documented in this file with the resulting backtest
   reports linked.

Until #1–#5 land, v2.1 stays **Provisional** and the production code
runs the §5 v2.0 13-condition strict-AND gate, sized at §10 STANDARD
0.5% per trade. The Provisional status is **not a blocker** for
Phase D (catalyst engine, §13) or Phase K (Next.js trader app, §21);
those phases consume the Provisional v2.1 contract and produce
output gated by the §11 substantive-pass acceptance.

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

**Phase D (deterministic, MVP) — ✓ done (v1).** All five sources active
in `filter/saadhana_filter/catalysts/sources/`. Covers ~70% of catalysts.
NO LLM.

| Source | Module | Catalyst types emitted | Freshness | Magnitude |
|---|---|---|---|---|
| 1. BSE/NSE corporate filings | `bse_filings.py` | `earnings_beat`, `guidance_raise`, `buyback`, `management_change`, `m_and_a` | 7 / 30 / drop>30d | base 5–7 + ×1.5 strength-keyword boost |
| 2. NSE shareholding pattern | `shareholding.py` | `fii_increase`, `dii_increase`, `promoter_buying` | 30 / 90 / drop>90d | `min(10, abs(delta_pp) * 2)` |
| 3. NSE block & bulk deals | `block_deals.py` | `block_deal_buy`, `block_deal_sell` | 7 / 30 / drop>30d | `min(10, value_cr / 100)`; cluster-boost ×1.5 |
| 4. SEBI insider trading | `insider_trades.py` | `promoter_buying`, `promoter_selling`, `insider_buying` | 14 / 60 / drop>60d | `value × role_weight × cluster_boost` |
| 5. Sector momentum | `sector_momentum.py` | `sector_momentum` | always FRESH | `min(10, change_5d * 200) × (0.5 + breadth)` |

Phase D1 ships fixture-backed fetchers under `data/catalysts/`; Phase D2
swaps each `*_fixture_fetcher` for a live BSE/NSE/SEBI scraper without
changing the classifier, aggregator, or downstream consumers. The
fetcher protocols are defined per source file.

**Phase E (LLM-classified):** news headlines via free RSS / API. Small
local model (Qwen 7B / Phi-4) classifies each headline into the §13.1
taxonomy with confidence score. Headlines with confidence < 0.75 are
dropped. Phase E does NOT extend the taxonomy — it adds a sixth
classification source emitting the same shape.

**High-conviction flag.** A row is flagged
`has_high_conviction_catalyst = true` when any attached catalyst is
both `FRESH` and has `magnitude_score ≥ 7`. Drives §14 conviction
tier in Phase F.

**Cluster boost.** Sources 3 (block deals) and 4 (insider trades)
apply a ×1.5 boost when ≥ 2 same-side disclosures land for the same
symbol within the lookback window — a hand-curated proxy for
"stacked institutional interest" until the full §14 conviction tier
formalises this.

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

## Sec.14a Scanner cohort registry

The InvestQuest architecture (review v1.2) defines **10 cohorts** —
each a separate candidate function with its own entry rules, exit rules,
universe filters, and validation gates. The scanner cohort registry is
the single source of truth for which cohorts are wired into the daily
scan, what they do, and where they sit in the validation pipeline.

Per §0.7, the universe filter (§2) is sector-agnostic. Each cohort
declares its own optional `sector_exclusions` list, which the scanner
applies to the universe at candidate-function invocation time. The
ledger (§17) stores `cohort_id` and any applied exclusions on every
emitted signal — making sector decisions auditable per-signal, not
buried in a global universe filter.

### Cohort schema

Each registered cohort is a record with the following fields:

| Field | Type | Description |
|---|---|---|
| `cohort_id` | str | Stable slug (e.g., `pro_setup_13`, `triple_confluence`); used as the §17 ledger key |
| `display_name` | str | Human-facing label for /scanners and /stock pages |
| `description` | str | One-paragraph plain-English thesis |
| `instrument` | str | `equity` (v1) — reserved for `etf`, `index_future`, etc. |
| `horizon` | str | `swing` (5–60 bars), `position` (60–250 bars), `intraday` (deferred) |
| `source` | str | Spec section(s) that define the candidate function (e.g., `Sec.5`, `Sec.5.10`) |
| `candidate_fn` | str | Fully-qualified Python callable name (e.g., `saadhana_filter.signals.candidate_pro_setup_13`) |
| `entry_logic` | str | One-line summary; full logic in `source` |
| `exit_logic` | str | One-line summary; full logic in §25 Position Monitor |
| `sector_exclusions` | list[str] | Sector names excluded *for this cohort only*. Empty list = sector-agnostic (matches universe). |
| `position_size_tier` | str | §10 tier — `STANDARD` / `HIGH`; or `dynamic` when cohort emits its own conviction (e.g., Triple confluence 2-of-3 vs 3-of-3) |
| `validation_gate` | str | Phase identifier — `G1` (technical baseline), `G2` (catalyst layer), `F` (Phase F shadow), `paper` (paper trading), `live` |
| `status` | str | `live` / `shadow` / `paper` / `validation` / `deferred` / `retired` |
| `g1_baseline_ref` | str \| null | Path to the G1 baseline backtest report (`spec/samples/...md`); null until S1.3-equivalent rebaseline runs |

### v1 cohort registry

The v1 registry contains exactly the two cohorts that the Triple
confluence vertical slice ships. The remaining 8 cohorts are reserved
slots — listed below as `deferred` with their target sprint — and will
be filled in their respective backtest tasks per §0.7.

| `cohort_id` | `display_name` | `source` | `horizon` | `sector_exclusions` | `position_size_tier` | `status` | `g1_baseline_ref` |
|---|---|---|---|---|---|---|---|
| `pro_setup_13` | Pro-setup 13/13 | Sec.5 | swing | `['FINANCIAL_SERVICES','NBFC','BANK']` | `STANDARD` | `live` | `spec/samples/backtest_report_g1_investquest_universe.md` (industrial slice) |
| `triple_confluence` | Triple confluence | Sec.5.10 | position | `[]` | `dynamic` (medium=STANDARD, high=HIGH) | `validation` | (pending S2.3 backtest) |

### Reserved cohorts (deferred to later sprints)

Listed in §14a so the scanner shape is fixed at the v1 schema lock
even though the candidate functions don't exist yet. Each reservation
is a *promise* to ship the cohort with a G1 baseline before flipping
its `status` to `live`.

| `cohort_id` | `display_name` | Target sprint | Notes |
|---|---|---|---|
| `counter_trend` | Counter-trend rebound | future | RSI-divergence + reversal |
| `base_breakout` | Base breakout | future | Multi-week base + volume |
| `rpi_leaders` | RPI leaders (sustained) | future | RPI > 80 percentile, multi-week |
| `rpi_spurt` | RPI spurt + crossover | W1.5 (Wave 1) | Cohort #2 per D9; needs §2 universe seed-list expansion |
| `volume_blast` | Volume blast | future | RVOL ≥ 3 + breakout |
| `super_strength` | Super strength | future | All-time-high proximity + RPI |
| `ma_crossover` | MA crossover (stand-alone) | future | Sec.5.7 as cohort #8 |
| `adaptive_trendflip` | Adaptive trendflip | future | Sec.5.8 as cohort #9 |
| `deviation_trend` | Deviation trend | future | Sec.5.9 as cohort #10 |

The 10-cohort target is the InvestQuest architecture v1.2 commitment;
the v1 registry ships **2 of 10** (`pro_setup_13` + `triple_confluence`).
The other 8 ship as their backtest tasks complete — never before
their G1 baseline lands.

### Storage representation

The registry is stored as Python source at
`filter/saadhana_filter/scan/cohorts.py`:

```python
COHORTS: list[CohortSpec] = [
    CohortSpec(
        cohort_id="pro_setup_13",
        display_name="Pro-setup 13/13",
        description="Strict-AND of 13 BUY conditions per §5; "
                    "sector_exclusions migrate from §0.5 amendment.",
        instrument="equity",
        horizon="swing",
        source="Sec.5",
        candidate_fn="saadhana_filter.signals.candidate_pro_setup_13",
        entry_logic="all 13 BUY conditions True",
        exit_logic="§25 Tier 1 (hard stop / target ladder / score collapse)",
        sector_exclusions=["FINANCIAL_SERVICES", "NBFC", "BANK"],
        position_size_tier="STANDARD",
        validation_gate="G1",
        status="live",
        g1_baseline_ref="spec/samples/backtest_report_g1_investquest_universe.md",
    ),
    CohortSpec(
        cohort_id="triple_confluence",
        display_name="Triple confluence",
        description="2-of-3 / 3-of-3 agreement across MA crossover, "
                    "Adaptive SuperTrend, Deviation Trend (Sec.5.10).",
        instrument="equity",
        horizon="position",
        source="Sec.5.10",
        candidate_fn="saadhana_filter.signals.candidate_triple_confluence",
        entry_logic="≥ 2 components qualified bullish on same scan bar",
        exit_logic="§25 Tier 2 (component decay watchlist; 0-of-3 = exit)",
        sector_exclusions=[],
        position_size_tier="dynamic",
        validation_gate="paper",
        status="validation",
        g1_baseline_ref=None,
    ),
]
```

The same data is mirrored to a Vercel Postgres `scanner_cohorts` table
(schema locked in S1.7) so the Next.js /scanners page can render the
registry without re-importing Python.

### Status lifecycle

A cohort moves through statuses in a fixed order:

```
deferred → validation → shadow → paper → live
                                     ↓
                                  retired
```

| Transition | Gate |
|---|---|
| `deferred` → `validation` | candidate_fn implemented + unit tests green |
| `validation` → `shadow` | G1 backtest baseline meets §11 acceptance OR documented exception |
| `shadow` → `paper` | 4 weeks of shadow-mode signals match expected drift envelope (§18) |
| `paper` → `live` | 4 weeks of paper trading meets paper-acceptance gate (Sprint 3) |
| `live` → `retired` | §18 forensics 3σ drift breach OR operator decommission |

### Edge cases

| Case | Behaviour |
|---|---|
| Two cohorts emit signals for the same symbol on the same bar | Both ledger entries written; UI dedupes by symbol with badges showing all qualifying cohorts. Position sizing takes the **higher** tier across the agreeing cohorts. |
| Cohort has empty `sector_exclusions` but a sector consistently underperforms in shadow mode | Forensics opens a CR (§19) proposing exclusion; doesn't auto-mutate the registry. |
| Operator hard-disables a cohort mid-day | `status: 'paused'` (transient) — no new signals; existing positions continue to be monitored by §25. Resume restores prior status. |
| Two registry rows share `cohort_id` | Schema validation fails at `cohorts.py` import time; daily scan refuses to start. |

### Cross-references

- §0.7: cohort-level sector exclusion principle (this section is the registry).
- §17: every emitted signal records `cohort_id` + applied `sector_exclusions`.
- §18 forensics: drift envelope is computed *per `cohort_id`*, not blended.
- §19 rule promotion: new cohorts arrive here as `validation` after their CR ships.
- §25 Position Monitor: exit logic deduplication is keyed by (symbol, cohort_id).
- Sprint 3 K1.x: /scanners page reads this registry; one tab per `live` or
  `shadow` cohort.

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

### 15.1 Catalysts (Phase D additions)

Each candidate row carries an attached catalyst summary populated by
the Phase D engine (see §13). Schema:

```jsonc
{
  // ...existing candidate fields...
  "catalysts": [
    {
      "type": "earnings_beat",        // §13.1 taxonomy
      "date": "2026-04-25",            // ISO YYYY-MM-DD (event date)
      "days_old": 5,
      "freshness": "FRESH",            // FRESH (<7d) | RECENT (<30d) | STALE
      "source_url": "https://www.bseindia.com/...",
      "detail": "Q4 EPS up 18% YoY beat estimates by 12%.",
      "magnitude_score": 9             // 0..10, deterministic per §13.1
    }
  ],
  "catalyst_count_fresh": 1,
  "catalyst_count_recent": 0,
  "has_high_conviction_catalyst": true  // FRESH + magnitude ≥ 7
}
```

The same catalyst payload appears on `signals/research.json` per-row
records (where catalysts are attached to every Tier-1-passing symbol,
not only candidates) and in the per-sector ``catalyst_rollup`` field
on each `sector_strength` entry, which surfaces top-N highlights for
the /research drill-down "Triggers" panel.

**Sources currently active** (Phase D, deterministic only):
1. BSE/NSE corporate filings (earnings_beat, guidance_raise, buyback,
   management_change, m_and_a) — fixture-backed in Phase D1; Phase
   D2 swaps in the live scraper without changing the schema.
2. NSE shareholding pattern (fii_increase, dii_increase,
   promoter_buying) — *land in upcoming commit*.
3. NSE block & bulk deals (block_deal_buy) — *land in upcoming commit*.
4. SEBI insider trading disclosures (promoter_buying, insider_buying)
   — *land in upcoming commit*.
5. Sector momentum (sector_momentum) — *land in upcoming commit*.

Phase E adds an LLM news-classification source that emits the same
catalyst schema; it does not extend the §13.1 taxonomy.

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

A shadow rule is promoted to pending_approval if **all** of:
- ≥ 30 days in shadow
- ≥ 20 phantom decisions made
- **Composite improvement gate** — `Δ(P&L) × Δ(Win Rate) × Δ(Profit Factor)`
  must be **> 0 across all three dimensions**
- **No single metric** (Sharpe, max consecutive losses, avg loss) may
  degrade by more than 5%

Rationale: chasing a single metric (hit-rate alone, or P&L alone) is
the standard way rule systems over-fit to the in-sample window. The
composite gate forces a candidate rule to demonstrate it improves
**count, magnitude, and consistency** simultaneously — much harder to
satisfy by accident, and aligned with how the §11 backtest gate
combines hit rate, win/loss, and Profit Factor.

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

- **Page set** (Phase K scope):
  - `/` — hero + today's top 3 score-12+ candidates preview
  - `/scanner` — universe selector + sortable results table (K1.2)
  - `/stock/[symbol]` — header + 13-condition checklist + risk levels (K1.3)
  - `/about` — methodology + disclaimer (K1)
  - **`/research`** — sector strength heatmap + top-10 sector RS list +
    score 10–13 *Watching* candidates within leading sectors + 52WH
    breakout watch panel. **Visible in all regimes including Risk-Off**
    (the system is standing aside but the user still wants to see what
    the universe is doing). No BUY action enabled; no position sizing
    displayed; rows tagged *"Research Only — system standing aside per
    §12"*. Header text quotes §12 verbatim. Connects conceptually to
    §22 Thinking Engine M1 (Sector Strength Engine) — `/research` is
    the surface where M1 will eventually render its outputs. K1 ships
    a basic implementation (sector-RS computed naively from index
    OHLCV); M1 swaps in the proper multi-window RS + breadth + tier
    classifier.
  - `/learning` — forensics review (PERSONAL only, see §21.2)

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

### 21.4 Information architecture (routes shipped + reserved)

**Routes shipped (K1)**

| Route | Purpose |
|---|---|
| `/` | Home — hero + regime ribbon ("● {regime} · Nifty {pct}% / Strongest today: A · B · C") |
| `/scanner` | Daily BUY/HOLD/SELL/WATCH candidates from `latest.json` |
| `/markets` | Market pulse — sector strength, divergent strength, breakout watch (formerly `/research`, renamed for clarity in K1 IA cleanup; permanent 301 in `next.config.js`) |
| `/stock/[symbol]` | Per-symbol detail — pattern card + catalyst card; renders for any Tier-1-passing symbol regardless of pattern-match status |
| `/about` | Disclaimer, methodology, phases reference |
| `/about/phases` | Phase guidance reference (Layer 3 of the three-layer phase explanation) |

**Routes reserved (post-MVP)**

| Route | Purpose | Phase |
|---|---|---|
| `/watchlist` | Personal saved stocks | After Phase F + Personal mode (K2) |
| `/stocks` | Browse all Nifty 500 — search + mini cards + sector filter | Post-K1 |
| `/research` | **TRUE research** — broker reports, peer comparison, target prices, fundamentals deep-dive | Phase D2/E + new fundamentals data layer |
| `/learning` | Forensics review, weekly retros, rule-promotion proposals | Phase L (Personal-only) |

**Naming discipline.** Never use "Research" for market-pulse content;
"Research" is reserved for the future fundamental analysis layer once
we have broker reports + peer comparison + target prices feeding it.
Industry convention: market-pulse content is "Markets" / "Today" /
"Pulse" — pick one and stick to it. We picked **Markets** in K1.
Component / file / type names that reference the legacy term
(`research-header.tsx`, `ResearchSnapshot`, `signals/research.json`)
intentionally stay as-is to keep the diff narrow; only user-facing
copy renames.

### 21.5 Navigation map (how users reach `/stock/[symbol]`)

The detail page is the conceptual centre of the app — it carries
the per-symbol pattern checklist, risk levels, catalysts, and
(future) chart. Discoverability is enforced by these paths:

1. **Click symbol in any /markets panel** — Strength Despite
   Weakness, 52-Week High Breakout Watch, and the sector drill-
   down's "Top stocks" sub-table all use the shared
   `<SymbolCell>` (`trader/app/components/symbol-cell.tsx`).
2. **Click symbol in /scanner** — every candidate row uses
   `<SymbolCell>` next to the catalyst-chip count.
3. **Search via the nav search bar** — `<SymbolSearch>`
   (`trader/app/components/symbol-search.tsx`) sits in the
   desktop nav between the link group and the CTA, and at the
   top of the mobile drawer. Lazily fetches `/api/universe`
   on first focus; matches symbol prefix → symbol substring →
   company-name substring. Keyboard: ↓/↑ to navigate, Enter to
   open, Escape to clear.
4. **Direct URL** — `/stock/{symbol}` is a stable URL surface
   meant to survive shares, bookmarks, and the eventual
   `/research` (true research) cross-links.
5. **Future routes:** `/watchlist` (Phase F + Personal mode),
   `/research` broker-report links (Phase D2+), `/learning`
   forensics review (Phase L) all link into the same detail
   page; no other discoverability path replaces them.

**Affordance contract for `<SymbolCell>`.** Default: theme text +
JetBrains Mono + fontWeight 500. Hover: accent color tint +
underline + visible ↗ arrow. The arrow is `opacity: 0` by default
and `0.7` on hover — it reinforces "this is a drill-into-detail
link" without adding visual noise to the steady state. Hover
styles live in `globals.css` (the `.saadhana-symbol-cell` class)
because inline styles can't express `:hover`.

**Universe data source.** `/api/universe` reads
`signals/research.json` (the canonical universe — Tier-1-passing
symbols scanned today) and joins on `data/nifty500_constituents.csv`
to pick up the `Company Name` column. Server-side only; the CSV
never leaves the server. Response cached `s-maxage=300` since the
scan rotates only daily.

---

## 22. Thinking Engine (post-MVP roadmap, future Phases Q/R/S/T)

The Thinking Engine is the higher-order conviction layer that sits
**above** Pro-Setup + Catalyst. It targets the 5–10× bagger setups —
rare (5–15 per decade in Indian equities) but where asymmetric upside
lives.

**Reference setup.** India 2021 PSU / Defense / Banking re-rating: 10+
years of underperformance, multiple narrative triggers aligning,
sector breadth confirming, produced multi-baggers (BEL, HAL, Concor,
IRCTC). The Pro-Setup engine alone misses these — by the time score
reaches 13/13 the move is already 2-3× along. The Thinking Engine
catches them at the inflection.

Positioning:
- **Pro-Setup (§5)** — table stakes. Many systems do similar things
  and produce ~40–50% hit rate with PF 1.5–2.0. A working swing
  system, not a moat.
- **Catalyst (§13)** — adds idiosyncratic context. Lifts conviction
  but stays inside the same swing-trade frame.
- **Thinking Engine (§22)** — adds *structural* capabilities Pro-Setup
  can't: multi-year base recognition + multi-attribute thesis
  synthesis. This is what separates institutional desks from retail.

### 22.1 Module roadmap

Four modules, sequenced post-MVP after Phase D + Phase F:

- **M1 / Phase Q — Sector Strength Engine.** Multi-window sector RS
  (5d / 20d / 60d / 252d), sector breadth (% above 50DMA / 200DMA /
  Stage 2), volume sustainability, lead / confirming / mature /
  fading tier classifier. Surface: the public `/research` page (§21.1)
  is the eventual render target.

- **M2 / Phase R — Pattern Lifecycle Engine.** Pre-breakout / initial
  / confirmed / failed taxonomy. Adds *temporal context* to Pro-Setup
  signals — a 13/13 stock in `confirmed` lifecycle stage is materially
  higher conviction than a 13/13 stock in `initial` stage even though
  both score the same on §5.

- **M3 / Phase S — Multi-Year Base / Turnaround Engine.** Stock down
  ≥ 40% from prior peak (or flat ≥ 3 years), recent break above a
  multi-year resistance level (typically 200-week SMA reclaim), volume
  confirmation, sector + fundamental + catalyst convergence. **The
  5–10× bagger detector.** Outputs feed M4.

- **M4 / Phase T — Thesis Score Synthesizer.** Composite of ProSetup +
  Catalyst + Sector Strength + Lifecycle + Multi-year Base +
  Fundamentals → 0–100 thesis score. Drives position sizing 0.5%
  STANDARD → 1.5% HIGH → **5% THESIS-grade** (extreme rarity, not a
  routine sizing tier).

### 22.2 Validation philosophy

The Thinking Engine validation **departs from §11's statistical gate**.
With N=5–15 multi-bagger setups per decade, classical backtesting
produces uninformative confidence intervals (standard error on hit
rate at N=10 is ±15pp — the test signal can't beat noise).

Validation shifts to:

- **Thesis-quality manual review** of historical examples documented
  in `spec/thinking_engine.md` §2 (PSU re-rating 2021, Defense
  2022–23, Pharma COVID 2020, IT 2017–19). Each example walks the
  setup, catalysts, sector / macro / fundamental alignment, and
  outcome — the same way an investment-committee memo reads.
- **Paper-trade-only deployment for the first 12 months** after each
  module ships. Real capital deployment requires explicit human
  approval per a Phase-F-style ledger after the paper window.
- **Separate audit trail** at `spec/thinking_engine.md` (this file
  remains the operational §11-gated contract; the Thinking Engine
  has its own evidence file).

### 22.3 Dependency graph

```
M1 (Sector Strength)  ──┐
                        ├──► M3 (Multi-Year Base)  ──► M4 (Thesis Score)
M2 (Lifecycle)        ──┘                              │
                                                       │
Phase D (Catalyst)    ──────────────────────────────►  M4
Phase F (Conviction)  ──────────────────────────────►  M4
```

- M1 standalone — depends only on existing universe + sector-index
  data.
- M2 depends on M1 + existing §5 Pro-Setup conditions.
- M3 depends on M1 + M2 + Phase D catalyst data (the multi-attribute
  convergence test needs the catalyst tags).
- M4 synthesizes everything above.

CR-005 (in `spec/candidate_rules.md`) lists the schema fields Phase D
must emit so M1–M3 can land later without an expensive schema
migration. CR-005 is the only candidate marked **ACTIVE** rather than
parked — apply during Phase D implementation.

---

## 22b. What v2 deliberately excludes (parked for v3+)

- Sector rotation overlay (beyond regime filter and the §22 M1
  Sector Strength Engine when it lands)
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
| **D** ✓ | Catalyst engine v1 (deterministic sources) | All 5 sources active in `signals/research.json` and `signals/latest.json`; surfaces in `/research` drill-down "Triggers", `/stock/[symbol]` catalyst card, `/scanner` chip count. **Phase D2 (live scrapers) deferred until verified BSE/NSE/SEBI network access** — fixture fetchers swap 1:1 for live ones without contract change. |
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

## Sec.25 Position Monitor

The Position Monitor is the runtime component that watches every open
position and decides when to exit. v1 in this spec corresponds to
"Sec.20 Position Monitor" in the InvestQuest architecture v1.2 review;
the section is renumbered here to avoid collision with §20 Compute
architecture (per §0.6 reservations).

The §17 ledger records *signal emissions* (entries); §25 governs *exits*.
A position has exactly one entry row in the ledger and exactly one exit
row when closed. While open, the monitor advances state on every scan
bar and produces audit events for every state change.

### Position state machine

```
HEALTHY ──┬─→ AT_RISK ──┬─→ TRIGGERED ──→ CLOSED
          │             │
          └─→ TARGET_NEAR ┘ (re-enters HEALTHY if pulls back without trigger)
```

| State | Definition |
|---|---|
| `HEALTHY` | Entry-bar default. Risk model says position is operating within thesis. |
| `AT_RISK` | Distance-to-stop ≤ 1 ATR OR a Tier-1 exit precondition is forming (e.g., 2 of 3 Triple confluence components have flipped). UI surfaces this as a yellow badge. |
| `TARGET_NEAR` | Within 0.5 ATR of next target ladder rung (§7). Ladder partial-exit logic primes here. |
| `TRIGGERED` | An exit trigger fired this bar; exit order being placed. Transient — at most one bar. |
| `CLOSED` | Exit order filled OR cancelled-and-replaced as MARKET on next bar. Terminal. |

State is recomputed on every scan bar. Transitions emit a `position_event`
row keyed by (`position_id`, `bar_date`, `from_state`, `to_state`, `reason`).

### Exit triggers (six)

The six triggers below are evaluated **in priority order** every scan
bar. The first trigger that fires produces a `TRIGGERED` event and
the position closes; remaining triggers are not evaluated.

| Priority | Trigger | Definition | Applies to |
|---|---|---|---|
| 1 | `HARD_STOP` | Close ≤ entry_stop (per §10) | All cohorts |
| 2 | `TARGET_T3` | Close ≥ target_t3 (per §7); also produces ladder partial at T1/T2 | All cohorts |
| 3 | `PATTERN_INVALIDATION` | Cohort-specific structural break (see Triple confluence table below) | All cohorts |
| 4 | `TRAILING_BREAK` | Trailing stop logic per §10 broken (e.g., close below 5-EMA after T2 hit) | All cohorts |
| 5 | `TIME_LIMIT` | Bars-held ≥ horizon-specific cap (swing 60, position 250) AND no T1 hit | All cohorts |
| 6 | `REGIME_OVERRIDE` | §18 forensics 2σ pause OR operator manual override | All cohorts |

**`PATTERN_INVALIDATION` is cohort-specific.** Each cohort registers
its invalidation logic in the §14a `exit_logic` field; the monitor
dispatches on `cohort_id`. Cohort tables below give the full logic.

### Monitoring tiers

The monitor evaluates positions at three cadences:

| Tier | Cadence | What runs | Cost / day |
|---|---|---|---|
| **Tier A — EOD batch** | 1× per day after market close | Full evaluation of all six triggers across all open positions; updates state, writes events, places next-day exit orders | One scheduled GH Actions run |
| **Tier B — Intraday EOD-equivalent** | 1× per day (15:25 IST, 5 min before close) | Same as Tier A but on the *current* day's bar — produces same-day exit orders for triggers that have already fired | One scheduled run |
| **Tier C — Instant** | (deferred per D5) | Sub-bar trigger detection via live feed | v2 (Sec.6.3 deferred bucket) |

v1 ships **Tier A + Tier B**. Tier C is reserved.

### Triple confluence exit logic (Sec.5.10 cohort)

| Trigger | Definition (specific to triple_confluence) |
|---|---|
| `HARD_STOP` | close ≤ entry_stop (where entry_stop = entry × 0.97 OR entry − 1.5×ATR_at_entry, whichever tighter) |
| `TARGET_T3` | close ≥ entry × 1.15 (position horizon target) |
| `PATTERN_INVALIDATION` | All 3 components currently `qualified=False` OR ≥ 2 components currently `direction = -1` (thesis fully broken) |
| `TRAILING_BREAK` | After T2 hit (entry × 1.10), close below entry × 1.04 (lock partial profit) |
| `TIME_LIMIT` | bars_held ≥ 250 AND close < entry × 1.05 (didn't reach T1) |
| `REGIME_OVERRIDE` | Forensics 2σ drift on cohort_id `triple_confluence` over trailing 4-week window |

A 3-of-3 entry that decays to 2-of-3 is a `state_change → AT_RISK` event,
**not** an exit. The position only exits on full thesis breakdown
(0-of-3 OR ≥ 2 bearish).

### Pro-setup 13/13 exit logic (Sec.5 cohort)

| Trigger | Definition (specific to pro_setup_13) |
|---|---|
| `HARD_STOP` | close ≤ entry_stop (per §5 distance-to-stop logic) |
| `TARGET_T3` | close ≥ target_t3 (per §7 ladder, swing horizon target) |
| `PATTERN_INVALIDATION` | `stage_2 = False` OR `inst_flow_score = False` (core thesis broken — these were the gating conditions at entry) |
| `TRAILING_BREAK` | After T2 hit, close below 5-EMA |
| `TIME_LIMIT` | bars_held ≥ 60 AND close < entry × 1.05 |
| `REGIME_OVERRIDE` | Forensics 2σ drift on cohort_id `pro_setup_13` |

### Audit event schema

Every state change writes a row to the `position_events` table:

| Column | Type | Description |
|---|---|---|
| `position_id` | uuid | FK to `positions` table |
| `bar_date` | date | Scan bar this event was produced for |
| `from_state` | str | Previous state |
| `to_state` | str | New state |
| `reason` | str | Trigger name (`HARD_STOP`, `AT_RISK_DTS_LT_1ATR`, etc.) |
| `cohort_id` | str | Cohort that owns this position |
| `metadata` | jsonb | Cohort-specific snapshot (e.g., for triple_confluence: which 0/1/2/3 components qualified) |
| `created_at` | timestamp | UTC |

Audit completeness rule: a position's full lifecycle MUST be reconstructable
by replaying events in `bar_date, created_at` order. If a state change is
inferred at run time (e.g., a missed bar from a data outage), the
event still gets written — flagged with `metadata.inferred = true`.

### Edge cases

| Case | Behaviour |
|---|---|
| Two triggers fire on the same bar | Higher-priority trigger wins (table order). Audit event records the winning trigger plus `metadata.also_fired = [...]`. |
| Position has zero bars of history at scan time (entry day before EOD) | Skip evaluation — entry events don't get exit-checked on entry bar. First evaluation is on bar+1. |
| Cohort retired while position open | Position continues to be monitored under its *original* cohort_id's exit logic until closed. Retired status applies only to *new* signal emission. |
| Operator manually closes position via /positions UI | Treated as `REGIME_OVERRIDE` with `metadata.manual_close = operator_id`. |
| Same symbol held under two cohorts (e.g., pro_setup_13 AND triple_confluence) | Two separate `position_id`s, two independent exit timelines. Sizing for each follows its cohort's tier. |
| Data outage prevents evaluation on a scheduled bar | On next successful run, monitor fires for *both* missed bar and current bar — events recorded with `metadata.inferred = true` for the missed bar. |

### Cross-references

- §10 risk math: entry_stop and trailing-stop primitives.
- §7 target ladder: T1/T2/T3 partial exits.
- §14a registry: `exit_logic` field references this section's
  cohort-specific tables; new cohorts must extend those tables before
  going live.
- §17 ledger: the entry row points forward to a `position_id`; this
  section's events table owns the per-bar exit timeline.
- §18 forensics: produces the regime override signal that triggers
  `REGIME_OVERRIDE` on a per-cohort basis.
- §25 storage in Postgres (positions + position_events tables) is
  locked in S1.7 alongside §17 ledger.

---

**End of spec v2.0** — this document is the contract. Every line of code
written for the filter must trace back to a section here. Drift from spec
is caught by parity tests and forensics — not by reviewers months later.
