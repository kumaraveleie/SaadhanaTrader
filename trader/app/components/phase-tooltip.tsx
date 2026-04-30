'use client';

import { useState } from 'react';
import { PHASE_HELP } from '../lib/labels';
import type { LifecycleTag } from '../lib/scan-types';
import { useTheme } from './theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Hover-only popover for a phase tag. Wraps the tag (or any node)
 * and reveals a 4-line action-oriented popover from PHASE_HELP[tag].
 * Layer 1 of the three-layer phase guidance system.
 */
export function PhaseTooltip({
  tag,
  onLearnMore,
  children,
}: {
  tag: LifecycleTag;
  onLearnMore?: () => void;
  children: React.ReactNode;
}) {
  const { t } = useTheme();
  const [open, setOpen] = useState(false);
  const help = PHASE_HELP[tag];

  return (
    <span
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 8px)',
            left: 0,
            zIndex: 100,
            width: 280,
            padding: '12px 14px',
            background: t.card,
            border: `1px solid ${t.border}`,
            borderRadius: 8,
            boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
            display: 'block',
            textTransform: 'none',
            letterSpacing: 'normal',
          }}
        >
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: t.text,
              marginBottom: 4,
            }}
          >
            {help.title}
          </div>
          <div
            style={{
              fontSize: 11,
              color: t.text3,
              fontFamily: FONT_MONO,
              marginBottom: 10,
            }}
          >
            {help.summary}
          </div>
          {help.lines.map((line) => (
            <div
              key={line}
              style={{
                fontSize: 12,
                color: t.text2,
                lineHeight: 1.5,
                marginBottom: 4,
              }}
            >
              {line}
            </div>
          ))}
          <div style={{ marginTop: 10 }}>
            {onLearnMore ? (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  onLearnMore();
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  padding: 0,
                  fontSize: 12,
                  color: t.accent,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                Learn more →
              </button>
            ) : (
              <a
                href="/about/phases"
                style={{
                  fontSize: 12,
                  color: t.accent,
                  fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                Learn more →
              </a>
            )}
          </div>
        </span>
      )}
    </span>
  );
}
