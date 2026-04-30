/**
 * §21.1 public-mode label translation.
 *
 * Internal labels (BUY / HOLD / SELL / WATCH / WAIT) are NEVER rendered
 * directly in user-facing JSX. Always go through this mapping. The
 * public domain treats Saadhana as a research / pattern-detection tool;
 * the wording reflects that framing. Personal-mode (Phase K2) uses the
 * raw internal labels.
 */

import type { SignalState } from './scan-types';

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
