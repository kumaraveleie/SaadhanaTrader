'use client';

import { LIFECYCLE_DISPLAY, type PhaseTone } from '../lib/labels';
import type { LifecycleTag as Tag } from '../lib/scan-types';

const TONE_COLOR: Record<PhaseTone, { fg: string; bg: string }> = {
  bullish: { fg: '#00FF88', bg: 'rgba(0,255,136,0.12)' },
  info: { fg: '#00C8FF', bg: 'rgba(0,200,255,0.12)' },
  warning: { fg: '#FFB800', bg: 'rgba(255,184,0,0.14)' },
  muted: { fg: '#9CA3AF', bg: 'rgba(107,114,128,0.12)' },
};

/**
 * Lifecycle tag pill — internal key in, plain-English label out.
 * Internal keys (INITIAL/CONFIRMED/LATE/UNKNOWN) flow through unchanged
 * in code; only this component performs the user-facing translation.
 */
export function LifecycleTag({ tag }: { tag: Tag }) {
  const display = LIFECYCLE_DISPLAY[tag];
  const tone = TONE_COLOR[display.tone];
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        background: tone.bg,
        color: tone.fg,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '0.06em',
        whiteSpace: 'nowrap',
        textTransform: 'uppercase',
      }}
    >
      {display.label}
    </span>
  );
}
