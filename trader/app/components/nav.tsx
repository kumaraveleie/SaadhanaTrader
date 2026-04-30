'use client';

import Link from 'next/link';
import { useTheme } from './theme';
import { BrandMark } from './brand-mark';

const NAV_LINKS = [
  { href: '/scanner', label: 'Scanner' },
  { href: '/research', label: 'Research' },
  { href: '/about', label: 'About' },
];

export function Nav() {
  const { t } = useTheme();
  return (
    <nav
      style={{
        padding: '20px clamp(20px, 5vw, 64px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: `1px solid ${t.border}`,
        background: t.bg,
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backdropFilter: 'blur(8px)',
      }}
    >
      <Link href="/" style={{ textDecoration: 'none', color: t.text, display: 'inline-flex' }}>
        <BrandMark size={32} color={t.text} accent={t.accent} />
      </Link>

      <div
        className="saadhana-nav-links"
        style={{ display: 'flex', gap: 28, alignItems: 'center', fontSize: 14 }}
      >
        {NAV_LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            style={{ color: t.text2, fontWeight: 500, textDecoration: 'none' }}
          >
            {l.label}
          </Link>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <Link
          href="/scanner"
          style={{
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            borderRadius: 8,
            background: t.accent,
            color: t.bg,
            cursor: 'pointer',
            textDecoration: 'none',
            letterSpacing: '-0.01em',
          }}
        >
          Open Scanner →
        </Link>
      </div>
    </nav>
  );
}
