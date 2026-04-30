# Saadhana — Candidate Rules Registry

This file tracks rule ideas to test in §19 shadow mode once the Signal
Ledger has 90+ closed signals. Rules are **not** added to §5 directly.
They earn their way in via the rule promotion pipeline (§19) with
evidence — composite improvement across P&L × Win Rate × Profit Factor
per §19.2, no single-metric degradation > 5%.

## Active candidates

### CR-001: ADX(14) > 20 trend-strength filter
- **Source:** External Nifty algo backtest report (Apr 2026)
- **Hypothesis:** Filtering BUYs by ADX > 20 would reduce false
  positives in choppy / sideways stocks where the §5 13-condition
  stack triggers but no real trend exists. The 13 conditions can
  align in a flat range (RSI mid-band, EMAs marginally stacked, BB
  width briefly above its median) without any directional conviction.
  ADX is a directional-movement-strength indicator that's orthogonal
  to the existing condition set.
- **Test plan:** Once Phase H ledger has 90+ closed signals, run in
  §19 shadow mode for 30 days. Promote per §19.2 if composite
  improvement is positive across Δ(P&L) × Δ(Win Rate) × Δ(Profit
  Factor) with no single-metric degradation > 5%.
- **Status:** Parked (awaiting Phase H + 90 days of closed-signal data)

### CR-002: Recency-of-strength as HIGH-conviction-tier filter
- **Source:** Phase G1 A4 stop-out audit + Apr 2026 recency sweep
  (`spec/samples/backtest_g1_a4_stopout_audit.md` and
  `spec/samples/backtest_g1_recency_sweep.md`).
- **Hypothesis:** ``days_since_52wh`` ≤ 90 is a meaningful entry-
  quality filter, but as a hard BUY gate it cuts trade volume
  85–90% (G1d ran with N=11). Used instead as a HIGH-conviction-
  tier gate per §14, it would split BUYs into:
  - **STANDARD tier** (1× sizing per §10) — score = 13/13 on the
    v2.0 §5 conditions, no recency requirement.
  - **HIGH tier** (1.5× sizing per §10) — score = 13/13 AND last
    52WH touch within 90 calendar days.

  The recency sweep at 90 days produced PF 2.59 / Sharpe 4.98 vs.
  A1's 1.95 / 2.81 on the same cohort. If that quality lift
  survives in Phase F's tier-weighted portfolio replay, HIGH-tier
  sizing should outperform STANDARD-tier even with smaller N.
- **Test plan:** Implement in Phase F (§14 conviction tier). Run
  the §11 backtest with the tier-split sizing and compare the
  tier-weighted return curve against the equal-weight A1 baseline.
  If HIGH-tier alone beats blended on Sharpe and PF, promote per
  §19 user-approval flow.
- **Status:** Parked for Phase F implementation.

### CR-003: Sector Leadership exception during Risk-Off
- **Source:** Strategic conversation Apr 2026 — sector rotation
  observation (PSU / Defense / FMCG strength during weak markets).
- **Hypothesis:** Stocks in sectors with relative-strength ratio
  ≥ 1.05 vs Nifty over 60 days, satisfying Pro-Setup score 13/13
  AND HIGH conviction tier (CR-002 recency), may produce positive
  expectancy even in Risk-Off regime where §12 currently disables
  all BUYs. Sized at 0.25% portfolio risk per trade (half of
  STANDARD) to acknowledge elevated regime risk. The §12 rule that
  *all* long-only systems lose money in bear markets is broadly
  true but not absolute — sector leaders sometimes carry positive
  expectancy through index drawdowns when the leadership is real
  (relative-strength ratio above 1.05 over a 60-day window is the
  candidate filter for "real").
- **Test plan:** Phase F shadow mode for 60 days post-implementation.
  Required evidence: PF ≥ 2.0 on Risk-Off subset, max consecutive
  losses ≤ 6, Sharpe ≥ 1.0 on the regime-specific window. Promote
  per §19.2 composite gate only if all three clear AND no Sharpe /
  hit-rate degradation > 5% on the Risk-On / Caution subsets.
- **Status:** Parked pending Phase D + Phase F.

### CR-004: Catalyst-confirmed BUYs in Risk-Off
- **Source:** Strategic conversation Apr 2026 — turnaround story
  observation. Multi-bagger setups (PSU 2021, Defense 2022-23)
  often trigger BEFORE broader market regime improves; idiosyncratic
  catalyst strength sometimes dominates regime weakness.
- **Hypothesis:** Score 13/13 + fresh catalyst within 14 days from
  §13.1 categories (`earnings_beat`, `management_change`,
  `m_and_a`, `policy_tailwind`) may justify BUYs in Risk-Off regime.
  Sized at 0.25% portfolio risk per trade to acknowledge the
  regime-against-position asymmetry. Distinct from CR-003 — that's
  *sector-driven* exception; this is *catalyst-driven* exception.
  Both exceptions can coexist independently.
- **Test plan:** Phase D + Phase F shadow mode for 60 days post-
  implementation. Same evidence requirements as CR-003 (PF ≥ 2.0 on
  Risk-Off subset, max consecutive losses ≤ 6, Sharpe ≥ 1.0).
