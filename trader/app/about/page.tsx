'use client';

import { useTheme } from '../components/theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export default function AboutPage() {
  const { t } = useTheme();
  return (
    <div style={{ maxWidth: 760, margin: '20px auto 80px', lineHeight: 1.65 }}>
      <h1
        style={{
          fontSize: 'clamp(32px, 4vw, 44px)',
          fontWeight: 700,
          letterSpacing: '-0.03em',
          margin: '0 0 24px',
          color: t.text,
        }}
      >
        About Saadhana Trader
      </h1>
      <p style={{ fontSize: 17, color: t.text2, marginBottom: 32 }}>
        Saadhana is a research and pattern-detection tool for Indian
        cash-equity markets. We do one thing: scan the Nifty 500 every
        evening, apply 13 transparent technical conditions plus a
        fundamental quality gate to every symbol, and surface the names
        where every box is checked. Same input, same output, every time.
      </p>

      <Section title="What it does">
        <ul style={{ paddingLeft: 20, margin: 0, color: t.text2 }}>
          <li>
            Scores every Nifty 500 stock 0–13 against the daily Pro-Setup
            checklist (trend, momentum, accumulation, risk, not-extended).
          </li>
          <li>
            Filters by a quarterly fundamental gate (market cap ≥ ₹5,000 Cr,
            growth, low pledge, healthy debt or bank-equivalent metrics).
          </li>
          <li>
            Surfaces the symbols where the entire 13-condition stack fires
            on the most recent closed daily bar.
          </li>
          <li>
            Displays a paired entry-stop and target ladder so the risk math
            is explicit at a glance.
          </li>
          <li>
            Records every signal with full feature snapshot for later
            forensics review.
          </li>
        </ul>
      </Section>

      <Section title="What it isn't">
        <ul style={{ paddingLeft: 20, margin: 0, color: t.text2 }}>
          <li>
            <strong>Not investment advice.</strong> The patterns here are
            data, not recommendations. Decisions, capital, and consequences
            are entirely yours.
          </li>
          <li>
            <strong>Not a guarantee.</strong> A high Pro-Setup score is a
            historical pattern, not a future result. Markets change; bear
            regimes drag everything; individual trades will lose.
          </li>
          <li>
            <strong>Not real-time.</strong> Data is end-of-day. Intraday
            moves aren&apos;t reflected.
          </li>
          <li>
            <strong>Not registered.</strong> We are not a SEBI-registered
            Investment Advisor or Research Analyst. This is a research
            tool, not a regulated advisory service.
          </li>
        </ul>
      </Section>

      <Section title="The Pro-Setup score, briefly">
        <p style={{ fontSize: 15, color: t.text2, marginBottom: 12 }}>
          Each stock&apos;s daily score is the count of the 13 conditions
          that fire on the most recent closed bar. The conditions cover
          five qualifications:
        </p>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 14,
            color: t.text2,
            marginTop: 8,
          }}
        >
          <tbody>
            {[
              ['Trend', '4', 'Stage 2, EMA stack, weekly higher-highs/lows'],
              ['Momentum', '2', 'RSI in 50–70 band, MACD histogram rising'],
              ['Accumulation', '2', 'Institutional buy in last 5 days, 30-bar flow score positive'],
              ['Risk', '3', 'Stop ≤ 3% away, ATR-projected upside ≥ 5%, R/R ≥ 2:1'],
              ['Not extended', '2', 'Within 2% of 52-week high (with breakout exception); BB width healthy'],
            ].map(([label, n, desc]) => (
              <tr key={label} style={{ borderTop: `1px solid ${t.border}` }}>
                <td style={{ padding: '12px 8px', color: t.text, fontWeight: 600, width: 130 }}>
                  {label}
                </td>
                <td
                  style={{
                    padding: '12px 8px',
                    fontFamily: FONT_MONO,
                    color: t.text3,
                    width: 60,
                  }}
                >
                  {n}
                </td>
                <td style={{ padding: '12px 8px' }}>{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 13, color: t.text3, marginTop: 16 }}>
          A symbol is surfaced as <em>High Pattern Match</em> when the
          score reaches 13 of 13 in a Risk-On market regime. Anything
          below that is either watch-only or filtered out entirely.
        </p>
      </Section>

      <Section title="Full disclaimer">
        <p style={{ fontSize: 14, color: t.text2 }}>
          Saadhana Trader is an end-of-day research and pattern-detection
          tool for educational and analytical purposes. Information
          displayed is computed mechanically from public market data and
          is presented as patterns the system has identified, not as
          recommendations. We are not registered with the Securities and
          Exchange Board of India (SEBI) as an Investment Advisor or
          Research Analyst.
        </p>
        <p style={{ fontSize: 14, color: t.text2, marginTop: 16 }}>
          Equity markets carry substantial risk of loss. Past pattern
          matches do not guarantee future returns. Before acting on any
          information shown here, consult a SEBI-registered Investment
          Advisor and conduct your own due diligence. By using this site
          you acknowledge that you understand these limitations and accept
          full responsibility for any decisions and outcomes.
        </p>
        <p style={{ fontSize: 14, color: t.text2, marginTop: 16 }}>
          Market data is sourced from public end-of-day exchange feeds
          and may be delayed by minutes to hours after the trading
          session. Outages, data errors, and corporate-action gaps may
          cause temporary discrepancies.
        </p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const { t } = useTheme();
  return (
    <section style={{ marginTop: 48 }}>
      <h2
        style={{
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: '-0.02em',
          margin: '0 0 16px',
          color: t.text,
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
