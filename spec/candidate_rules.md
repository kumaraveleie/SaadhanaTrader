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
