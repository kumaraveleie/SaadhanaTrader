'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useTheme } from './theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Layer 2 of phase guidance — right-side slide-in drawer with the
 * full comparison table. Shared from /research column header `?`
 * icon and the distribution chip strip `?` icon.
 */
export function PhaseDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTheme();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="phase-drawer-title"
      style={{ position: 'fixed', inset: 0, zIndex: 200 }}
    >
      <div
        onClick={onClose}
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.5)',
          backdropFilter: 'blur(2px)',
        }}
      />
      <aside
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          bottom: 0,
          width: 'min(480px, 100vw)',
          background: t.bg,
          borderLeft: `1px solid ${t.border}`,
          boxShadow: '-20px 0 40px rgba(0,0,0,0.4)',
          overflowY: 'auto',
          padding: '24px 28px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 12,
          }}
        >
          <h2
            id="phase-drawer-title"
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: '-0.02em',
              margin: 0,
              color: t.text,
            }}
          >
            How to read phases
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close drawer"
            style={{
              background: 'transparent',
              border: 'none',
              color: t.text2,
              fontSize: 22,
              cursor: 'pointer',
              padding: 4,
            }}
          >
            ×
          </button>
        </div>
        <p style={{ fontSize: 14, color: t.text2, lineHeight: 1.6, margin: '8px 0 24px' }}>
          Saadhana classifies every stock into one of four phases based on
          where it sits in its trend. The phase tells you not just IF a
          stock is moving — but WHERE in the move you&apos;d be entering.
        </p>

        <Section title="Comparison">
          <div
            style={{
              border: `1px solid ${t.border}`,
              borderRadius: 8,
              overflow: 'hidden',
              fontSize: 12,
            }}
          >
            <Row
              cols={['Phase', 'When to buy', 'Risk profile', 'Hit rate']}
              header
            />
            <Row
              cols={['Breakout', 'Fresh strength', 'Tight stop, big upside', '~50–55%']}
              tone={t.bullish}
            />
            <Row
              cols={['Trending', 'Trend running, ride it', 'Wider stop, less upside', '~60–65%']}
              tone={t.text}
            />
            <Row
              cols={['Extended', 'Avoid — late stage', "Don't chase", '~30–35%']}
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
              fontSize: 13,
              color: t.text2,
              lineHeight: 1.6,
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
              the system shouldn&apos;t fire here (the &quot;not extended&quot;
              filter prevents it)
            </li>
            <li>
              No match but the stock shows <strong style={{ color: t.text }}>Trending</strong>
              {' '}on /research → that&apos;s information, not action
            </li>
          </ul>
        </Section>

        <Section title="A stock moves through phases">
          <p style={{ fontSize: 13, color: t.text2, lineHeight: 1.6, margin: 0 }}>
            Sideways → Breakout → Trending → Extended → retracement back to
            Trending or Sideways. Buy in <strong style={{ color: t.text }}>Breakout</strong>
            {' '}or <strong style={{ color: t.text }}>Trending</strong>. Sell when phase
            becomes <strong style={{ color: t.text }}>Extended</strong> or when the
            exit rules fire.
          </p>
        </Section>

        <Section title="Coming next (CR-008)">
          <p style={{ fontSize: 13, color: t.text2, lineHeight: 1.6, margin: 0 }}>
            When the conviction tier ships, sizing will reflect phase
            automatically — Breakout HIGH, Trending STANDARD, Extended
            downgraded to WATCH. Until then, all matches are STANDARD-sized
            and phase is informational.
          </p>
        </Section>

        <div style={{ marginTop: 'auto', paddingTop: 24 }}>
          <Link
            href="/about/phases"
            onClick={onClose}
            style={{
              display: 'inline-block',
              padding: '10px 16px',
              background: t.accent,
              color: t.bg,
              borderRadius: 8,
              fontWeight: 600,
              fontSize: 13,
              textDecoration: 'none',
              fontFamily: 'inherit',
            }}
          >
            Open full reference at /about/phases →
          </Link>
        </div>
      </aside>
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
    <section style={{ marginBottom: 24 }}>
      <h3
        style={{
          fontSize: 11,
          color: t.text3,
          fontFamily: FONT_MONO,
          fontWeight: 600,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          margin: '0 0 10px',
        }}
      >
        {title}
      </h3>
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
        gridTemplateColumns: '1fr 1.5fr 1.4fr 0.8fr',
        gap: 0,
        background: header ? t.surface : 'transparent',
        borderTop: header ? 'none' : `1px solid ${t.border}`,
      }}
    >
      {cols.map((c, i) => (
        <div
          key={i}
          style={{
            padding: '10px 12px',
            color: header ? t.text3 : i === 0 ? tone ?? t.text : t.text2,
            fontWeight: header ? 600 : i === 0 ? 600 : 500,
            fontSize: header ? 11 : 12,
            letterSpacing: header ? '0.08em' : 'normal',
            textTransform: header ? 'uppercase' : 'none',
            lineHeight: 1.4,
          }}
        >
          {c}
        </div>
      ))}
    </div>
  );
}
