'use client';

import { useTheme } from '../components/theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * K1.2 placeholder. The real scanner page (sortable results table,
 * universe selector, stale-data indicator, Risk_Off empty state, Tier 1
 * failures hidden) lands after K1.1 sign-off.
 */
export default function ScannerPage() {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 720, margin: '40px auto', textAlign: 'center' }}>
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
        K1.2 — In progress
      </div>
      <h1
        style={{
          fontSize: 'clamp(28px, 4vw, 36px)',
          fontWeight: 700,
          margin: '0 0 16px',
          color: t.text,
          letterSpacing: '-0.03em',
        }}
      >
        Scanner page is being built
      </h1>
      <p style={{ fontSize: 16, color: t.text2, lineHeight: 1.6 }}>
        The full scanner — universe selector, sortable results table,
        stale-data indicator, Risk-Off empty state — lands at the next
        K1.2 checkpoint. Until then this stub keeps the navigation links
        intact so you can verify the layout shell without 404s.
      </p>
    </div>
  );
}
