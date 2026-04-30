'use client';

import { useTheme } from '../components/theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Placeholder for the Sector Strength engine. Surfaces what's coming so
 * the empty card reads as deliberate rather than unfinished.
 */
export function SectorStrengthPanel() {
  const { t } = useTheme();
  return (
    <section
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 16,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <header style={{ padding: '20px 24px', borderBottom: `1px solid ${t.border}` }}>
        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            margin: 0,
            color: t.text,
            letterSpacing: '-0.02em',
          }}
        >
          Sector Strength
        </h2>
        <p
          style={{
            fontSize: 13,
            color: t.text3,
            margin: '6px 0 0',
            lineHeight: 1.55,
            maxWidth: 720,
          }}
        >
          Which sectors are leading the market — and which are quietly
          falling behind.
        </p>
      </header>

      <div style={{ padding: '36px 24px', textAlign: 'center' }}>
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 11,
            color: t.text3,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            marginBottom: 10,
          }}
        >
          Coming next
        </div>
        <p
          style={{
            fontSize: 14,
            color: t.text2,
            margin: 0,
            lineHeight: 1.6,
            maxWidth: 520,
            marginInline: 'auto',
          }}
        >
          A heatmap of sector relative strength and breadth, with lead /
          mature / fading classifications. Will appear here when ready.
        </p>
      </div>
    </section>
  );
}
