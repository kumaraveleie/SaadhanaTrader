'use client';

import Link from 'next/link';
import { useTheme } from '../../components/theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export default function PhasesPage() {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 760, margin: '20px auto 80px', lineHeight: 1.65 }}>
      <Link
        href="/about"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 13,
          color: t.text2,
          marginBottom: 16,
          textDecoration: 'none',
        }}
      >
        ← About
      </Link>

      <h1
        style={{
          fontSize: 'clamp(28px, 4vw, 40px)',
          fontWeight: 700,
          letterSpacing: '-0.03em',
          margin: '0 0 16px',
          color: t.text,
        }}
      >
        How to read phases
      </h1>
      <p style={{ fontSize: 16, color: t.text2, marginBottom: 32 }}>
        Saadhana classifies every stock into one of four phases based on
        where it sits in its trend lifecycle. The phase tells you not just
        IF a stock is moving — but WHERE in the move you&apos;d be entering.
      </p>

      <Section title="Comparison">
        <div
          style={{
            border: `1px solid ${t.border}`,
            borderRadius: 10,
            overflow: 'hidden',
            fontSize: 13,
          }}
        >
          <Row
            cols={['Phase', 'When to buy', 'Risk profile', 'Hit rate']}
            header
          />
          <Row
            cols={[
              'Breakout',
              'Fresh strength entry',
              'Tight stop, big upside',
              '~50–55%',
            ]}
            tone={t.bullish}
          />
          <Row
            cols={[
              'Trending',
              'Trend running, ride it',
              'Wider stop, smaller upside',
              '~60–65%',
            ]}
            tone={t.text}
          />
          <Row
            cols={[
              'Extended',
              'Avoid — late stage',
              "Don't chase",
              '~30–35%',
            ]}
            tone={t.warning}
          />
          <Row
            cols={['Sideways', 'Wait — no signal', 'No clear direction', 'n/a']}
            tone={t.text3}
          />
        </div>
      </Section>

      <Section title="Practical rule">
        <ul
          style={{
            padding: '0 0 0 20px',
            margin: 0,
            color: t.text2,
            fontSize: 14,
            lineHeight: 1.65,
          }}
        >
          <li>
            Pattern Match + <strong style={{ color: t.text }}>Breakout</strong> →
            take it (best risk/reward)
          </li>
          <li>
            Pattern Match + <strong style={{ color: t.text }}>Trending</strong> →
            take it (highest probability)
          </li>
          <li>
            Pattern Match + <strong style={{ color: t.text }}>Extended</strong> →
            the system shouldn&apos;t fire here. The &quot;not extended&quot;
            filter prevents it.
          </li>
          <li>
            No match but the stock shows <strong style={{ color: t.text }}>Trending</strong>
            {' '}on /research → that&apos;s information, not action.
          </li>
        </ul>
      </Section>

      <Section title="A stock moves through phases">
        <p style={{ fontSize: 14, color: t.text2, lineHeight: 1.65 }}>
          Sideways → Breakout → Trending → Extended → retracement back to
          Trending or Sideways. Buy in <strong style={{ color: t.text }}>Breakout</strong>
          {' '}or <strong style={{ color: t.text }}>Trending</strong>. Sell when
          phase becomes <strong style={{ color: t.text }}>Extended</strong> or
          when the exit rules fire.
        </p>
      </Section>

      <Section title="Detailed phase definitions">
        <p style={{ fontSize: 14, color: t.text2, marginBottom: 12 }}>
          Each phase classifier with the underlying rules:
        </p>
        <ul style={{ padding: '0 0 0 20px', margin: 0, color: t.text2, fontSize: 13.5, lineHeight: 1.7 }}>
          <li>
            <strong style={{ color: t.bullish }}>Breakout</strong> — bars
            since pivot break &lt; 15 AND distance from 50-DMA &lt; 5% AND
            RSI 55–70 AND inst-flow score &gt; 0
          </li>
          <li>
            <strong style={{ color: t.text }}>Trending</strong> — not
            Breakout, not Extended, AND Pro-Setup Score ≥ 11
          </li>
          <li>
            <strong style={{ color: t.warning }}>Extended</strong> — RSI
            &gt; 80 OR distance from 50-DMA &gt; 15% OR (bars since 52WH
            break &lt; 5 with BB width &gt; 2× median)
          </li>
          <li>
            <strong style={{ color: t.text3 }}>Sideways</strong> — anything
            else
          </li>
        </ul>
      </Section>

      <Section title="Worked example (today's data)">
        <p style={{ fontSize: 14, color: t.text2, lineHeight: 1.65 }}>
          Today&apos;s distribution: 0 Breakout · 8 Trending · 57 Extended ·
          308 Sideways. The dominant Extended cohort (Power-sector and
          industrial names that already ran) is a textbook late-stage
          cluster — any chase entry here would be a Phase 3 buy. Compare
          to a bullish-market day where you&apos;d typically see 3–8
          Breakout candidates emerging — those are the system&apos;s ideal
          entries.
        </p>
      </Section>

      <Section title="How phases differ from Pro-Setup Score">
        <p style={{ fontSize: 14, color: t.text2, lineHeight: 1.65 }}>
          Score is binary (does the stock pass our 13 conditions today?).
          Phase is temporal (where in the move is it?).
        </p>
        <p style={{ fontSize: 14, color: t.text2, lineHeight: 1.65, marginTop: 12 }}>
          A 13/13 stock CAN be Extended (rare, filtered out by the &quot;not
          extended&quot; condition) or Trending (most common Pattern Match)
          or Breakout (the ideal). Score tells you yes/no. Phase tells you
          early/middle/late.
        </p>
      </Section>

      <Section title="Coming in Phase F (CR-008)">
        <p style={{ fontSize: 14, color: t.text2, lineHeight: 1.65 }}>
          When the conviction-tier feature ships, sizing will reflect phase
          automatically:
        </p>
        <ul style={{ padding: '0 0 0 20px', margin: '12px 0 0', color: t.text2, fontSize: 13.5, lineHeight: 1.7 }}>
          <li>
            <strong style={{ color: t.bullish }}>Breakout</strong> → HIGH
            conviction → 1.5% portfolio risk
          </li>
          <li>
            <strong style={{ color: t.text }}>Trending</strong> → STANDARD
            → 0.5% portfolio risk
          </li>
          <li>
            <strong style={{ color: t.warning }}>Extended</strong> →
            downgraded to WATCH (no entry)
          </li>
        </ul>
        <p style={{ fontSize: 13, color: t.text3, lineHeight: 1.65, marginTop: 12 }}>
          Until then, all Pattern Matches are STANDARD-sized; phase is
          informational only.
        </p>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const { t } = useTheme();
  return (
    <section style={{ marginTop: 40 }}>
      <h2
        style={{
          fontSize: 20,
          fontWeight: 700,
          letterSpacing: '-0.02em',
          margin: '0 0 14px',
          color: t.text,
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function Row({
  cols,
  header,
  tone,
}: {
  cols: string[];
  header?: boolean;
  tone?: string;
}) {
  const { t } = useTheme();
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.6fr 1.6fr 0.8fr',
        background: header ? t.surface : 'transparent',
        borderTop: header ? 'none' : `1px solid ${t.border}`,
      }}
    >
      {cols.map((c, i) => (
        <div
          key={i}
          style={{
            padding: '12px 14px',
            color: header ? t.text3 : i === 0 ? tone ?? t.text : t.text2,
            fontWeight: header ? 600 : i === 0 ? 600 : 500,
            fontSize: header ? 11 : 13,
            letterSpacing: header ? '0.08em' : 'normal',
            textTransform: header ? 'uppercase' : 'none',
            lineHeight: 1.45,
            fontFamily: header ? FONT_MONO : 'inherit',
          }}
        >
          {c}
        </div>
      ))}
    </div>
  );
}
