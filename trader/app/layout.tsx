import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { ThemeProvider } from './components/theme';
import { Nav } from './components/nav';
import { Footer } from './components/footer';
import { DisclaimerBanner } from './components/disclaimer-banner';
import './globals.css';

const inter = Inter({
  variable: '--font-sans',
  subsets: ['latin'],
  display: 'swap',
});
const jetMono = JetBrains_Mono({
  variable: '--font-mono',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Saadhana Trader — Disciplined pattern detection for Indian equities',
  description:
    'Indian cash-equity scanner that surfaces high-probability long candidates from 13 transparent technical conditions and a fundamental quality gate. Research only — not investment advice.',
  keywords: [
    'Indian stocks',
    'NSE',
    'pattern detection',
    'stock scanner',
    'Nifty 500',
    'technical analysis',
  ],
  authors: [{ name: 'Saadhana Trader' }],
  openGraph: {
    title: 'Saadhana Trader',
    description: 'Disciplined pattern detection for Indian cash equities.',
    siteName: 'Saadhana Trader',
    type: 'website',
    locale: 'en_IN',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Saadhana Trader',
    description: 'Disciplined pattern detection for Indian cash equities.',
  },
  robots: { index: false, follow: false }, // §21.3 — no indexing until SEBI legal opinion clears
};

export const viewport: Viewport = {
  themeColor: '#0A0A0F',
  width: 'device-width',
  initialScale: 1,
};

const PUBLIC_MODE = (process.env.NEXT_PUBLIC_MODE ?? 'public') === 'public';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetMono.variable}`}>
      <body>
        <ThemeProvider>
          <Nav />
          {PUBLIC_MODE && <DisclaimerBanner />}
          <main style={{ padding: '40px clamp(20px, 5vw, 64px)' }}>{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
