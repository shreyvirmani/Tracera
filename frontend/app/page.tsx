'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  CheckCircle2,
  Cookie,
  Gauge,
  Globe,
  Lock,
  Radar,
  ServerCog,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { isValidScanUrl } from '@/lib/api';
import { TraceraLogo } from '@/components/layout/Navbar';

const WORKFLOW_STEPS = [
  {
    icon: Globe,
    title: 'Validate the target',
    description:
      'Every URL is canonicalized and screened before any request is made. Private, loopback, and other prohibited destinations are refused.',
  },
  {
    icon: Radar,
    title: 'Observe the public response',
    description:
      'Tracera fetches the publicly served response with strict timeouts, size limits, and per-hop redirect validation. No intrusion, no exploitation.',
  },
  {
    icon: SlidersHorizontal,
    title: 'Run deterministic rules',
    description:
      'A rule engine evaluates the extracted signals — security headers, cookies, TLS metadata, and response characteristics — against concrete checks.',
  },
  {
    icon: Gauge,
    title: 'Score and report',
    description:
      'Findings are aggregated into a 0–100 risk score with severity tiers, evidence, and recommended remediation for each finding.',
  },
];

const FINDING_AREAS = [
  {
    icon: Lock,
    title: 'Transport security',
    description:
      'HTTPS usage, HSTS policy, and TLS protocol characteristics observed on the connection.',
  },
  {
    icon: ShieldCheck,
    title: 'Security headers',
    description:
      'Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy.',
  },
  {
    icon: Cookie,
    title: 'Cookie handling',
    description:
      'Secure and HttpOnly attributes and SameSite policy on cookies set by the response.',
  },
  {
    icon: ServerCog,
    title: 'Configuration disclosure',
    description:
      'Server version banners, X-Powered-By leaks, and risky CORS combinations such as wildcard origins with credentials.',
  },
  {
    icon: Globe,
    title: 'Content hygiene',
    description:
      'Mixed content served over HTTP from an HTTPS page, and unusually large response bodies.',
  },
];

