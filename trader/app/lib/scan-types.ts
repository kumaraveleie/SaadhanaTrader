/**
 * Client-safe types and helpers for the §15 scan output.
 *
 * This file has NO Node-only imports so client components (e.g. the
 * freshness indicator) can pull from it without dragging the server-
 * only ``readLatestScan`` reader into the browser bundle.
 */

export type Regime = 'Risk_On' | 'Caution' | 'Risk_Off';
export type SignalState = 'BUY' | 'HOLD' | 'SELL' | 'WATCH' | 'WAIT';

// ──────────────────────────────────────────────────────────────────────────
// §13 Phase D catalyst types — mirrors the Python dataclasses in
// filter/saadhana_filter/catalysts/types.py.
// ──────────────────────────────────────────────────────────────────────────
export type CatalystType =
  | 'earnings_beat'
  | 'guidance_raise'
  | 'buyback'
  | 'management_change'
  | 'm_and_a'
  | 'policy_tailwind'
  | 'fii_increase'
  | 'dii_increase'
  | 'promoter_buying'
  | 'block_deal_buy'
  | 'sector_momentum';

export type FreshnessTag = 'FRESH' | 'RECENT' | 'STALE';

export type Catalyst = {
  type: CatalystType;
  date: string; // ISO YYYY-MM-DD
  days_old: number;
  freshness: FreshnessTag;
  source_url: string;
  detail: string;
  magnitude_score: number; // 0..10
};

// One-symbol-tagged catalyst as it appears inside a sector rollup highlight.
export type SectorCatalystHighlight = Catalyst & {
  symbol: string;
};

export type CatalystRollup = {
  fresh_count: number;
  recent_count: number;
  high_conviction_count: number;
  highlights: SectorCatalystHighlight[];
};

export type CandidateRow = {
  symbol: string;
  signal: SignalState;
  pro_setup_score: number;
  drs: number;
  regime: Regime;
  tier1_passed: boolean;
  failed_conditions: string[];
  notes: string[];
  sell_reason: string | null;
  // BUY-only risk levels (§5.4 + §7); absent for HOLD/SELL rows
  entry_price?: number;
  stop_loss?: number;
  target_t1?: number;
  target_t2?: number;
  risk_pct?: number;
  reward_pct?: number;
  rr_ratio?: number;
  // §13 catalysts (Phase D). Optional on legacy JSON (pre-Phase D);
  // empty array on current scans when no catalysts present.
  catalysts?: Catalyst[];
  catalyst_count_fresh?: number;
  catalyst_count_recent?: number;
  has_high_conviction_catalyst?: boolean;
};

export type ScanResult = {
  scan_date: string; // ISO YYYY-MM-DD
  spec_version: string;
  regime: Regime;
  universe_size: number;
  tier1_passed: number;
  candidates: CandidateRow[];
};

/**
 * Calendar-day age of the scan as integer days (0 = today, 1 = yesterday).
 * Used by the freshness indicator to color-shift per design_system §5.
 */
export function scanAgeDays(scanDateIso: string, now: Date = new Date()): number {
  const scan = new Date(scanDateIso + 'T00:00:00');
  const today = new Date(now.toISOString().slice(0, 10) + 'T00:00:00');
  return Math.max(0, Math.round((today.getTime() - scan.getTime()) / (1000 * 60 * 60 * 24)));
}

// ──────────────────────────────────────────────────────────────────────────
// /research page snapshot — emitted by ``scripts/research_scan.py``
// (mirrors ``ResearchSnapshot`` / ``ResearchRow`` in
// filter/saadhana_filter/scan/research.py exactly)
// ──────────────────────────────────────────────────────────────────────────
export type LifecycleTag = 'INITIAL' | 'CONFIRMED' | 'LATE' | 'UNKNOWN';

export type ResearchRow = {
  symbol: string;
  sector: string;
  sub_industry: string; // NSE Industry — finer than sector (e.g. "Capital Goods")
  close_today: number;
  close_yesterday: number;
  pct_change_today: number; // decimal
  pct_change_5d: number; // decimal — 5-trading-day return
  dist_from_50dma_pct: number; // decimal
  dist_from_200dma_pct: number; // decimal; >0 = above 200-DMA
  dist_from_52wh_pct: number; // decimal; negative = below 52WH
  bars_since_52wh_break: number | null;
  rsi_14: number;
  bb_width_pct: number;
  bb_width_over_median: number;
  inst_flow_score_30b: number;
  inst_buy_bar_count_5d: number;
  rvol_today: number; // today's volume / 50-bar prior mean
  pro_setup_score: number;
  lifecycle: LifecycleTag;
  // §13 catalysts (Phase D). Empty array when no catalysts present.
  catalysts: Catalyst[];
  catalyst_count_fresh: number;
  catalyst_count_recent: number;
  has_high_conviction_catalyst: boolean;
};

// M1 v0 sector aggregate emitted under ``sector_strength`` in research.json.
export type SectorTopStock = {
  symbol: string;
  today_pct: number;
  pct_change_5d: number;
  phase: LifecycleTag;
  inst_flow_score_30b: number;
};

export type SectorStrength = {
  sector: string; // slug e.g. "PHARMACEUTICALS"
  sector_label: string; // human-readable e.g. "Pharmaceuticals"
  today_pct: number;
  rs_5d: number | null;
  rs_20d: number | null;
  rs_60d: number | null;
  breadth_above_50dma: number;
  breadth_above_200dma: number;
  sector_phase: string; // M1 v0 placeholder
  sector_phase_note: string;
  top_stocks: SectorTopStock[];
  inst_flow_total: number;
  inst_buy_bar_count_5d: number;
  sector_count: number;
  rank_by_inst_flow: number;
  // §13 catalyst rollup across constituents (Phase D).
  catalyst_rollup: CatalystRollup;
};

export type ResearchSnapshot = {
  scan_date: string;
  spec_version: string;
  universe_size: number;
  tier1_passed: number;
  nifty_close_today: number;
  nifty_close_yesterday: number;
  nifty_pct_change_today: number;
  sector_strength: SectorStrength[];
  rows: ResearchRow[];
};
