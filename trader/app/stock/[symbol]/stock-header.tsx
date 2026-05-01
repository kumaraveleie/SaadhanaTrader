'use client';

import Link from 'next/link';
import { useTheme } from '../../components/theme';
import { SignalPill } from '../../components/signal-pill';
import { FreshnessIndicator } from '../../components/freshness-indicator';
import { publicLabel, regimeLabel } from '../../lib/labels';
import type { CandidateRow, Regime, ResearchRow } from '../../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * /stock/[symbol] header. Renders for any symbol that exists in either
 * the daily scan (`latest.json` candidates) OR the research snapshot
 * (`research.json` rows) — pattern-match status is independent of
 * sector / price / catalyst data.
 *
 * Fallback chain for each field: candidate → research row → null.
 * The signal pill is omitted when the symbol isn't a candidate today.
 */
export function StockHeader({
  symbol,
  candidate,
  researchRow,
  regime,
  scanDate,
}: {
  symbol: string;
  candidate: CandidateRow | null;
  researchRow: ResearchRow | null;
  regime: Regime;
  scanDate: string;
}) {
  const { t } = useTheme();
  const description = candidate
    ? publicLabel(candidate.signal).description
    : `End-of-day snapshot for ${symbol} on ${scanDate}. Pattern, catalyst, and sector context below.`;

  const proSetupScore =
    candidate?.pro_setup_score ?? researchRow?.pro_setup_score ?? null;
  const sector = researchRow?.sub_industry ?? null;
  const closeToday = researchRow?.close_today ?? null;
  const pctChange = researchRow?.pct_change_today ?? null;
  const pctTone =
    pctChange === null
      ? t.text2
      : pctChange > 0
      ? t.bullish
      : pctChange < 0
      ? t.bearish
      : t.text2;
  const regimeText = regimeLabel(regime).text;

  return (
    <div>
      <Link
        href="/scanner"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 13,
          color: t.text2,
          marginBottom: 12,
          textDecoration: 'none',
        }}
      >
        ← Back to scanner
      </Link>

      <div
        style={{
          padding: 28,
          border: `1px solid ${t.border}`,
          borderRadius: 16,
          background: t.card,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 16,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontFamily: FONT_MONO,
                fontSize: 28,
                fontWeight: 700,
                color: t.text,
                letterSpacing: '0.01em',
                marginBottom: 6,
              }}
            >
              {symbol}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              {candidate && <SignalPill signal={candidate.signal} />}
              {sector && (
                <span
                  style={{
                    fontSize: 12,
                    color: t.text3,
                    fontFamily: FONT_MONO,
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}
                >
                  {sector}
                </span>
              )}
            </div>
          </div>
          <FreshnessIndicator scanDate={scanDate} />
        </div>

        <p
          style={{
            marginTop: 20,
            fontSize: 15,
            color: t.text2,
            lineHeight: 1.6,
            maxWidth: 720,
          }}
        >
          {description}
        </p>

        <div
          style={{
            marginTop: 24,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 12,
          }}
        >
          {closeToday !== null && (
            <KV
              label="Close"
              value={`₹${closeToday.toFixed(2)}`}
            />
          )}
          {pctChange !== null && (
            <KV
              label="Today"
              value={`${pctChange >= 0 ? '+' : ''}${(pctChange * 100).toFixed(2)}%`}
              valueColor={pctTone}
            />
          )}
          {proSetupScore !== null && (
            <KV
              label="Pro-Setup score"
              value={`${proSetupScore}/13`}
              valueColor={proSetupScore === 13 ? t.bullish : t.text}
            />
          )}
          {candidate && (
            <KV
              label="Drawdown resistance"
              value={`${Math.round(candidate.drs)} / 100`}
            />
          )}
          <KV label="Market" value={regimeText} />
        </div>
      </div>
    </div>
  );
}

function KV({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  const { t } = useTheme();
  return (
    <div>
      <div
        style={{
          fontSize: 11,
          color: t.text3,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          fontFamily: FONT_MONO,
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: valueColor ?? t.text,
        }}
      >
        {value}
      </div>
    </div>
  );
}
