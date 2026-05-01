'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from './theme';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

const MAX_MATCHES = 8;
const MIN_QUERY_LENGTH = 2;

type UniverseSymbol = {
  symbol: string;
  name: string | null;
  sub_industry: string;
  close: number;
};

type Variant = 'desktop' | 'mobile';

/**
 * Persistent symbol search affordance — bridges the discoverability
 * gap from any page in the app to /stock/[symbol]. Desktop variant
 * sits in the nav between links and the CTA; mobile variant lives
 * at the top of the hamburger drawer.
 *
 * Matches against symbol prefix + symbol substring + company-name
 * substring, all case-insensitive. Universe data is pulled lazily
 * from /api/universe on first focus to keep the initial page load
 * lean.
 *
 * Keyboard: ↓/↑ to navigate matches, Enter to open, Escape to clear.
 */
export function SymbolSearch({
  variant = 'desktop',
  onNavigate,
}: {
  variant?: Variant;
  onNavigate?: () => void;
}) {
  const { t } = useTheme();
  const router = useRouter();

  const [query, setQuery] = useState('');
  const [universe, setUniverse] = useState<UniverseSymbol[]>([]);
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const [loadState, setLoadState] = useState<'idle' | 'loading' | 'loaded' | 'error'>('idle');

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Lazy-fetch the universe on first focus so the bundle stays small
  // and the request fires only when the user actually engages search.
  async function ensureUniverseLoaded() {
    if (loadState !== 'idle') return;
    setLoadState('loading');
    try {
      const r = await fetch('/api/universe');
      const data = await r.json();
      setUniverse(Array.isArray(data.symbols) ? data.symbols : []);
      setLoadState('loaded');
    } catch {
      setLoadState('error');
    }
  }

  // Click outside closes the dropdown.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const matches = useMemo<UniverseSymbol[]>(() => {
    if (query.length < MIN_QUERY_LENGTH) return [];
    const q = query.trim().toLowerCase();
    const prefix: UniverseSymbol[] = [];
    const symbolSubstring: UniverseSymbol[] = [];
    const nameSubstring: UniverseSymbol[] = [];
    for (const s of universe) {
      const sym = s.symbol.toLowerCase();
      const name = (s.name ?? '').toLowerCase();
      if (sym.startsWith(q)) {
        prefix.push(s);
      } else if (sym.includes(q)) {
        symbolSubstring.push(s);
      } else if (name.includes(q)) {
        nameSubstring.push(s);
      }
      if (
        prefix.length + symbolSubstring.length + nameSubstring.length >=
        MAX_MATCHES * 3
      ) {
        break;
      }
    }
    // Symbol-prefix matches first (most expected); then symbol-substring
    // (e.g. "EXIDE" finding "EXIDEIND"); then name-substring last.
    return [...prefix, ...symbolSubstring, ...nameSubstring].slice(
      0,
      MAX_MATCHES,
    );
  }, [universe, query]);

  function navigate(symbol: string) {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
    setQuery('');
    setOpen(false);
    inputRef.current?.blur();
    onNavigate?.();
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') {
      setQuery('');
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (e.key === 'Enter' && matches.length > 0) {
      e.preventDefault();
      navigate(matches[highlighted].symbol);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlighted((i) => Math.min(matches.length - 1, i + 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlighted((i) => Math.max(0, i - 1));
      return;
    }
  }

  const isMobile = variant === 'mobile';
  const inputWidth = isMobile ? '100%' : 200;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: isMobile ? '100%' : 'auto',
      }}
    >
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-label="Search stock symbol or name"
        aria-expanded={open && query.length >= MIN_QUERY_LENGTH}
        aria-controls="saadhana-symbol-search-dropdown"
        aria-autocomplete="list"
        placeholder="Search stock…"
        value={query}
        onFocus={() => {
          setOpen(true);
          ensureUniverseLoaded();
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setHighlighted(0);
          setOpen(true);
        }}
        onKeyDown={handleKey}
        style={{
          width: inputWidth,
          padding: '8px 12px',
          fontSize: 13,
          background: t.surface,
          border: `1px solid ${t.border}`,
          borderRadius: 8,
          color: t.text,
          outline: 'none',
          fontFamily: 'inherit',
        }}
      />
      {open && query.length >= MIN_QUERY_LENGTH && (
        <ul
          id="saadhana-symbol-search-dropdown"
          role="listbox"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: isMobile ? 0 : 'auto',
            width: isMobile ? '100%' : 320,
            maxHeight: 320,
            overflowY: 'auto',
            background: t.card,
            border: `1px solid ${t.border}`,
            borderRadius: 10,
            boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
            margin: 0,
            padding: 4,
            listStyle: 'none',
            zIndex: 100,
          }}
        >
          {matches.length === 0 ? (
            <li
              style={{
                padding: '10px 12px',
                fontSize: 12,
                color: t.text3,
                lineHeight: 1.5,
              }}
            >
              {loadState === 'loading'
                ? 'Loading universe…'
                : loadState === 'error'
                ? 'Could not load universe. Try the full ticker.'
                : 'No stock found. Type the full ticker (e.g. DIVISLAB).'}
            </li>
          ) : (
            matches.map((m, i) => (
              <li
                key={m.symbol}
                role="option"
                aria-selected={i === highlighted}
                onMouseDown={(e) => {
                  // mousedown so the click registers BEFORE the input's
                  // blur from the surrounding click-outside handler.
                  e.preventDefault();
                  navigate(m.symbol);
                }}
                onMouseEnter={() => setHighlighted(i)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 10px',
                  borderRadius: 6,
                  background: i === highlighted ? t.surface : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_MONO,
                    fontSize: 13,
                    color: t.text,
                    fontWeight: 600,
                    minWidth: 90,
                  }}
                >
                  {m.symbol}
                </span>
                <span
                  style={{
                    fontSize: 12,
                    color: t.text2,
                    flex: 1,
                    minWidth: 0,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {m.name ?? m.sub_industry}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    color: t.text3,
                    fontFamily: FONT_MONO,
                  }}
                >
                  ₹{m.close.toFixed(0)}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
