'use client';

import { useTheme } from '../../components/theme';
import { regimeLabel } from '../../lib/labels';
import type { CandidateRow, Regime } from '../../lib/scan-types';
import { ConditionChecklist } from './condition-checklist';
import { RiskLevelsCard } from './risk-levels-card';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Self-contained "Pattern" card. Renders the condition checklist +
 * risk levels when the symbol is a candidate today, otherwise renders
 * an empty state explaining why no pattern fired. Either way the
 * catalyst card on the same page renders independently.
 */
export function PatternSection({
  candidate,
  regime,
  scanDate,
}: {
  candidate: CandidateRow | null;
  regime: Regime;
  scanDate: string;
}) {
  const { t } = useTheme();

  if (!candidate) {
    return (
      <Card title="Pattern" subtitle="Saadhana's 13-condition technical match">
        <EmptyBody regime={regime} scanDate={scanDate} />
      </Card>
    );
  }

  return (
    <Card title="Pattern" subtitle="Saadhana's 13-condition technical match">
      <div
        className="saadhana-stock-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)',
          gap: 24,
        }}
      >
        <ConditionChecklist failedConditions={candidate.failed_conditions} />
        <RiskLevelsCard candidate={candidate} />
      </div>
    </Card>
  );
}

function EmptyBody({
  regime,
  scanDate,
}: {
  regime: Regime;
  scanDate: string;
}) {
  const { t } = useTheme();
  const market = regimeLabel(regime).text;
  return (
    <div
      style={{
        padding: '24px 8px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 11,
          color: t.text3,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          marginBottom: 10,
        }}
      >
        No qualifying pattern today
      </div>
      <p
        style={{
          fontSize: 14,
          color: t.text2,
          margin: 0,
          lineHeight: 1.6,
          maxWidth: 520,
          marginInline: 'auto',
        }}
      >
        On the latest scan ({scanDate}), this stock didn&apos;t match the
        full 13-condition pattern set. Market read at scan time was{' '}
        <strong style={{ color: t.text }}>{market}</strong>.
        {regime === 'Risk_Off' && (
          <>
            {' '}Our trading rules pause new pattern matches when the
            broader market trades below its 200-day moving average —
            capital preservation over fear of missing out.
          </>
        )}{' '}
        Catalysts and sector context below are independent of the
        pattern check.
      </p>
    </div>
  );
}

function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const { t } = useTheme();
  return (
    <section
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 14,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          padding: '16px 22px',
          borderBottom: `1px solid ${t.border}`,
        }}
      >
        <h2
          style={{
            fontSize: 16,
            fontWeight: 700,
            margin: 0,
            color: t.text,
            letterSpacing: '-0.02em',
          }}
        >
          {title}
        </h2>
        {subtitle && (
          <p
            style={{
              fontSize: 12,
              color: t.text3,
              margin: '4px 0 0',
              fontFamily: FONT_MONO,
            }}
          >
            {subtitle}
          </p>
        )}
      </header>
      <div style={{ padding: '20px 22px' }}>{children}</div>
    </section>
  );
}
