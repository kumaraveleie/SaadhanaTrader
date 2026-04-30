'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from './theme';
import { BrandMark } from './brand-mark';

type NavItem = { href: string; label: string };

const NAV_LINKS: NavItem[] = [
  { href: '/scanner', label: 'Scanner' },
  { href: '/research', label: 'Research' },
  { href: '/about', label: 'About' },
];

const MOBILE_LINKS: NavItem[] = [
  { href: '/scanner', label: 'Scanner' },
  { href: '/research', label: 'Research' },
  { href: '/about', label: 'About' },
  { href: '/about/phases', label: 'Phases' },
  { href: '/about#disclaimer', label: 'Disclaimer' },
];

export function Nav() {
  const { t } = useTheme();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const burgerRef = useRef<HTMLButtonElement | null>(null);
  const drawerRef = useRef<HTMLDivElement | null>(null);

  // Escape closes; click outside closes; focus trap inside drawer
  useEffect(() => {
    if (!menuOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        burgerRef.current?.focus();
        return;
      }
      if (e.key === 'Tab' && drawerRef.current) {
        const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    function onClick(e: MouseEvent) {
      if (!drawerRef.current || !burgerRef.current) return;
      if (
        !drawerRef.current.contains(e.target as Node) &&
        !burgerRef.current.contains(e.target as Node)
      ) {
        setMenuOpen(false);
      }
    }
    window.addEventListener('keydown', onKey);
    window.addEventListener('mousedown', onClick);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('mousedown', onClick);
    };
  }, [menuOpen]);

  function isActive(href: string): boolean {
    const path = href.split('#')[0];
    if (path === '/about' && pathname?.startsWith('/about/')) {
      // /about exact match only — sub-routes get their own active state
      return pathname === '/about';
    }
    return pathname === path;
  }

  return (
    <nav
      style={{
        padding: '20px clamp(20px, 5vw, 64px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: `1px solid ${t.border}`,
        background: t.bg,
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backdropFilter: 'blur(8px)',
      }}
    >
      <Link href="/" style={{ textDecoration: 'none', color: t.text, display: 'inline-flex' }}>
        <BrandMark size={32} color={t.text} accent={t.accent} />
      </Link>

      <div
        className="saadhana-nav-links"
        style={{ display: 'flex', gap: 28, alignItems: 'center', fontSize: 14 }}
      >
        {NAV_LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            style={{
              color: isActive(l.href) ? t.accent : t.text2,
              fontWeight: 500,
              textDecoration: 'none',
            }}
          >
            {l.label}
          </Link>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <Link
          href="/scanner"
          style={{
            padding: '10px 18px',
            fontSize: 14,
            fontWeight: 600,
            borderRadius: 8,
            background: t.accent,
            color: t.bg,
            cursor: 'pointer',
            textDecoration: 'none',
            letterSpacing: '-0.01em',
          }}
        >
          Open Scanner →
        </Link>

        <button
          ref={burgerRef}
          type="button"
          className="saadhana-nav-burger"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          aria-controls="saadhana-mobile-drawer"
          onClick={() => setMenuOpen((v) => !v)}
          style={{
            background: 'transparent',
            border: `1px solid ${t.border}`,
            borderRadius: 8,
            padding: '8px 10px',
            color: t.text2,
            cursor: 'pointer',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {menuOpen ? <CloseIcon /> : <HamburgerIcon />}
        </button>
      </div>

      {menuOpen && (
        <div
          ref={drawerRef}
          id="saadhana-mobile-drawer"
          role="navigation"
          aria-label="Mobile menu"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            width: '100vw',
            background: t.surface,
            borderBottom: `1px solid ${t.border}`,
            padding: '20px clamp(20px, 5vw, 64px)',
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
            boxShadow: '0 12px 24px rgba(0,0,0,0.35)',
          }}
        >
          {MOBILE_LINKS.map((l) => {
            const active = isActive(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setMenuOpen(false)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  minHeight: 48,
                  padding: '12px 14px',
                  fontSize: 16,
                  fontWeight: 500,
                  color: active ? t.accent : t.text,
                  textDecoration: 'none',
                  borderRadius: 8,
                  borderLeft: `2px solid ${active ? t.accent : 'transparent'}`,
                  background: active ? t.bg : 'transparent',
                }}
              >
                {l.label}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}

function HamburgerIcon() {
  return (
    <svg
      aria-hidden
      width={22}
      height={18}
      viewBox="0 0 22 18"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <line x1="1" y1="2" x2="21" y2="2" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <line x1="1" y1="9" x2="21" y2="9" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <line x1="1" y1="16" x2="21" y2="16" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      aria-hidden
      width={22}
      height={18}
      viewBox="0 0 22 18"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <line x1="3" y1="2" x2="19" y2="16" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <line x1="19" y1="2" x2="3" y2="16" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}
