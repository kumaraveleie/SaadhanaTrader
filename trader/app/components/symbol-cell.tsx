'use client';

import Link from 'next/link';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Shared symbol cell — the canonical drill-into-stock affordance for
 * every table in the app. Renders as a Link to /stock/{symbol} with
 * a visible hover state (underline + accent color tint + ↗ arrow on
 * hover) so users immediately recognise it as clickable.
 *
 * The hover state is implemented via global CSS classes
 * (.saadhana-symbol-cell + .saadhana-symbol-arrow in globals.css)
 * because inline styles can't express :hover. Color tokens in the
 * CSS match the dark-theme palette in trader/app/components/theme.tsx.
 */
export function SymbolCell({ symbol }: { symbol: string }) {
  return (
    <Link
      href={`/stock/${encodeURIComponent(symbol)}`}
      className="saadhana-symbol-cell"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontFamily: FONT_MONO,
        fontWeight: 500,
        textDecoration: 'none',
        cursor: 'pointer',
      }}
    >
      <span>{symbol}</span>
      <span
        aria-hidden
        className="saadhana-symbol-arrow"
        style={{
          fontSize: 11,
          opacity: 0,
          transition: 'opacity 80ms ease',
          marginLeft: 2,
        }}
      >
        ↗
      </span>
    </Link>
  );
}
