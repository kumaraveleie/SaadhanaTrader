/**
 * Canonical 13-condition catalogue per spec §5 v2.0 (preserved by v2.1).
 *
 * Order matches ``ALL_CONDITIONS`` in
 * ``filter/saadhana_filter/indicators/conditions.py``. The labels here are
 * user-facing — short headline + 1-line "what it tests" description for
 * the /stock/[symbol] checklist. Internal canonical keys never appear in
 * the rendered DOM — they're used only as React keys.
 *
 * NOTE: ``not_extended`` is the v2.0 form (kept in v2.1 — see §5.5).
 * The recency-of-strength idea lives in CR-002 as a Phase F conviction-
 * tier candidate, NOT a hard BUY gate.
 */

export type ConditionMeta = {
  key: string; // canonical snake_case
  group: 'Trend' | 'Momentum' | 'Accumulation' | 'Risk' | 'Not extended';
  headline: string;
  description: string;
};

export const CONDITIONS: readonly ConditionMeta[] = [
  // §5.1 Trend
  {
    key: 'stage_2',
    group: 'Trend',
    headline: 'Stage 2 (Weinstein)',
    description: 'Close above the 30-week SMA and the SMA itself is rising — confirmed structural uptrend.',
  },
  {
    key: 'above_50_and_200_ema',
    group: 'Trend',
    headline: 'Above 50 & 200 EMAs',
    description: 'Price trades above both the 50-day and 200-day exponential averages — long-cycle support intact.',
  },
  {
    key: '5ema_above_20ema_rising',
    group: 'Trend',
    headline: '5-EMA above 20-EMA, rising',
    description: 'Short-term moving average is above the medium-term and accelerating — fresh momentum, not stalling.',
  },
  {
    key: 'weekly_hh_hl',
    group: 'Trend',
    headline: 'Weekly higher highs / higher lows',
    description: 'Last 8 weekly bars show structural higher highs and higher lows — clean uptrend on the weekly timeframe.',
  },
  // §5.2 Momentum
  {
    key: 'rsi_50_70',
    group: 'Momentum',
    headline: 'RSI(14) between 50 and 70',
    description: 'Relative Strength Index in the constructive band — momentum building, not yet overbought.',
  },
  {
    key: 'macd_hist_rising',
    group: 'Momentum',
    headline: 'MACD histogram > 0 and rising',
    description: 'MACD signal expanding to the upside — momentum accelerating, not peaking.',
  },
  // §5.3 Accumulation
  {
    key: 'institutional_flow',
    group: 'Accumulation',
    headline: 'Institutional / heavy buy in last 5 days',
    description: 'At least one bar in the past week with relative volume ≥ 1.5× and an up close — accumulation footprint.',
  },
  {
    key: 'inst_flow_score',
    group: 'Accumulation',
    headline: 'Net 30-bar accumulation positive',
    description: 'Heavy-buy bars outnumber heavy-sell bars over the last 30 sessions — supply absorbed, not distributed.',
  },
  // §5.4 Risk
  {
    key: 'distance_to_stop_le_3pct',
    group: 'Risk',
    headline: 'Stop within 3% of entry',
    description: 'Technical risk level (max of 20-EMA or 5-bar low − ATR × 0.5) sits within 3% of the close — tight risk per-trade.',
  },
  {
    key: 'atr_upside_ge_5pct',
    group: 'Risk',
    headline: 'Volatility-projected upside ≥ 5%',
    description: 'ATR(14) × 20 days projects ≥ 5% reachable upside before the nearest resistance — meaningful target distance.',
  },
  {
    key: 'rr_ge_2',
    group: 'Risk',
    headline: 'Reward / risk ratio ≥ 2',
    description: 'Projected upside is at least twice the distance to stop — favorable expected-value asymmetry.',
  },
  // §5.5 Not extended
  {
    key: 'not_extended',
    group: 'Not extended',
    headline: 'Not extended (≥ 2% from 52-week high)',
    description: 'Close is more than 2% below the 52-week high — entering after a pullback, not chasing a top. (Fresh-breakout exception applies.)',
  },
  {
    key: 'bb_width_alive',
    group: 'Not extended',
    headline: 'Bollinger band width healthy',
    description: 'Bollinger band width above its 30-bar median (or fresh breakout in last 3 bars) — avoiding dead consolidation.',
  },
];

export const CONDITION_GROUPS: ReadonlyArray<ConditionMeta['group']> = [
  'Trend',
  'Momentum',
  'Accumulation',
  'Risk',
  'Not extended',
];
