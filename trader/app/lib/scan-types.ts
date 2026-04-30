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
