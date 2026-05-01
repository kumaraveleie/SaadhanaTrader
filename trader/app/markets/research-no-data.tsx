'use client';

import { useTheme } from '../components/theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function ResearchNoData() {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 720, margin: '60px auto', textAlign: 'center' }}>
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 12,
          color: t.text3,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          marginBottom: 16,
        }}
      >
        Market data unavailable
      </div>
      <h1
        style={{
          fontSize: 'clamp(24px, 3vw, 32px)',
          fontWeight: 700,
          margin: '0 0 16px',
          color: t.text,
          letterSpacing: '-0.03em',
        }}
      >
        Today&apos;s market snapshot couldn&apos;t be loaded
      </h1>
      <p style={{ fontSize: 15, color: t.text2, lineHeight: 1.6 }}>
        The nightly end-of-day update may not have completed yet. Check
        back after the next session close.
      </p>
    </div>
  );
}
