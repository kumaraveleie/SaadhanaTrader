'use client';

import Link from 'next/link';
import { useTheme } from '../components/theme';
import { LifecycleTag } from './lifecycle-tag';
import type { ResearchRow } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * 52WH Breakout Watch — universe-wide names within 5% of 52WH with
 * healthy momentum (RSI 50-75) and positive 30-bar inst flow score.
 * Visible in all regimes; ranked by closest-to-52WH first.
 */
export function Breakout52whPanel({ rows }: { rows: ResearchRow[] }) {
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
          52-Week High Breakout Watch
        </h2>
        <p style={{ fontSize: 13, color: t.text3, margin: '6px 0 0', lineHeight: 1.55, maxWidth: 800 }}>
          Tier-1-passing names within 5% of their 52-week high with healthy momentum
          (RSI 50–75) and positive 30-bar institutional flow. <strong style={{ color: t.text2 }}>
          Universe-wide — visible regardless of regime</strong>; the §12 trading rule still
          gates BUYs. Top 20 by 52WH proximity.
        </p>
      </header>

      {rows.length === 0 ? (
        <div style={{ padding: '36px 24px', textAlign: 'center' }}>
          <p style={{ fontSize: 14, color: t.text2, margin: 0, lineHeight: 1.6 }}>
            No symbols currently within 5% of 52WH with the momentum + accumulation
            criteria. The bear regime has pulled most names well below their highs.
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                {[
                  { label: 'Symbol', align: 'left' as const },
                  { label: 'Sector', align: 'left' as const },
                  { label: 'Dist 52WH', align: 'right' as const },
                  { label: 'Lifecycle', align: 'left' as const },
                  { label: 'RSI', align: 'right' as const },
                  { label: 'Score', align: 'right' as const },
                  { label: 'Inst flow 30b', align: 'right' as const },
                ].map((h) => (
                  <th
                    key={h.label}
                    style={{
                      padding: '12px 14px',
                      textAlign: h.align,
                      fontSize: 11,
                      fontWeight: 600,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: t.text3,
                      background: t.surface,
                      borderBottom: `1px solid ${t.border}`,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} style={{ borderTop: `1px solid ${t.border}` }}>
                  <td style={{ padding: '12px 14px' }}>
                    <Link
                      href={`/stock/${encodeURIComponent(r.symbol)}`}
                      style={{ color: t.text, fontWeight: 600, fontFamily: FONT_MONO }}
                    >
                      {r.symbol}
                    </Link>
                  </td>
                  <td style={{ padding: '12px 14px', color: t.text3, fontSize: 12 }}>
                    {r.sector}
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
                    {(r.dist_from_52wh_pct * 100).toFixed(2)}%
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <LifecycleTag tag={r.lifecycle} />
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
                    {r.rsi_14.toFixed(0)}
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: r.pro_setup_score >= 11 ? t.bullish : t.text2 }}>
                    {r.pro_setup_score}/13
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: r.inst_flow_score_30b > 0 ? t.bullish : t.text2 }}>
                    {r.inst_flow_score_30b > 0 ? '+' : ''}{r.inst_flow_score_30b}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
