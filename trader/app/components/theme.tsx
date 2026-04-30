'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

export type ThemeName = 'dark';

export type ThemeTokens = {
  bg: string;
  surface: string;
  card: string;
  text: string;
  text2: string;
  text3: string;
  border: string;
  borderEmphasis: string;
  accent: string;
  accentSoft: string;
  accentDeep: string;
  accentGlow: string;
  bullish: string;
  bearish: string;
  warning: string;
  info: string;
};

// Carried 1:1 from Optaur — see spec/design_system.md §1 + §9.
// Color tokens MUST stay identical to keep both apps in the same family.
export const THEMES: Record<ThemeName, ThemeTokens> = {
  dark: {
    bg: '#0A0A0F',
    surface: '#14141A',
    card: '#1E1E26',
    text: '#F0F0F4',
    text2: '#9CA3AF',
    text3: '#6B7280',
    border: 'rgba(255,255,255,0.08)',
    borderEmphasis: 'rgba(255,255,255,0.14)',
    accent: '#00FF88',
    accentSoft: 'rgba(0,255,136,0.12)',
    accentDeep: '#00CC6A',
    accentGlow: 'rgba(0,255,136,0.4)',
    bullish: '#00FF88',
    bearish: '#FF3366',
    warning: '#FFB800',
    info: '#00C8FF',
  },
};

type Ctx = { theme: ThemeName; t: ThemeTokens };
const ThemeCtx = createContext<Ctx | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme] = useState<ThemeName>('dark');
  return <ThemeCtx.Provider value={{ theme, t: THEMES[theme] }}>{children}</ThemeCtx.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error('useTheme must be inside ThemeProvider');
  return ctx;
}
