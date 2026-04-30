'use client';

import Link from 'next/link';
import { BrandMark } from './components/brand-mark';
import { useTheme } from './components/theme';

/**
 * K1.1 placeholder home — minimal shell verification.
 * Real hero + today's top-picks card grid lands after K1.1 sign-off.
 */
export default function HomePage() {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 880, margin: '40px auto', textAlign: 'center' }}>
      <div style={{ marginBottom: 32, display: 'flex', justifyContent: 'center' }}>
        <BrandMark size={72} color={t.text} accent={t.accent} showWordmark={false} />
      </div>
      <h1
        style={{
          fontSize: 'clamp(40px, 6vw, 72px)',
          fontWeight: 700,
          letterSpacing: '-0.04em',
          lineHeight: 1.05,
          margin: 0,
          color: t.text,
        }}
      >
        The rules don&apos;t blink.
      </h1>
      <p
        style={{
          marginTop: 20,
          fontSize: 18,
          color: t.text2,
          lineHeight: 1.55,
          maxWidth: 640,
          marginInline: 'auto',
        }}
      >
        Saadhana Trader scans the Nifty 500 every evening, applies the same
        13 technical conditions and a fundamental quality gate to every
        symbol, and surfaces the names where every box is checked. Same
        input, same output, every time.
      </p>
      <div
        style={{
          marginTop: 40,
          display: 'flex',
          gap: 12,
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}
      >
        <Link
          href="/scanner"
          style={{
            padding: '14px 24px',
            background: t.accent,
            color: t.bg,
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 14,
            letterSpacing: '-0.01em',
          }}
        >
          Open scanner →
        </Link>
        <Link
          href="/about"
          style={{
            padding: '14px 24px',
            border: `1px solid ${t.border}`,
            color: t.text,
            borderRadius: 8,
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          How it works
        </Link>
      </div>
      <p
        style={{
          marginTop: 64,
          fontSize: 12,
          color: t.text3,
          fontFamily: 'var(--font-mono), ui-monospace, monospace',
        }}
      >
        K1.1 shell verification · scanner page lands at K1.2
      </p>
    </div>
  );
}
