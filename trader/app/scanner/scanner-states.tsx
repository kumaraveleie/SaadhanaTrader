'use client';

import { useTheme } from '../components/theme';
import { FreshnessIndicator } from '../components/freshness-indicator';
import { regimeLabel as regimeLabelMap } from '../lib/labels';
import type { Regime } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Scanner header: scan date freshness indicator, regime banner, summary
 * counts. Tier 1 internals are intentionally hidden in public mode —
 * universe + candidate counts only.
 */
export function ScannerHeader({
  scanDate,
  regime,
  universeSize,
  candidatesCount,
}: {
  scanDate: string;
  regime: Regime;
  universeSize: number;
  candidatesCount: number;
}) {
  const { t } = useTheme();
  const tone = regimeTone(regime, t);
  const regimeText = regimeLabelMap(regime).text;
  return (
    <header style={{ marginBottom: 32 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 16,
        }}
      >
        <h1
          style={{
            fontSize: 'clamp(28px, 4vw, 36px)',
            fontWeight: 700,
            letterSpacing: '-0.03em',
            margin: 0,
            color: t.text,
          }}
        >
          Scanner
        </h1>
        <FreshnessIndicator scanDate={scanDate} />
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
        }}
      >
        <Stat label="Market" value={regimeText} valueColor={tone.fg} />
        <Stat label="Universe" value={`${universeSize} symbols`} />
        <Stat label="Pattern matches today" value={`${candidatesCount}`} />
      </div>
    </header>
  );
}

function Stat({
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
    <div
      style={{
        padding: '14px 18px',
        background: t.card,
        border: `1px solid ${t.border}`,
        borderRadius: 12,
      }}
    >
      <div
        style={{
          fontSize: 11,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: t.text3,
          fontFamily: FONT_MONO,
          marginBottom: 6,
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

/**
 * §12-aware empty state. Risk_Off explicitly tells the user the
 * system is standing aside; Caution / Risk_On with empty candidates
 * just says no qualifying setups today.
 */
export function ScannerEmptyState({ regime }: { regime: Regime }) {
  const { t } = useTheme();
  const message =
    regime === 'Risk_Off'
      ? {
          title: 'Defensive market — no new ideas today',
          body: (
            <>
              The Nifty 50 is trading below its 200-day moving average. The
              system steps aside when the broader market is weak —
              capital preservation over fear of missing out. No entries
              are being surfaced today, and existing held names are being
              reviewed under tighter stops.
            </>
          ),
        }
      : regime === 'Caution'
      ? {
          title: 'Mixed market — no high-conviction matches',
          body: (
            <>
              The Nifty 50 sits between its 50-day and 200-day moving
              averages. The system requires a perfect 13-of-13 score and
              high conviction in this regime. None of today’s scans
              cleared that bar.
            </>
          ),
        }
      : {
          title: 'No qualifying setups today',
          body: (
            <>
              The system scanned the universe and found no symbols with
              all 13 technical conditions firing simultaneously plus the
              quality filter. This is normal — the system is
              deliberately selective.
            </>
          ),
        };
  return (
    <div
      style={{
        padding: '48px 32px',
        background: t.card,
        border: `1px solid ${t.border}`,
        borderRadius: 12,
        textAlign: 'center',
      }}
    >
      <h2
        style={{
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: '-0.02em',
          margin: '0 0 12px',
          color: t.text,
        }}
      >
        {message.title}
      </h2>
      <p
        style={{
          fontSize: 15,
          color: t.text2,
          lineHeight: 1.65,
          maxWidth: 560,
          margin: '0 auto',
        }}
      >
        {message.body}
      </p>
    </div>
  );
}

/**
 * No JSON file at all. Different message from the empty-candidates
 * state — this is an infrastructure problem, not a market outcome.
 */
export function ScannerNoData() {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 720, margin: '60px auto', textAlign: 'center' }}>
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 12,
          color: t.text3,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          marginBottom: 16,
        }}
      >
        Scan data unavailable
      </div>
      <h1
        style={{
          fontSize: 'clamp(24px, 3vw, 32px)',
          fontWeight: 700,
          margin: '0 0 16px',
          color: t.text,
          letterSpacing: '-0.03em',
        }}
      >
        No scan results to display
      </h1>
      <p style={{ fontSize: 15, color: t.text2, lineHeight: 1.6 }}>
        The latest scan output (<code style={{ color: t.text3 }}>signals/latest.json</code>)
        could not be read. The nightly cron may not have completed yet, or the
        deploy is missing the file. Check back after the next end-of-day run.
      </p>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────
function regimeTone(
  regime: Regime,
  t: ReturnType<typeof useTheme>['t'],
): { fg: string } {
  switch (regime) {
    case 'Risk_On':
      return { fg: t.bullish };
    case 'Caution':
      return { fg: t.warning };
    case 'Risk_Off':
      return { fg: t.bearish };
  }
}
