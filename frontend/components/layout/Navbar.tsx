'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, Moon, ShieldHalf, Sun, X } from 'lucide-react';
import { useTheme } from '@/lib/theme/ThemeProvider';
import { Button } from '../ui/Button';

const APP_LINKS = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'New Scan', href: '/scan' },
  { label: 'History', href: '/history' },
];

export function TraceraLogo({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5" aria-label="Tracera home">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/30">
        <ShieldHalf className="h-4.5 w-4.5 h-5 w-5 text-primary" aria-hidden="true" />
      </span>
      {!compact && (
        <span className="text-lg font-bold tracking-tight text-text-primary">
          Tracera
        </span>
      )}
    </Link>
  );
}

export function ThemeToggleButton() {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="focus-ring rounded-lg p-2 text-text-secondary transition-colors hover:bg-surface hover:text-text-primary"
      aria-label={mounted && theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {mounted && theme === 'dark' ? (
        <Sun className="h-5 w-5" aria-hidden="true" />
      ) : (
        <Moon className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  );
}

export function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <TraceraLogo />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
            {APP_LINKS.map((link) => {
              const isActive =
                pathname === link.href ||
                (link.href !== '/' && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={isActive ? 'page' : undefined}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-ring ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-text-secondary hover:bg-surface hover:text-text-primary'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggleButton />
          <div className="hidden sm:block">
            <Link href="/scan">
              <Button size="sm">New Scan</Button>
            </Link>
          </div>
          <button
            type="button"
            className="focus-ring rounded-lg p-2 text-text-secondary hover:bg-surface md:hidden"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav
          className="border-t border-border bg-background px-4 pb-4 pt-2 md:hidden"
          aria-label="Mobile navigation"
        >
          {APP_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className={`block rounded-lg px-3 py-2.5 text-sm font-medium ${
                pathname === link.href
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:bg-surface hover:text-text-primary'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}

export default Navbar;
