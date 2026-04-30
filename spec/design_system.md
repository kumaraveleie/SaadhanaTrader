# Saadhana Trader — Design System

**Reference parent:** Optaur (https://optaur-demo.vercel.app/)
**Status:** Locked · **Version:** 1.0
**Goal:** Saadhana Trader visually belongs to the same product family as
Optaur. Same dark theme, same neon accent, same typography, same brand-mark
construction. Different glyph, same DNA.

This document is the contract for visual implementation. Every component
in `trader/app/components/` honors these tokens. Inline styles via theme
tokens (not heavy Tailwind) — same pattern as Optaur.

---

## 1. Color tokens

Carried 1:1 from Optaur's `theme.tsx`. Do not edit without spec change.

```ts
// trader/app/components/theme.tsx
export const THEMES = {
  dark: {
    // surfaces
    bg:              '#0A0A0F',     // page background
    surface:         '#14141A',     // sticky nav, side panels
    card:            '#1E1E26',     // result cards, table rows

    // text
    text:            '#F0F0F4',     // primary
    text2:           '#9CA3AF',     // secondary (labels, nav links)
    text3:           '#6B7280',     // tertiary (metadata, timestamps)

    // borders
    border:          'rgba(255,255,255,0.08)',
    borderEmphasis:  'rgba(255,255,255,0.14)',

    // accent — neon green (Tradingview / Robinhood Pro feel)
    accent:          '#00FF88',
    accentSoft:      'rgba(0,255,136,0.12)',  // hover bg, badges
    accentDeep:      '#00CC6A',                // pressed states
    accentGlow:      'rgba(0,255,136,0.4)',   // glow shadow

    // signal semantics
    bullish:         '#00FF88',     // BUY / Pattern Match / inst. buy
    bearish:         '#FF3366',     // SELL / Pattern Broken / inst. sell
    warning:         '#FFB800',     // WATCH / caution regime
    info:            '#00C8FF',     // neutral metrics / labels
  },
};
```

### Saadhana-specific semantic mapping

| Internal label | Public label (§21.1) | Color token |
|---|---|---|
| BUY | High Pattern Match | `bullish` (#00FF88) |
| HOLD | Pattern Holding | `info` (#00C8FF) |
| SELL | Pattern Broken | `bearish` (#FF3366) |
| WATCH | — (not displayed) | `warning` (#FFB800) |
| WAIT | — (not displayed) | `text3` (#6B7280) |
| Stage 2 | — | `bullish` |
| Stage 3 / 4 | — | `bearish` |
| Risk-On regime | — | `bullish` |
| Caution regime | — | `warning` |
| Risk-Off regime | — | `bearish` |
| Catalyst HIGH | — | `accent` (#00FF88) |
| Catalyst STANDARD | — | `info` (#00C8FF) |
| Catalyst Unknown | — | `text3` (gray) |

---

## 2. Typography

```ts
import { Inter, JetBrains_Mono } from 'next/font/google';

const inter   = Inter({ variable: '--font-sans', subsets: ['latin'], display: 'swap' });
const jetMono = JetBrains_Mono({ variable: '--font-mono', subsets: ['latin'], display: 'swap' });
```

### Type scale

| Use | Font | Size | Weight | Letter-spacing |
|---|---|---|---|---|
| Display (hero) | Inter | clamp(40px, 6vw, 72px) | 700 | -0.04em |
| H1 | Inter | clamp(32px, 4vw, 44px) | 700 | -0.03em |
| H2 | Inter | 28px | 700 | -0.03em |
| H3 | Inter | 20px | 600 | -0.02em |
| Body | Inter | 16px | 400 | normal |
| Body small | Inter | 14px | 400 | normal |
| Label / nav | Inter | 14px | 500 | normal |
| Button | Inter | 14px | 600 | -0.01em |
| Caption | Inter | 12px | 500 | 0.02em (uppercase OK) |
| Numeric / table | JetBrains Mono | 14px | 500 | normal |
| Code | JetBrains Mono | 13px | 400 | normal |

**All prices, scores, percentages, RVOL values use `var(--font-mono)`** —
tabular numerals matter for scanning a results table.

---

## 3. Layout primitives

### Page shell

```
<html>
  <body style={{ background: t.bg, color: t.text }}>
    <Nav />
    <main style={{ padding: '40px clamp(20px, 5vw, 64px)' }}>
      {children}
    </main>
    <Footer />
  </body>
</html>
```

### Nav (sticky, backdrop blur — 1:1 from Optaur)
- Padding: `20px clamp(20px, 5vw, 64px)`
- `position: sticky; top: 0; z-index: 50`
- `backdrop-filter: blur(8px)` — content shows through
- 1px bottom border in `t.border`
- Three groups: brand-mark · nav links · sign-in + CTA

### Card
- Background: `t.card`
- Border: `1px solid t.border`
- Border-radius: `12px` (small cards) / `16px` (feature cards)
- Padding: `20px` (compact) / `28px` (regular) / `40px` (hero)
- Hover: `border-color: t.borderEmphasis` + `transform: translateY(-2px)`

### Bento grid
- `grid-template-columns: repeat(12, 1fr)`
- Gap: `16px` (tight) / `24px` (regular)
- Featured cards span 6 or 8 columns; supporting cards span 3 or 4
- Mobile (`@media max-width: 900px`): collapse to single column

### Buttons

```tsx
// Primary
{
  padding: '10px 18px',
  fontSize: 14,
  fontWeight: 600,
  borderRadius: 8,
  background: t.accent,
  color: t.bg,
  letterSpacing: '-0.01em',
}

// Secondary
{
  padding: '10px 18px',
  fontSize: 14,
  fontWeight: 500,
  borderRadius: 8,
  background: 'transparent',
  border: `1px solid ${t.border}`,
  color: t.text,
}

// Ghost (nav-link style)
{
  color: t.text2,
  fontWeight: 500,
  fontSize: 14,
  textDecoration: 'none',
}
```

---

## 4. Brand mark

Saadhana's brand mark follows Optaur's construction pattern: a clean
geometric primary shape + an animated accent dot. Different glyph, same
construction technique → same product family.

### Optaur (parent reference)
Stylized "O" ring (stroke 3, radius 22) with a neon-green spark notch
in the upper-right that pulses (`optaur-spark` + `optaur-ping` keyframes).

### Saadhana (this repo)
Concentric target / chakra construction: outer ring + inner ring + center
spark. The center spark pulses to signify "the rule fires." Symbolizes
*saadhana* (disciplined practice) — focus, repetition, accumulation.

```tsx
// trader/app/components/brand-mark.tsx
export function BrandMark({ size = 28, color = 'currentColor', accent = '#00FF88', showWordmark = true }) {
  const wm = Math.round(size * 0.72);
  const gap = size * 0.36;
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap }}>
      <svg width={size} height={size} viewBox="-32 -32 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        {/* outer ring */}
        <circle cx="0" cy="0" r="22" stroke={color} strokeWidth="2.5" fill="none" />
        {/* inner ring */}
        <circle cx="0" cy="0" r="13" stroke={color} strokeWidth="1.5" fill="none" opacity="0.5" />
        {/* center spark + ping */}
        <circle r="7" fill="none" stroke={accent} strokeWidth="1.5" className="saadhana-ping" />
        <circle r="4" fill={accent} className="saadhana-spark" />
      </svg>
      {showWordmark && (
        <span style={{
          fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: wm,
          color, letterSpacing: '-0.03em', lineHeight: 1,
        }}>Saadhana</span>
      )}
    </div>
  );
}
```

### Pulse animations (in `globals.css`)

```css
.saadhana-spark {
  transform-box: fill-box;
  transform-origin: center;
  animation: saadhana-dot-breathe 2.4s ease-in-out infinite;
}
.saadhana-ping {
  transform-box: fill-box;
  transform-origin: center;
  animation: saadhana-spark-ping 2.4s ease-out infinite;
  opacity: 0;
}
@keyframes saadhana-dot-breathe {
  0%, 100% { opacity: 0.85; transform: scale(0.92); }
  50%      { opacity: 1;    transform: scale(1.10); }
}
@keyframes saadhana-spark-ping {
  0%   { transform: scale(0.6); opacity: 0; }
  15%  { opacity: 0.8; }
  100% { transform: scale(2.4); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .saadhana-spark, .saadhana-ping { animation: none !important; }
}
```

---

## 5. Component patterns specific to Saadhana

### Signal pill
For each result row's signal status. Shape: rounded rect, padding `4px 10px`,
font-size 12, font-weight 600, uppercase, letter-spacing 0.04em.

```tsx
function SignalPill({ signal }: { signal: 'BUY' | 'HOLD' | 'SELL' | 'WATCH' }) {
  const map = {
    BUY:   { label: 'High Pattern Match', bg: t.accentSoft, fg: t.bullish },
    HOLD:  { label: 'Pattern Holding',    bg: 'rgba(0,200,255,0.12)', fg: t.info },
    SELL:  { label: 'Pattern Broken',     bg: 'rgba(255,51,102,0.12)', fg: t.bearish },
    WATCH: { label: 'Watching',           bg: 'rgba(255,184,0,0.12)', fg: t.warning },
  };
  const s = map[signal];
  return <span style={{
    background: s.bg, color: s.fg,
    padding: '4px 10px', borderRadius: 6,
    fontSize: 12, fontWeight: 600,
    letterSpacing: '0.04em', textTransform: 'uppercase',
  }}>{s.label}</span>;
}
```

### Score gauge (e.g., 12/13 Pro-Setup Score)
Horizontal bar 4px tall, full-width container, fill = `score / max`.
Color: bullish if score ≥ 10, warning if 7–9, bearish if < 7. Background
`t.accentSoft`. Display "12/13" as mono numeric next to it.

### Conviction tier badge
Larger pill (padding `6px 12px`), gradient background:
- HIGH: `linear-gradient(135deg, t.accent, t.accentDeep)` with text `t.bg`
- STANDARD: `t.accentSoft` border `t.accent` text `t.accent`
- WATCH: `t.warning` background with text `t.bg`

### Catalyst chip
Small inline tag (font-size 11, padding `2px 8px`, border-radius 4),
displayed inline in a row of chips:
- Fresh (≤7 days): `bullish` text on `accentSoft` background
- Standard (≤30 days): `info` text on `rgba(0,200,255,0.10)`
- Stale (30–90 days): `text2` text on `rgba(255,255,255,0.04)`

### Live data indicator
A 6px circle with `pulse` animation (already exists in Optaur's
`globals.css`). Color = `bullish` when live, `warning` when 15-min
delayed, `text3` when EOD only.

```html
<span style={{
  display: 'inline-block', width: 6, height: 6,
  borderRadius: '50%', background: t.bullish,
  animation: 'pulse 2s ease-in-out infinite',
}} />
EOD · {scanDate}
```

### Disclaimer banner (PUBLIC mode only — §21.1 required)
Layout-level, sits **above `<Footer />`** on every page in public mode.

*Placement note (v2 — Apr 2026):* the v1 design placed the banner
below `<Nav />`. Live K1.1 testing showed that placement squeezed the
hero on mobile and ate vertical space on the scanner. Moved to a
bottom-anchored slot (just above the footer) so the disclaimer stays
persistent and reachable without competing for primary content space.
Font bumped from 12 → 14px and padding from 8 → 14px so the bottom-
anchored placement reads at a glance.

```tsx
function DisclaimerBanner() {
  return (
    <div style={{
      padding: '14px clamp(20px, 5vw, 64px)',
      background: 'rgba(255,184,0,0.08)',
      borderTop: `1px solid ${t.border}`,
      borderBottom: `1px solid ${t.border}`,
      fontSize: 14, color: t.text2, textAlign: 'center', lineHeight: 1.55,
    }}>
      Saadhana Trader is a research and pattern-detection tool.
      Information only. Not investment advice.{' '}
      <Link href="/about" style={{ color: t.accent, fontWeight: 500 }}>
        Read the full disclaimer →
      </Link>
    </div>
  );
}
```

---

## 6. Page-level layouts

### `/` — Home / Hero
Same as Optaur home: large headline, sub-headline, two CTAs (primary
"Open Scanner" + secondary "How it works"), live preview of today's top 3
matches in a card grid below the fold. Footer with disclaimer.

### `/scanner` — The screener
Two-column layout:
- Left rail (320px fixed): universe selector, condition checkboxes,
  match-mode toggle, "Scan" button
- Right (flex): regime banner at top, results table, click-row →
  expand inline detail card with mini chart

### `/stock/[symbol]` — Stock detail
Three-region:
- Top card: symbol, name, price, signal pill, conviction tier, key metrics
- Middle: lightweight-charts candle pane + volume sub-pane (institutional
  bars colored per `saadhana_volume_v2.pine` rules)
- Right rail: 13 Pro-Setup conditions checklist (each with green tick or
  red X), catalyst card (chips + 1-line narrative), risk levels card

### `/learning` — Forensics review (PERSONAL only)
- This week's outcomes summary
- Win/loss breakdown table
- Detected pattern cards
- Proposed rule with shadow-mode evidence + Approve/Reject buttons
- Per-rule trust score chart (recharts horizontal bar)
- Full weekly review markdown rendered

---

## 7. Responsive breakpoints

```css
@media (max-width: 900px) {
  /* Nav links collapse; hamburger reveals */
  .nav-links { display: none; }
  /* Bento grids become single column */
  .bento { grid-template-columns: 1fr !important; }
  /* Scanner left rail becomes top drawer */
  .scanner-rail { width: 100%; position: relative; }
}
@media (max-width: 600px) {
  /* Tables horizontally scroll; wrapper has overflow-x: auto */
  /* Stock detail collapses to single column */
}
```

---

## 8. Reuse from Optaur — files to mirror

When Claude Code starts on the Next.js app, copy these from Optaur as
the starting point and rename `Optaur → Saadhana`:

| Optaur file | Saadhana destination | Modifications |
|---|---|---|
| `app/components/theme.tsx` | `trader/app/components/theme.tsx` | None — copy as-is |
| `app/components/brand-mark.tsx` | `trader/app/components/brand-mark.tsx` | Replace SVG glyph per §4 above |
| `app/components/nav.tsx` | `trader/app/components/nav.tsx` | Update nav links: Scanner, Stocks, About |
| `app/components/footer.tsx` | `trader/app/components/footer.tsx` | Update disclaimer per §21.1 |
| `app/globals.css` | `trader/app/globals.css` | Rename `optaur-*` classes to `saadhana-*` |
| `app/layout.tsx` | `trader/app/layout.tsx` | Update metadata; add DisclaimerBanner if `NEXT_PUBLIC_MODE === 'public'` |
| `app/icon.tsx` | `trader/app/icon.tsx` | Saadhana glyph |
| `app/opengraph-image.tsx` | `trader/app/opengraph-image.tsx` | Saadhana branding |

---

## 9. What MUST stay the same as Optaur

- Color tokens (1:1)
- Typography choices (Inter + JetBrains Mono)
- Card / button / nav construction patterns
- Motion: pulse, breathe, ping animations and durations
- Mobile responsive breakpoints (900px, 600px)
- `prefers-reduced-motion` handling
- Accessibility: aria-hidden on decorative SVGs, focus rings on
  interactive elements

## 10. What's new / different in Saadhana

- Brand glyph (concentric rings vs single ring with notch)
- Wordmark text: "Saadhana"
- Disclaimer banner (mandatory in public mode)
- Signal pills mapped to "Pattern Match" labels in public mode
- `/learning` page (does not exist in Optaur — forensics is Saadhana-specific)
- Catalyst chip pattern (Optaur doesn't have this concept)

---

**End of design system v1.0** — when this document changes, propagate
to all components in the same PR. Visual drift is a bug.
