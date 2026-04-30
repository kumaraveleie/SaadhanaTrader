'use client';

import { useTheme } from './theme';
import { publicLabel } from '../lib/labels';
import type { SignalState } from '../lib/scan-types';

/**
 * §21.1 / design_system §5 — Signal pill.
 * Always renders the public-mode label; never the raw internal label.
 * Color comes from the design-system semantic token table (BUY/HOLD/
 * SELL/WATCH).
 */
export function SignalPill({ signal }: { signal: SignalState }) {
  const { t } = useTheme();
  const label = publicLabel(signal).text;
  const visual = visualFor(signal, t);
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '4px 10px',
        borderRadius: 6,
        background: visual.bg,
        color: visual.fg,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

function visualFor(
  signal: SignalState,
  t: ReturnType<typeof useTheme>['t'],
): { bg: string; fg: string } {
  switch (signal) {
    case 'BUY':
      return { bg: t.accentSoft, fg: t.bullish };
    case 'HOLD':
      return { bg: 'rgba(0,200,255,0.12)', fg: t.info };
    case 'SELL':
      return { bg: 'rgba(255,51,102,0.12)', fg: t.bearish };
    case 'WATCH':
      return { bg: 'rgba(255,184,0,0.12)', fg: t.warning };
    default:
      return { bg: 'rgba(255,255,255,0.04)', fg: t.text3 };
  }
}
