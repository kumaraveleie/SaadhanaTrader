'use client';

import Link from 'next/link';
import { useTheme } from './theme';

/**
 * Layout-level §21.1 disclaimer banner. Sits below `<Nav />` on every
 * page in public mode (NEXT_PUBLIC_MODE !== 'personal'). Per CLAUDE.md
 * "Compliance reminders": editing this requires touching app/layout.tsx,
 * not a per-page choice.
 */
export function DisclaimerBanner() {
  const { t } = useTheme();
  return (
    <div
      role="region"
      aria-label="Compliance disclaimer"
      style={{
        padding: '8px clamp(20px, 5vw, 64px)',
        background: 'rgba(255,184,0,0.08)',
        borderBottom: `1px solid ${t.border}`,
        fontSize: 12,
        color: t.text2,
        textAlign: 'center',
        lineHeight: 1.5,
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
