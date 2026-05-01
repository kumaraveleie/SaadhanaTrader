'use client';

import Link from 'next/link';
import { BrandMark } from './components/brand-mark';
import { RegimeRibbon } from './components/regime-ribbon';
import { useTheme } from './components/theme';
import type { Regime, SectorStrength } from './lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function HomeClient({
  regime,
  niftyPctChange,
  topSectors,
}: {
  regime: Regime | null;
  niftyPctChange: number | null;
  topSectors: SectorStrength[];
}) {
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

      {regime !== null && niftyPctChange !== null && (
        <div style={{ marginTop: 36, maxWidth: 640, marginInline: 'auto' }}>
          <RegimeRibbon
            regime={regime}
            niftyPctChange={niftyPctChange}
            footer={<StrongestToday sectors={topSectors} />}
          />
        </div>
      )}

      <p
        style={{
          marginTop: 56,
          fontSize: 12,
          color: t.text3,
          fontFamily: FONT_MONO,
        }}
      >
        Built for Indian cash equity · EOD signals
      </p>
    </div>
  );
}

function StrongestToday({ sectors }: { sectors: SectorStrength[] }) {
  const { t } = useTheme();
  if (sectors.length === 0) return null;
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 8,
        fontSize: 12,
        fontFamily: FONT_MONO,
        color: t.text2,
      }}
    >
      <span style={{ color: t.text3 }}>Strongest today:</span>
      {sectors.map((s, i) => {
        const pct = s.today_pct * 100;
        const tone = pct > 0 ? t.bullish : pct < 0 ? t.bearish : t.text2;
        return (
          <span
            key={s.sector}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <Link
              href={`/markets`}
              style={{
                color: t.text,
                textDecoration: 'none',
                fontWeight: 500,
              }}
            >
              {s.sector_label}
            </Link>
            <span style={{ color: tone, fontWeight: 600 }}>
              {pct >= 0 ? '+' : ''}
              {pct.toFixed(1)}%
            </span>
            {i < sectors.length - 1 && <span style={{ color: t.text3 }}>·</span>}
          </span>
        );
      })}
    </div>
  );
}
