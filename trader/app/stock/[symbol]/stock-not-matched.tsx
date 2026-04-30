'use client';

import Link from 'next/link';
import { useTheme } from '../../components/theme';
import type { Regime } from '../../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

type Props = {
  symbol: string;
  reason: 'no_scan' | 'not_in_candidates';
  regime?: Regime;
  scanDate?: string;
};

/**
 * Renders when a /stock/[symbol] route resolves to a symbol that
 * isn't in today's ``candidates`` list (or the scan file is missing).
 *
 * Two cases:
 *   - ``no_scan``: the JSON file is missing/corrupt — infrastructure
 *     problem, not a market outcome.
 *   - ``not_in_candidates``: the symbol either didn't qualify today
 *     OR isn't in the scan universe at all. We can't distinguish the
 *     two without echoing the universe list to the client; the copy
 *     covers both cases.
 */
export function StockNotMatched({ symbol, reason, regime, scanDate }: Props) {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 720, margin: '40px auto' }}>
      <Link
        href="/scanner"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 13,
          color: t.text2,
          marginBottom: 16,
        }}
      >
        ← Back to scanner
      </Link>

      <div
        style={{
          padding: 36,
          border: `1px solid ${t.border}`,
          borderRadius: 16,
          background: t.card,
          textAlign: 'center',
        }}
      >
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 28,
            fontWeight: 700,
            color: t.text,
            letterSpacing: '0.01em',
            marginBottom: 8,
          }}
        >
          {symbol}
        </div>
        <div
          style={{
            display: 'inline-block',
            padding: '4px 10px',
            borderRadius: 6,
            background: 'rgba(255,255,255,0.04)',
            color: t.text3,
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            marginBottom: 24,
          }}
        >
          No qualifying pattern today
        </div>

        {reason === 'no_scan' ? (
          <p style={{ fontSize: 15, color: t.text2, lineHeight: 1.65 }}>
            Scan output is unavailable right now (the nightly cron may not
            have completed yet, or the deploy is missing the file). Check
            back after the next end-of-day update.
          </p>
        ) : (
          <>
            <p style={{ fontSize: 15, color: t.text2, lineHeight: 1.65 }}>
              On the latest scan ({scanDate}), {symbol} did not match the
              full 13-condition pattern set, or is outside the system&apos;s
              scan universe (Nifty 500, industrial sectors). The scan
              ran in <strong style={{ color: t.text }}>{regimeLabel(regime)}</strong>{' '}
              regime.
              {regime === 'Risk_Off' && (
                <>
                  {' '}
                  Per spec §12, the system suspends new pattern matches when
                  the broader market trades below its 200-day moving average —
                  capital preservation over fear of missing out.
                </>
              )}
            </p>
            <Link
              href="/scanner"
              style={{
                display: 'inline-block',
                marginTop: 28,
                padding: '12px 22px',
                background: t.accent,
                color: t.bg,
                borderRadius: 8,
                fontWeight: 600,
                fontSize: 14,
                letterSpacing: '-0.01em',
              }}
            >
              See today&apos;s matches →
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

function regimeLabel(regime?: Regime): string {
  if (!regime) return 'Unknown';
  switch (regime) {
    case 'Risk_On':
      return 'Risk-On';
    case 'Caution':
      return 'Caution';
    case 'Risk_Off':
      return 'Risk-Off';
  }
}
