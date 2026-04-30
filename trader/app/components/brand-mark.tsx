'use client';

type Props = {
  size?: number;
  color?: string;
  accent?: string;
  showWordmark?: boolean;
  fontSize?: number;
};

/**
 * Saadhana brand mark — concentric rings + center spark.
 * Per spec/design_system.md §4: same construction technique as Optaur
 * (clean geometric primary + animated accent dot) with a different
 * glyph (chakra/target rings symbolizing disciplined practice).
 *
 * The .saadhana-spark and .saadhana-ping classes pulse via CSS in
 * globals.css — outer ring is the static frame, inner ring is the
 * second concentric, and the center pair (ping + spark) carries the
 * animation indicating "the rule fires".
 */
export function BrandMark({
  size = 28,
  color = 'currentColor',
  accent = '#00FF88',
  showWordmark = true,
  fontSize,
}: Props) {
  const wm = fontSize ?? Math.round(size * 0.72);
  const gap = size * 0.36;

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap }}>
      <svg
        width={size}
        height={size}
        viewBox="-32 -32 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Outer ring — primary frame */}
        <circle cx="0" cy="0" r="22" stroke={color} strokeWidth="2.5" fill="none" />
        {/* Inner ring — concentric */}
        <circle cx="0" cy="0" r="13" stroke={color} strokeWidth="1.5" fill="none" opacity="0.5" />
        {/* Center spark + ping */}
        <circle r="7" fill="none" stroke={accent} strokeWidth="1.5" className="saadhana-ping" />
        <circle r="4" fill={accent} className="saadhana-spark" />
      </svg>
      {showWordmark && (
        <span
          style={{
            fontFamily: 'var(--font-sans), -apple-system, "Segoe UI", system-ui, sans-serif',
            fontWeight: 700,
            fontSize: wm,
            color,
            letterSpacing: '-0.03em',
            lineHeight: 1,
          }}
        >
          Saadhana
        </span>
      )}
    </div>
  );
}
