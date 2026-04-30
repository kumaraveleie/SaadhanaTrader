'use client';

import { useTheme } from '../../components/theme';
import type { CandidateRow } from '../../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * §5.4 + §7 risk levels card. Renders ONLY for BUY candidates — the
 * risk_levels are computed at signal time and only attached to the
 * BUY-row payload per ``_decision_to_row`` in scan/daily.py.
 *
 * For HOLD / SELL / WATCH the card collapses to a "no fresh entry
 * levels today" message; entry happened on a prior scan day, so the
 * current row carries no entry/stop/target.
 */
export function RiskLevelsCard({ candidate }: { candidate: CandidateRow }) {
  const { t } = useTheme();
  const isBuy = candidate.signal === 'BUY' && candidate.entry_price !== undefined;

  return (
    <aside
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 16,
        background: t.card,
        padding: 24,
      }}
    >
      <h2
        style={{
          fontSize: 16,
          fontWeight: 700,
          margin: 0,
          color: t.text,
          letterSpacing: '-0.01em',
        }}
      >
        Technical risk levels
      </h2>
      <p
        style={{
          fontSize: 12,
          color: t.text3,
          margin: '4px 0 20px',
          lineHeight: 1.5,
        }}
      >
        Computed at signal time per the system&apos;s risk methodology.
        These are technical projections, not investment targets.
      </p>

      {isBuy ? (
        <BuyLevels candidate={candidate} />
      ) : (
        <p style={{ fontSize: 13, color: t.text2, lineHeight: 1.6 }}>
          No fresh entry levels for today — this row reflects a
          previously-matched pattern, not a new signal candidate.
        </p>
      )}
    </aside>
  );
}

function BuyLevels({ candidate }: { candidate: CandidateRow }) {
  const { t } = useTheme();
  const rows: { label: string; value: string; tone?: string }[] = [
    {
      label: 'Reference price',
      value: fmtRupee(candidate.entry_price!),
    },
    {
      label: 'Technical risk level',
      value: fmtRupee(candidate.stop_loss!),
      tone: t.bearish,
    },
    {
      label: 'Technical projection T1',
      value: fmtRupee(candidate.target_t1!),
      tone: t.info,
    },
    {
      label: 'Technical projection T2',
      value: fmtRupee(candidate.target_t2!),
      tone: t.info,
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {rows.map((r) => (
          <div
            key={r.label}
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              gap: 16,
              borderBottom: `1px solid ${t.border}`,
              paddingBottom: 12,
            }}
          >
            <span style={{ fontSize: 13, color: t.text2 }}>{r.label}</span>
            <span
              style={{
                fontFamily: FONT_MONO,
                fontSize: 16,
                fontWeight: 600,
                color: r.tone ?? t.text,
              }}
            >
              {r.value}
            </span>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 20,
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 8,
        }}
      >
        <Stat label="Risk" value={`${(candidate.risk_pct! * 100).toFixed(2)}%`} />
        <Stat label="Reward" value={`${(candidate.reward_pct! * 100).toFixed(2)}%`} />
        <Stat label="R/R" value={candidate.rr_ratio!.toFixed(2)} />
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  const { t } = useTheme();
  return (
    <div
      style={{
        padding: '10px 12px',
        background: t.surface,
        borderRadius: 8,
        border: `1px solid ${t.border}`,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: t.text3,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          fontFamily: FONT_MONO,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: t.text,
          marginTop: 2,
          fontFamily: FONT_MONO,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function fmtRupee(n: number): string {
  return `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
