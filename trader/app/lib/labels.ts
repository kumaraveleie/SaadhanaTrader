/**
 * §21.1 public-mode label translation.
 *
 * Internal labels (BUY / HOLD / SELL / WATCH / WAIT) are NEVER rendered
 * directly in user-facing JSX. Always go through this mapping. The
 * public domain treats Saadhana as a research / pattern-detection tool;
 * the wording reflects that framing. Personal-mode (Phase K2) uses the
 * raw internal labels.
 */

import type { Regime, SignalState } from './scan-types';

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
