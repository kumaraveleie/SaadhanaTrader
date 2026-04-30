/**
 * Client-safe types and helpers for the §15 scan output.
 *
 * This file has NO Node-only imports so client components (e.g. the
 * freshness indicator) can pull from it without dragging the server-
 * only ``readLatestScan`` reader into the browser bundle.
 */

export type Regime = 'Risk_On' | 'Caution' | 'Risk_Off';
export type SignalState = 'BUY' | 'HOLD' | 'SELL' | 'WATCH' | 'WAIT';

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
  dist_from_52wh_pct: number; // decimal; negative = below 52WH
  bars_since_52wh_break: number | null;
  rsi_14: number;
  bb_width_pct: number;
  bb_width_over_median: number;
  inst_flow_score_30b: number;
  rvol_today: number; // today's volume / 50-bar prior mean
  pro_setup_score: number;
  lifecycle: LifecycleTag;
};

export type ResearchSnapshot = {
  scan_date: string;
  spec_version: string;
  universe_size: number;
  tier1_passed: number;
  nifty_close_today: number;
  nifty_close_yesterday: number;
  nifty_pct_change_today: number;
  rows: ResearchRow[];
};
