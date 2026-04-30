'use client';

import Link from 'next/link';
import { useTheme } from './theme';

/**
 * Layout-level §21.1 disclaimer banner. Sits **above** ``<Footer />``
 * on every page in public mode (NEXT_PUBLIC_MODE !== 'personal'). Per
 * CLAUDE.md "Compliance reminders": editing this requires touching
 * ``app/layout.tsx``, not a per-page choice.
 *
 * Placement note: bottom-anchored (above footer) per design_system.md
 * §5 v2 — moved there because the top placement squeezed the hero on
 * mobile and ate scanner-page real estate. Bottom keeps the disclaimer
 * persistent and visible without competing with primary content.
 */
export function DisclaimerBanner() {
  const { t } = useTheme();
  return (
    <div
      role="region"
      aria-label="Compliance disclaimer"
      style={{
        padding: '14px clamp(20px, 5vw, 64px)',
        background: 'rgba(255,184,0,0.08)',
        borderTop: `1px solid ${t.border}`,
        borderBottom: `1px solid ${t.border}`,
        fontSize: 14,
        color: t.text2,
        textAlign: 'center',
        lineHeight: 1.55,
      }}
    >
      Saadhana Trader is a research and pattern-detection tool.
      Information only. Not investment advice.{' '}
      <Link href="/about" style={{ color: t.accent, fontWeight: 500 }}>
        Read the full disclaimer →
      </Link>
    </div>
  );
}