- **Status:** Parked pending Phase D.

### CR-005: Schema hooks for Thinking Engine (Phase D outputs)
- **Source:** §22 Thinking Engine roadmap — pre-emptive schema design
  to avoid downstream rewrite when Modules M1-M4 land.
- **Hypothesis (operational, not signal):** Including the following
  fields in Phase D's per-candidate JSON output costs near-zero
  compute when computing the rest of Phase D, but skipping them
  forces an expensive schema migration when Phase Q-T land. This is
  a forward-compatibility candidate, not a return-edge candidate;
  the §19 promotion gate doesn't apply because there's no signal to
  test — it's purely a data-pipeline preparedness measure.
- **Required fields** to emit per candidate during Phase D:
  - `sector_index_value`
  - `sector_index_change_5d`
  - `sector_index_change_20d`
  - `sector_index_change_60d`
  - `sector_index_change_252d`
  - `sector_breadth_above_50dma`
  - `sector_breadth_above_200dma`
  - `pivot_high_recent`
  - `pivot_low_recent`
  - `bars_since_pivot_high_break`
  - `years_since_prior_peak` (capped at 10)
  - `prior_peak_price`
  - `weeks_above_30week_sma`
- **Status:** **ACTIVE** — apply during Phase D implementation, not parked.
  This is the only entry on this page that bypasses the §19 shadow
  pipeline because it's data plumbing, not a behavior change.

### CR-006: Supertrend(7,2) as conviction-tier confirmation
- **Source:** Chartink "D_MASTER swing trade breakout 10-20% gains"
  scanner review (Apr 2026).
- **Hypothesis:** Supertrend(7,2) crossing AND price above
  Supertrend may add edge as a HIGH-conviction-tier requirement
  (similar shape to CR-002 recency). Could compound with CR-002 to
  define an **ELITE** conviction tier (sized at 2× STANDARD = 1%
  per trade per §10) where score = 13/13 AND CR-002 recency AND
  Supertrend agreement all fire together. Supertrend(7,2) is
  parameter-light (period 7, multiplier 2 — well-known defaults)
  so the failure mode is interpretable; meets the
  "explainable rules" bar that the "deliberately ignore" section
  below imposes on opaque indicators.
- **Test plan:** Shadow mode in Phase F. Measure delta in HIGH-tier
  hit rate when Supertrend agreement is required vs not. Promote
  to ELITE tier per §19.2 composite gate with N ≥ 30 ELITE-tier
  trades.
- **Status:** Parked pending Phase F.

### CR-007: Gap-up rejection filter
- **Source:** Chartink scanner condition "less than 8% above
  yesterday's close" (Apr 2026).
- **Hypothesis:** BUYs taken when today's open is more than 5%
  above yesterday's close are likely chasing exhaustion gaps —
  the entry is structurally late and the §5.4 stop will sit at
  an awkward distance below a gap that's about to fill. Rejecting
  these entries should improve hit rate without losing meaningful
  trade count, since 5%-gap-up bars are a small fraction of qualifying
  setups historically. Threshold of 5% chosen over the Chartink
  paper's 8% because Saadhana's tighter §5.4 risk gate already
  filters out high-volatility entries; we don't need to be as
  permissive on the gap dimension.
- **Test plan:** Shadow mode after Phase H ledger has 90+ closed
  signals. Compare hit rate of gap-rejected vs gap-allowed BUYs.
  Promote per §19.2 if composite improvement is positive across
  the three required axes with no single-metric degradation > 5%.
- **Status:** Parked pending Phase H.

## Retired candidates

(none yet)

---

## How to add a candidate

1. Append a new entry below the last `CR-NNN` with the next sequential id.
2. Required fields: **Source**, **Hypothesis** (≥ 1 paragraph
   explaining what the rule corrects and *why* it should add signal,
   not just noise), **Test plan**, **Status**.
3. Status starts at `Parked`. When Phase H + the data prerequisite is
   met, the forensics engine elevates it to `Shadow` with a 30-day
   horizon. After the §19.2 gate is evaluated, status moves to
   `Pending approval`, then `Live` (✓) or `Retired` (✗).
4. **Never** modify §5 to add a candidate directly. The §19 pipeline
   exists so the system earns rule changes from its own forensics,
   not from external bench-press tests on different time windows.

## Sources we deliberately ignore

The following appear in third-party trading systems / backtest reports
the owner has reviewed; they are **not** parked here because they
violate the spec's design constraints:

- **VWAP-based filters** — VWAP is an intraday concept; v1 is EOD-only
  per spec §22. Park only if v3 adds intraday timing.
- **Ultimate Moving Average / ML SuperTrend / proprietary composites** —
  black-box indicators with no transparent failure mode. Saadhana
  prefers explainable rules whose forensics output a readable
  hypothesis. Re-evaluate only with a written decomposition.
- **Hit-rate targets above 70%** sourced from short trending-window
  backtests — see the §11 footnote on out-of-sample discipline.
  Targets shift only after a full §11 re-validation, never on the
  basis of an external sample.
