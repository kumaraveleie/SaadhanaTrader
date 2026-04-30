'use client';

import { useTheme } from '../../components/theme';
import { CONDITIONS, CONDITION_GROUPS, type ConditionMeta } from '../../lib/conditions';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function ConditionChecklist({
  failedConditions,
}: {
  failedConditions: string[];
}) {
  const { t } = useTheme();
  const failedSet = new Set(failedConditions);

  return (
    <section
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 16,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <header style={{ padding: '18px 24px', borderBottom: `1px solid ${t.border}` }}>
        <h2
          style={{
            fontSize: 16,
            fontWeight: 700,
            margin: 0,
            color: t.text,
            letterSpacing: '-0.01em',
          }}
        >
          13-condition checklist
        </h2>
        <p style={{ fontSize: 13, color: t.text3, margin: '4px 0 0' }}>
          Each condition computed on the most recent closed daily bar.
          A green check means the condition fired today.
        </p>
      </header>

      {CONDITION_GROUPS.map((group) => {
        const items = CONDITIONS.filter((c) => c.group === group);
        return (
          <div key={group}>
            <div
              style={{
                padding: '12px 24px',
                background: t.surface,
                borderBottom: `1px solid ${t.border}`,
                fontSize: 11,
                fontWeight: 600,
                color: t.text3,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                fontFamily: FONT_MONO,
              }}
            >
              {group}
            </div>
            {items.map((cond) => (
              <ConditionRow
                key={cond.key}
                cond={cond}
                met={!failedSet.has(cond.key)}
              />
            ))}
          </div>
        );
      })}
    </section>
  );
}

function ConditionRow({ cond, met }: { cond: ConditionMeta; met: boolean }) {
  const { t } = useTheme();
  return (
    <div
      style={{
        padding: '14px 24px',
        borderBottom: `1px solid ${t.border}`,
        display: 'grid',
        gridTemplateColumns: '24px 1fr',
        gap: 12,
        alignItems: 'flex-start',
      }}
    >
      <span
        aria-label={met ? 'condition met' : 'condition not met'}
        style={{
          width: 22,
          height: 22,
          borderRadius: '50%',
          background: met ? t.accentSoft : 'rgba(255,51,102,0.10)',
          color: met ? t.bullish : t.bearish,
          fontSize: 13,
          fontWeight: 700,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginTop: 2,
        }}
      >
        {met ? '✓' : '✗'}
      </span>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: t.text }}>
          {cond.headline}
        </div>
        <div style={{ fontSize: 13, color: t.text2, marginTop: 4, lineHeight: 1.5 }}>
          {cond.description}
        </div>
      </div>
    </div>
  );
}
