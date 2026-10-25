'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  AlertTriangle,
  CheckCircle2,
  Globe,
  Loader2,
  RotateCw,
} from 'lucide-react';
import {
  ApiError,
  ScanResponse,
  createScan,
  isValidScanUrl,
} from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { SeverityBadge } from '@/components/ui/SeverityBadge';

const EXAMPLE_URLS = [
  { label: 'example.com', url: 'https://example.com' },
  { label: 'github.com', url: 'https://github.com' },
  { label: 'cloudflare.com', url: 'https://cloudflare.com' },
];

function ScanWorkflow() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [url, setUrl] = useState(searchParams.get('url') ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const submittedUrlRef = useRef<string>('');

  const urlIsValid = isValidScanUrl(url);
  const showInlineError = url.trim().length > 0 && !urlIsValid;

  // Elapsed-seconds ticker while a scan request is in flight. The backend
  // performs the whole scan synchronously, so this reflects real elapsed
  // time rather than a simulated progress percentage.
  useEffect(() => {
    if (!submitting) return;
    setElapsed(0);
    const startedAt = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [submitting]);

  const startScan = useCallback(
    async (target: string) => {
      const trimmed = target.trim();
      if (!trimmed) {
        setError('Enter a URL to scan, for example https://example.com');
        inputRef.current?.focus();
        return;
      }
      if (!isValidScanUrl(trimmed)) {
        setError(
          'That does not look like a valid HTTP or HTTPS URL. Include the scheme, e.g. https://example.com'
        );
        inputRef.current?.focus();
        return;
      }

      setError(null);
      setResult(null);
      setSubmitting(true);
      submittedUrlRef.current = trimmed;

      try {
        const scan = await createScan(trimmed);
        if (scan.status === 'completed') {
          setResult(scan);
          // Brief pause so the completion state is perceivable, then navigate.
          setTimeout(() => router.push(`/scan/${scan.scan_id}`), 900);
        } else {
          // Validation, SSRF, or collection failure: show it inline with recovery actions.
          setResult(scan);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 429) {
          setError('You are scanning too frequently. Please wait a minute and try again.');
        } else if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('An unexpected error occurred while starting the scan.');
        }
      } finally {
        setSubmitting(false);
      }
    },
    [router]
  );

  // Auto-start when arriving with ?url= from the landing page.
  const prefilled = searchParams.get('url');
  const autoStarted = useRef(false);
  useEffect(() => {
    if (prefilled && !autoStarted.current) {
      autoStarted.current = true;
      startScan(prefilled);
    }
  }, [prefilled, startScan]);

  const failedResult = result && result.status !== 'completed' ? result : null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
          <Globe className="h-4 w-4" aria-hidden="true" />
          Security scan
        </span>
        <h1 className="text-balance mt-5 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
          Scan a website
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-text-secondary">
          Tracera will observe the site&apos;s public response and report
          evidence-backed findings. Scans typically finish in a few seconds.
        </p>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          startScan(url);
        }}
        className="mt-10 rounded-2xl border border-border bg-card p-6 shadow-card sm:p-8"
        noValidate
      >
        <label htmlFor="scan-url" className="block text-sm font-medium text-text-secondary">
          Target URL
        </label>
        <div className="relative mt-2">
          <Globe
            className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted"
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            id="scan-url"
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
            disabled={submitting}
            autoFocus
            aria-invalid={Boolean(error) || showInlineError}
            aria-describedby={error ? 'scan-url-error' : showInlineError ? 'scan-url-inline-error' : undefined}
            className={`w-full rounded-xl border bg-surface py-3.5 pl-12 pr-4 text-base text-text-primary placeholder:text-text-muted transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60 ${
              error || showInlineError ? 'border-danger' : 'border-border focus:border-primary'
            }`}
          />
        </div>
        {showInlineError && !error && (
          <p id="scan-url-inline-error" className="mt-2 text-sm text-danger">
            Enter a valid HTTP or HTTPS URL, including the scheme (https://…).
          </p>
        )}
        {error && (
          <p id="scan-url-error" role="alert" className="mt-2 text-sm text-danger">
            {error}
          </p>
        )}

        <div className="mt-6">
          <Button
            type="submit"
            size="lg"
            fullWidth
            loading={submitting}
            disabled={!urlIsValid && !submitting}
          >
            {submitting ? 'Scanning…' : 'Start security scan'}
          </Button>
        </div>

        {/* Real elapsed time while the backend runs the scan */}
        {submitting && (
          <div className="mt-6 rounded-xl border border-border bg-surface p-4" role="status" aria-live="polite">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
              <div className="flex-1">
                <p className="text-sm font-medium text-text-primary">
                  Observing {submittedUrlRef.current || 'target'}…
                </p>
                <p className="mt-0.5 text-xs text-text-secondary">
                  Validating the target, fetching the public response, and running
                  security rules. {elapsed}s elapsed.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Completion state */}
        {result && result.status === 'completed' && (
          <div
            className="mt-6 flex items-center gap-4 rounded-xl border border-success/30 bg-success-light/40 p-4"
            role="status"
            aria-live="polite"
          >
            <CheckCircle2 className="h-6 w-6 flex-shrink-0 text-success" aria-hidden="true" />
            <div className="flex-1">
              <p className="font-medium text-text-primary">Scan completed</p>
              <p className="text-sm text-text-secondary">Opening the results…</p>
            </div>
            {result.risk_tier && <SeverityBadge severity={result.risk_tier} size="md" />}
          </div>
        )}

        {/* Failure state with recovery actions */}
        {failedResult && (
          <div
            className="mt-6 rounded-xl border border-danger/30 bg-danger-light/40 p-4"
            role="alert"
          >
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-danger" aria-hidden="true" />
              <div className="flex-1">
                <p className="font-medium text-text-primary">
                  The scan could not be completed
                </p>
                <p className="mt-1 text-sm text-text-secondary">
                  {failedResult.error || 'The target could not be analyzed.'}
                </p>
                {failedResult.error_code && (
                  <p className="mt-1 font-mono text-xs text-text-muted">
                    Code: {failedResult.error_code}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => startScan(failedResult.url || submittedUrlRef.current)}
                  >
                    <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
                    Try again
                  </Button>
                  <Link
                    href="/scan"
                    className="inline-flex items-center rounded-lg px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:text-text-primary focus-ring"
                  >
                    Start over
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </form>

      <div className="mt-8 text-center">
        <p className="text-sm text-text-muted">Try an example:</p>
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {EXAMPLE_URLS.map((example) => (
            <button
              key={example.url}
              type="button"
              onClick={() => {
                setUrl(example.url);
                setError(null);
              }}
              disabled={submitting}
              className="rounded-lg border border-border bg-card px-3.5 py-1.5 font-mono text-xs text-text-secondary transition-colors hover:border-primary/40 hover:text-text-primary focus-ring disabled:opacity-50"
            >
              {example.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ScanPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="h-64 animate-pulse rounded-2xl bg-muted" aria-label="Loading scan form" />
        </div>
      }
    >
      <ScanWorkflow />
    </Suspense>
  );
}
