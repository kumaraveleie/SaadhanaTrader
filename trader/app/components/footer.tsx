'use client';

import Link from 'next/link';
import { useTheme } from './theme';
import { BrandMark } from './brand-mark';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function Footer() {
  const { t } = useTheme();
  const cols = [
    { title: 'Product', items: ['Scanner', 'Stocks', 'How it works'] },
    { title: 'Resources', items: ['Methodology', 'Pro-Setup score', 'FAQ'] },
    { title: 'Company', items: ['About', 'Contact'] },
    { title: 'Legal', items: ['Privacy', 'Terms', 'Disclaimer'] },
  ];
  return (
    <footer
      style={{
        background: t.surface,
        borderTop: `1px solid ${t.border}`,
        padding: '64px clamp(20px, 5vw, 64px) 32px',
        marginTop: 80,
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div
          className="saadhana-footer-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: '1.4fr repeat(4, 1fr)',
            gap: 32,
          }}
        >
          <div>
            <BrandMark size={28} color={t.text} accent={t.accent} />
            <p
              style={{
                fontSize: 14,
                color: t.text2,
                marginTop: 16,
                maxWidth: 280,
                lineHeight: 1.5,
              }}
            >
              Indian cash-equity pattern detection. Disciplined practice — same input,
              same output, every time.
            </p>
          </div>
          {cols.map((c) => (
            <div key={c.title}>
              <div
                style={{
                  fontSize: 12,
                  color: t.text3,
                  fontWeight: 600,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  marginBottom: 14,
                  fontFamily: FONT_MONO,
                }}
              >
                {c.title}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {c.items.map((i) => (
                  <a key={i} style={{ fontSize: 14, color: t.text2, cursor: 'pointer' }}>
                    {i}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* §21.1 SEBI disclaimer — sitewide, replaces per-panel compliance copy */}
        <div
          style={{
            marginTop: 48,
            paddingTop: 24,
            borderTop: `1px solid ${t.border}`,
            fontSize: 12,
            color: t.text3,
            lineHeight: 1.6,
          }}
        >
          <div style={{ marginBottom: 8 }}>
            Saadhana Trader is a research tool — information only, not investment
            advice. Not SEBI-registered.
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 12 }}>
            <Link
              href="/about"
              style={{ color: t.text2, textDecoration: 'underline', textUnderlineOffset: 2 }}
            >
              About
            </Link>
            <span style={{ color: t.text3 }}>·</span>
            <Link
              href="/about/phases"
              style={{ color: t.text2, textDecoration: 'underline', textUnderlineOffset: 2 }}
            >
              Phases
            </Link>
            <span style={{ color: t.text3 }}>·</span>
            <Link
              href="/about"
              style={{ color: t.text2, textDecoration: 'underline', textUnderlineOffset: 2 }}
            >
              Disclaimer
            </Link>
          </div>
        </div>

        <div
          style={{
            marginTop: 24,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: 12.5,
            color: t.text3,
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <span>© 2026 Saadhana Trader · Research dashboard · All rights reserved.</span>
          <div style={{ display: 'flex', gap: 14 }}>
            <a href="https://github.com/kumaraveleie/SaadhanaTrader" style={{ color: t.text3, cursor: 'pointer' }}>
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
