'use client';

import { useTheme } from './theme';
import { scanAgeDays } from '../lib/scan-types';

/**
 * §15 / design_system §5 — "Live data indicator" pulse.
 * Color shifts based on scan age:
 *   0 days (today)     → bullish green (live-ish)
 *   1 day              → warning amber (yesterday)
 *   ≥ 2 days           → text3 grey (stale)
 *
 * The dot pulses via the ``pulse`` keyframes in globals.css.
 */
export function FreshnessIndicator({ scanDate }: { scanDate: string }) {
  const { t } = useTheme();
  const ageDays = scanAgeDays(scanDate);
  const dotColor =
    ageDays === 0 ? t.bullish : ageDays === 1 ? t.warning : t.text3;
  const ageText =
    ageDays === 0 ? 'Today' : ageDays === 1 ? 'Yesterday' : `${ageDays} days old`;
  const isStale = ageDays >= 2;
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 13,
        color: isStale ? t.warning : t.text2,
        fontFamily: 'var(--font-mono), ui-monospace, monospace',
      }}
    >
      <span
        aria-hidden
        style={{
          display: 'inline-block',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dotColor,
          animation: ageDays <= 1 ? 'pulse 2s ease-in-out infinite' : undefined,
        }}
      />
      EOD · {scanDate} · {ageText}
      {isStale && (
        <span
          style={{
            marginLeft: 6,
            padding: '2px 8px',
            borderRadius: 4,
            background: 'rgba(255,184,0,0.12)',
            color: t.warning,
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          Stale
        </span>
      )}
    </div>
  );
}
