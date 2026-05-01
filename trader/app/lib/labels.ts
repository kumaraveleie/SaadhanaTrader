/**
 * §21.1 public-mode label translation.
 *
 * Internal labels (BUY / HOLD / SELL / WATCH / WAIT) are NEVER rendered
 * directly in user-facing JSX. Always go through this mapping. The
 * public domain treats Saadhana as a research / pattern-detection tool;
 * the wording reflects that framing. Personal-mode (Phase K2) uses the
 * raw internal labels.
 */

import type { CatalystType, FreshnessTag, LifecycleTag, Regime, SignalState } from './scan-types';

export type PublicLabel = {
  text: string;
  description: string;
};

const PUBLIC_LABELS: Record<SignalState, PublicLabel> = {
  BUY: {
    text: 'High Pattern Match',
    description:
      'All 13 technical conditions and the fundamental quality gate are firing on the most recent closed bar. The system has identified a setup that historically precedes upside; it is not a recommendation to act.',
  },
  HOLD: {
    text: 'Pattern Holding',
    description:
      'A previously-matched pattern remains intact — none of the system’s exit triggers have fired since detection.',
  },
  SELL: {
    text: 'Pattern Broken',
    description:
      'A previously-matched pattern has now triggered an exit condition. The system has flagged the change; whether to act on it is the reader’s decision.',
  },
  WATCH: {
    text: 'Watching',
    description:
      'The technical setup is partially formed (10–12 of 13 conditions firing). The system surfaces the name for visibility; no action is implied.',
  },
  WAIT: {
    text: '—',
    description: 'No qualifying pattern present today.',
  },
};

export function publicLabel(signal: SignalState): PublicLabel {
  return PUBLIC_LABELS[signal] ?? PUBLIC_LABELS.WAIT;
}

/**
 * Internal-label → display text resolver gated on the build-time mode
 * flag. Personal mode (Phase K2) returns the raw internal label.
 */
export function displayLabel(signal: SignalState, mode: 'public' | 'personal' = 'public'): string {
  if (mode === 'personal') return signal;
  return publicLabel(signal).text;
}

// ──────────────────────────────────────────────────────────────────────────
// Regime → plain-English (§21.1 public-mode jargon scrub).
// Internal labels (Risk_On/Caution/Risk_Off) are never rendered directly.
// ──────────────────────────────────────────────────────────────────────────
export type RegimeLabel = {
  text: string; // short headline ("defensive market")
  tooltip: string; // hover description for the curious
  tone: 'positive' | 'neutral' | 'caution';
};

const REGIME_LABELS: Record<Regime, RegimeLabel> = {
  Risk_On: {
    text: 'bullish market',
    tooltip: 'Nifty is trading above both its 50-day and 200-day moving averages.',
    tone: 'positive',
  },
  Caution: {
    text: 'mixed market',
    tooltip:
      'Nifty is between its 50-day and 200-day moving averages — direction is unclear.',
    tone: 'neutral',
  },
  Risk_Off: {
    text: 'defensive market',
    tooltip:
      'Nifty is trading below its 200-day moving average. The system pauses new long ideas in this regime.',
    tone: 'caution',
  },
};

export function regimeLabel(regime: Regime): RegimeLabel {
  return REGIME_LABELS[regime] ?? REGIME_LABELS.Caution;
}

// Lightweight jargon → plain English mapping for inline copy. Keeps a
// single dictionary so /research, /scanner, /about all speak the same.
export const PLAIN_LANGUAGE = {
  scanner: 'main scanner',
  scannerLong: 'trade scanner',
  rules: 'our trading rules',
  qualityFilter: 'quality filter',
  // Product nomenclature kept verbatim — these are the terms the user
  // explicitly chose to keep visible.
  proSetupScore: 'Pro-Setup Score',
  patternMatch: 'Pattern Match',
} as const;

