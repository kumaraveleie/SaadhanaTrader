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
        Research data unavailable
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
        No research snapshot to display
      </h1>
      <p style={{ fontSize: 15, color: t.text2, lineHeight: 1.6 }}>
        The latest research snapshot (<code style={{ color: t.text3 }}>signals/research.json</code>)
        could not be read. Run <code style={{ color: t.text3 }}>scripts/research_scan.py</code> to
        regenerate it, or check back after the next end-of-day update.
      </p>
    </div>
  );
}
