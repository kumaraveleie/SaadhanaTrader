'use client';

import { useTheme } from '../components/theme';
import type { LifecycleTag as Tag } from '../lib/scan-types';

const VISUALS: Record<Tag, { label: string; tone: string; bg: string }> = {
  INITIAL: { label: 'INITIAL', tone: '#00FF88', bg: 'rgba(0,255,136,0.12)' },
  CONFIRMED: { label: 'CONFIRMED', tone: '#00C8FF', bg: 'rgba(0,200,255,0.12)' },
  LATE: { label: 'LATE', tone: '#FFB800', bg: 'rgba(255,184,0,0.14)' },
  UNKNOWN: { label: 'UNKNOWN', tone: '#6B7280', bg: 'rgba(107,114,128,0.12)' },
};

/**
 * Lifecycle tag pill — colored per design_system §5 mapping.
 * INITIAL=bullish, CONFIRMED=info, LATE=warning, UNKNOWN=text3.
 */
export function LifecycleTag({ tag }: { tag: Tag }) {
  const v = VISUALS[tag];
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        background: v.bg,
        color: v.tone,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '0.06em',
        whiteSpace: 'nowrap',
      }}
    >
      {v.label}
    </span>
  );
}
