'use client';

import Link from 'next/link';
import { useTheme } from '../../components/theme';
import { SignalPill } from '../../components/signal-pill';
import { FreshnessIndicator } from '../../components/freshness-indicator';
import { publicLabel } from '../../lib/labels';
import type { CandidateRow } from '../../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function StockHeader({
  candidate,
  scanDate,
}: {
  candidate: CandidateRow;
  scanDate: string;
}) {
  const { t } = useTheme();
  const label = publicLabel(candidate.signal);

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
              {candidate.symbol}
            </div>
            <SignalPill signal={candidate.signal} />
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
          {label.description}
        </p>

        <div
          style={{
            marginTop: 24,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 12,
          }}
        >
          <KV
            label="Pro-Setup score"
            value={`${candidate.pro_setup_score}/13`}
            valueColor={candidate.pro_setup_score === 13 ? t.bullish : t.text}
          />
          <KV
            label="Drawdown resistance"
            value={`${Math.round(candidate.drs)} / 100`}
          />
          <KV label="Regime" value={candidate.regime.replace('_', '-')} />
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