// ──────────────────────────────────────────────────────────────────────────
// Lifecycle (internal canonical) → user-facing Phase labels.
// Internal keys (INITIAL/CONFIRMED/LATE/UNKNOWN) appear in §17 ledger,
// CR-008, Python research.py — never rename them. Translate ONLY at the
// UI boundary via this map.
// ──────────────────────────────────────────────────────────────────────────
export type PhaseTone = 'bullish' | 'info' | 'warning' | 'muted';

export type LifecycleDisplay = {
  label: string;
  hint: string;
  tone: PhaseTone;
};

export const LIFECYCLE_DISPLAY: Record<LifecycleTag, LifecycleDisplay> = {
  INITIAL: { label: 'Breakout', hint: 'fresh strength', tone: 'bullish' },
  CONFIRMED: { label: 'Trending', hint: 'trend running', tone: 'info' },
  LATE: { label: 'Extended', hint: 'stretched — avoid chasing', tone: 'warning' },
  UNKNOWN: { label: 'Sideways', hint: 'no clear signal', tone: 'muted' },
};

export function phaseLabel(tag: LifecycleTag): string {
  return LIFECYCLE_DISPLAY[tag].label;
}

export type PhaseHelp = {
  title: string;
  summary: string;
  lines: string[];
};

export const PHASE_HELP: Record<LifecycleTag, PhaseHelp> = {
  INITIAL: {
    title: 'Breakout',
    summary: 'Fresh strength · just emerged from base',
    lines: [
      '► Best entry: highest reward, slightly lower hit rate',
      '► Stop: tight (close to base support)',
    ],
  },
  CONFIRMED: {
    title: 'Trending',
    summary: 'Trend running · momentum confirmed',
    lines: [
      '► Solid entry: higher hit rate, less upside left',
      '► Stop: ATR-based, slightly wider than Breakout',
    ],
  },
  LATE: {
    title: 'Extended',
    summary: 'Stretched · stop chasing',
    lines: [
      '► Avoid new entries — late-stage exhaustion risk',
      '► Hold-only: tighten stops if already in position',
    ],
  },
  UNKNOWN: {
    title: 'Sideways',
    summary: 'No clear direction yet',
    lines: [
      '► Wait for the stock to declare — Breakout or breakdown',
      '► No system signal in this phase',
    ],
  },
};

export const LIFECYCLE_ORDER: LifecycleTag[] = [
  'INITIAL',
  'CONFIRMED',
  'LATE',
  'UNKNOWN',
];

// ──────────────────────────────────────────────────────────────────────────
// §13 Phase D catalyst-type → user-facing label.
// ──────────────────────────────────────────────────────────────────────────
export const CATALYST_LABEL: Record<CatalystType, string> = {
  earnings_beat: 'Earnings beat',
  guidance_raise: 'Guidance raise',
  buyback: 'Buyback',
  management_change: 'Mgmt change',
  m_and_a: 'M&A',
  policy_tailwind: 'Policy tailwind',
  fii_increase: 'FII increase',
  dii_increase: 'DII increase',
  promoter_buying: 'Promoter buying',
  block_deal_buy: 'Block deal',
  sector_momentum: 'Sector momentum',
};

export type CatalystTone = 'positive' | 'caution' | 'neutral';

// Mostly positive types; mgmt change is neutral-to-cautionary depending
// on context — UI defaults to neutral and text content carries the
// signal interpretation.
export const CATALYST_TONE: Record<CatalystType, CatalystTone> = {
  earnings_beat: 'positive',
  guidance_raise: 'positive',
  buyback: 'positive',
  management_change: 'neutral',
  m_and_a: 'neutral',
  policy_tailwind: 'positive',
  fii_increase: 'positive',
  dii_increase: 'positive',
  promoter_buying: 'positive',
  block_deal_buy: 'positive',
  sector_momentum: 'positive',
};

export function catalystLabel(type: CatalystType): string {
  return CATALYST_LABEL[type] ?? type;
}

export const FRESHNESS_LABEL: Record<FreshnessTag, string> = {
  FRESH: 'Fresh',
  RECENT: 'Recent',
  STALE: 'Stale',
};