export default function LandingPage() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError('Enter a URL to scan, for example https://example.com');
      return;
    }
    if (!isValidScanUrl(trimmed)) {
      setError('Enter a valid HTTP or HTTPS URL, for example https://example.com');
      return;
    }
    setError(null);
    router.push(`/scan?url=${encodeURIComponent(trimmed)}`);
  };

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-[480px] bg-[radial-gradient(60%_60%_at_50%_0%,rgb(var(--primary)/0.12),transparent_70%)]"
        />
        <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-20 sm:px-6 lg:px-8 lg:pt-28">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              Passive website risk assessment
            </span>
            <h1 className="text-balance mt-6 text-4xl font-bold tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
              Understand your website&apos;s security posture
              <span className="block text-primary">with evidence, not guesswork</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-text-secondary">
              Tracera observes the publicly available response from a website,
              runs deterministic security checks, and produces an evidence-backed
              risk report you can act on and share.
            </p>

            {/* Scan input */}
            <form onSubmit={handleSubmit} className="mx-auto mt-10 max-w-xl" noValidate>
              <label htmlFor="landing-url" className="sr-only">
                Website URL to scan
              </label>
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <Globe
                    className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted"
                    aria-hidden="true"
                  />
                  <input
                    id="landing-url"
                    type="url"
                    inputMode="url"
                    value={url}
                    onChange={(event) => {
                      setUrl(event.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="https://example.com"
                    autoComplete="url"
                    spellCheck={false}
                    aria-invalid={Boolean(error)}
                    aria-describedby={error ? 'landing-url-error' : undefined}
                    className={`w-full rounded-xl border bg-card py-3.5 pl-12 pr-4 text-base text-text-primary placeholder:text-text-muted transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
                      error ? 'border-danger' : 'border-border focus:border-primary'
                    }`}
                  />
                </div>
                <Button type="submit" size="lg" className="sm:px-6">
                  Scan a site
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
              {error && (
                <p id="landing-url-error" role="alert" className="mt-2 text-sm text-danger">
                  {error}
                </p>
              )}
              <p className="mt-3 text-xs text-text-muted">
                Tracera only requests publicly accessible pages and never attempts
                exploitation. Scan targets you are authorized to assess.
              </p>
            </form>
          </div>

          {/* Illustrative product preview */}
          <div className="mx-auto mt-16 max-w-4xl">
            <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-card">
              <div className="flex items-center gap-2 border-b border-border bg-surface px-4 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-danger/60" aria-hidden="true" />
                <span className="h-2.5 w-2.5 rounded-full bg-warning/60" aria-hidden="true" />
                <span className="h-2.5 w-2.5 rounded-full bg-success/60" aria-hidden="true" />
                <span className="ml-3 rounded-md border border-border bg-background px-3 py-1 font-mono text-xs text-text-muted">
                  tracera · scan report
                </span>
                <span className="ml-auto rounded-full border border-border bg-background px-2.5 py-0.5 text-[11px] text-text-muted">
                  Illustrative preview
                </span>
              </div>
              <div className="grid gap-6 p-6 sm:grid-cols-[auto_1fr] sm:p-8">
                <div className="flex items-center gap-4 sm:flex-col sm:items-start">
                  <div className="relative h-24 w-24">
                    <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                      <circle cx="60" cy="60" r="52" fill="none" strokeWidth="10" className="stroke-border" />
                      <circle
                        cx="60"
                        cy="60"
                        r="52"
                        fill="none"
                        strokeWidth="10"
                        strokeLinecap="round"
                        className="stroke-warning"
                        strokeDasharray={2 * Math.PI * 52}
                        strokeDashoffset={2 * Math.PI * 52 * 0.62}
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-warning">
                      38
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wider text-text-muted">Risk tier</p>
                    <p className="text-xl font-bold text-warning">Medium risk</p>
                  </div>
                </div>
                <div className="space-y-2.5">
                  {[
                    { severity: 'High', label: 'Missing Content-Security-Policy header', color: 'text-severity-high bg-severity-high/10 border-severity-high/30' },
                    { severity: 'Medium', label: 'HSTS policy not established', color: 'text-warning bg-warning/10 border-warning/30' },
                    { severity: 'Low', label: 'Server version disclosed in headers', color: 'text-severity-low bg-severity-low/10 border-severity-low/30' },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3"
                    >
                      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${row.color}`}>
                        {row.severity}
                      </span>
                      <span className="truncate text-sm text-text-primary">{row.label}</span>
                    </div>
                  ))}
                  <p className="pt-1 text-xs text-text-muted">
                    Every finding links to the observed evidence and a recommended fix.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border bg-surface/40">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text-primary">
              How Tracera works
            </h2>
            <p className="mt-3 text-text-secondary">
              A transparent pipeline: every result traces back to an observed fact.
            </p>
          </div>
          <ol className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {WORKFLOW_STEPS.map((step, index) => (
              <li key={step.title} className="rounded-xl border border-border bg-card p-6">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <step.icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span className="font-mono text-xs text-text-muted">
                    Step {index + 1}
                  </span>
                </div>
                <h3 className="mt-4 font-semibold text-text-primary">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                  {step.description}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Finding types */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text-primary">
              What Tracera checks
            </h2>
            <p className="mt-3 text-text-secondary">
              Findings come from a deterministic rule engine covering these areas.
            </p>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FINDING_AREAS.map((area) => (
              <div
                key={area.title}
                className="rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong"
              >
                <area.icon className="h-6 w-6 text-primary" aria-hidden="true" />
                <h3 className="mt-4 font-semibold text-text-primary">{area.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                  {area.description}
                </p>
              </div>
            ))}
            <div className="rounded-xl border border-primary/25 bg-primary/5 p-6">
              <h3 className="font-semibold text-text-primary">Deterministic, evidence-backed</h3>
              <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                Each finding records the rule that produced it, the evidence
                observed, and a confidence level — so results can be verified
                rather than trusted blindly.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Risk scoring */}
      <section className="border-t border-border bg-surface/40">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-text-primary">
                Risk scoring you can reason about
              </h2>
              <p className="mt-4 leading-relaxed text-text-secondary">
                Tracera&apos;s score is a transparent aggregation, not a black box.
                Each finding contributes a fixed weight based on its severity, and
                the total is capped at 100.
              </p>
              <ul className="mt-6 space-y-3">
                {[
                  'Critical findings weigh 25 points, high 15, medium 10, low 5, and info 1.',
                  'Scores map to four tiers: low (0–24), medium (25–49), high (50–74), and critical (75–100).',
                  'The score describes the issues these checks found — it is not a probability of compromise.',
                  'A clean scan means no issues were found by these rules, not that a site is secure.',
                ].map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-success" aria-hidden="true" />
                    <span className="text-sm leading-relaxed text-text-secondary">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-border bg-card p-8 shadow-card">
              <div className="space-y-4">
                {[
                  { tier: 'Low', range: '0–24', color: 'bg-success' },
                  { tier: 'Medium', range: '25–49', color: 'bg-warning' },
                  { tier: 'High', range: '50–74', color: 'bg-severity-high' },
                  { tier: 'Critical', range: '75–100', color: 'bg-danger' },
                ].map((tier) => (
                  <div key={tier.tier} className="flex items-center gap-4">
                    <span className="w-20 text-sm font-medium text-text-primary">{tier.tier}</span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <div className={`h-full rounded-full ${tier.color}`} style={{ width: tier.range === '0–24' ? '25%' : tier.range === '25–49' ? '50%' : tier.range === '50–74' ? '75%' : '100%' }} />
                    </div>
                    <span className="w-20 text-right font-mono text-xs text-text-muted">{tier.range}</span>
                  </div>
                ))}
              </div>
              <p className="mt-6 border-t border-border pt-4 text-xs leading-relaxed text-text-muted">
                Tier boundaries are fixed by the scoring engine, so results are
                comparable across scans.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-7xl px-4 py-20 text-center sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold tracking-tight text-text-primary">
            Run your first scan
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-text-secondary">
            Enter a URL and get an evidence-backed report in seconds.
          </p>
          <div className="mt-8">
            <Link href="/scan">
              <Button size="lg">
                Start scanning
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface/40">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-between gap-8 md:flex-row md:items-start">
            <div className="max-w-sm">
              <TraceraLogo />
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                Defensive website risk assessment. Tracera observes only publicly
                accessible responses and reports evidence-backed findings.
              </p>
            </div>
            <nav aria-label="Footer navigation" className="grid grid-cols-2 gap-x-12 gap-y-2 text-sm">
              <Link href="/scan" className="text-text-secondary transition-colors hover:text-text-primary">
                New scan
              </Link>
              <Link href="/dashboard" className="text-text-secondary transition-colors hover:text-text-primary">
                Dashboard
              </Link>
              <Link href="/history" className="text-text-secondary transition-colors hover:text-text-primary">
                Scan history
              </Link>
              <a
                href="http://localhost:8000/docs"
                className="text-text-secondary transition-colors hover:text-text-primary"
              >
                API docs
              </a>
            </nav>
          </div>
          <div className="mt-10 border-t border-border pt-6 text-xs text-text-muted">
            <p>© {new Date().getFullYear()} Tracera. Use responsibly: scan only targets you are authorized to assess.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
