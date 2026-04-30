'use client';

import { useTheme } from '../components/theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Sector Strength panel — placeholder for the full Phase Q / M1 Sector
 * Strength Engine (see spec/thinking_engine.md §3.1). The full module
 * lands post-MVP; this card explicitly states what's coming so users
 * see the placeholder for what it is rather than thinking the page is
 * unfinished.
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
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: t.text, letterSpacing: '-0.02em' }}>
          Sector Strength
        </h2>
        <p style={{ fontSize: 13, color: t.text3, margin: '6px 0 0', lineHeight: 1.55, maxWidth: 800 }}>
          Multi-window sector relative strength (5d / 20d / 60d / 252d), sector
          breadth (% above 50-DMA / 200-DMA / Stage 2), volume sustainability,
          lead / confirming / mature / fading tier classifier.
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
            marginBottom: 12,
          }}
        >
          Phase Q · M1 — pending
        </div>
        <p style={{ fontSize: 14, color: t.text2, margin: 0, lineHeight: 1.6, maxWidth: 560, marginInline: 'auto' }}>
          The full Sector Strength Engine ships as Module M1 of the Thinking
          Engine roadmap (see <code style={{ color: t.text3 }}>spec/thinking_engine.md</code> §3.1).
          This card will render the heatmap and lead-tier list when M1 lands.
        </p>
      </div>
    </section>
  );
}
