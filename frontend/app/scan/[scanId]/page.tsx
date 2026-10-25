'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Calendar,
  Download,
  FileText,
  Globe,
  RotateCw,
  Timer,
} from 'lucide-react';
import {
  ApiError,
  ScanResponse,
  getScan,
  getScanExportUrl,
} from '@/lib/api';
import { formatBytes, formatDate } from '@/lib/format';
import { RiskScoreCard } from '@/components/ui/RiskScoreCard';
import { StatusBadge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import FindingsList from '@/components/FindingsList';
import {
  Skeleton,
  SkeletonSeveritySection,
} from '@/components/ui/Skeleton';

function ScanResults({ scan }: { scan: ScanResponse }) {
  const failed = scan.status !== 'completed';

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      {/* Breadcrumb */}
      <Link
        href="/history"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-text-secondary transition-colors hover:text-text-primary focus-ring rounded"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Scan history
      </Link>

      {/* Target header */}
      <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold tracking-tight text-text-primary sm:text-3xl">
            {scan.url || scan.canonical_url || 'Scan result'}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-text-secondary">
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="h-4 w-4 text-text-muted" aria-hidden="true" />
              {formatDate(scan.created_at)}
            </span>
            <StatusBadge status={scan.status} size="sm" />
            <span className="font-mono text-xs text-text-muted">
              ID {scan.scan_id.slice(0, 8)}
            </span>
          </div>
        </div>
        {!failed && (
          <div className="flex flex-shrink-0 flex-wrap gap-2">
            <a
              href={getScanExportUrl(scan.scan_id)}
              download
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3.5 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-elevated focus-ring"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Export JSON
            </a>
            <Link
              href={`/report/${scan.scan_id}`}
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3.5 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-elevated focus-ring"
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
              Full report
            </Link>
          </div>
        )}
      </div>

      {failed ? (
        /* Failed scan: explain what happened and how to recover */
        <div className="mt-8 rounded-xl border border-danger/30 bg-danger-light/40 p-6">
          <div className="flex items-start gap-3">
            <RotateCw className="mt-1 h-5 w-5 flex-shrink-0 text-danger" aria-hidden="true" />
            <div>
              <h2 className="text-lg font-semibold text-text-primary">
                This scan did not complete
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                {scan.error || 'The target could not be analyzed.'}
              </p>
              {scan.error_code && (
                <p className="mt-2 inline-block rounded-md border border-border bg-surface px-2 py-1 font-mono text-xs text-text-secondary">
                  {scan.error_code}
                </p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                {scan.url && (
                  <Link
                    href={`/scan?url=${encodeURIComponent(scan.url)}`}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-background transition-colors hover:bg-primary-hover focus-ring"
                  >
                    <RotateCw className="h-4 w-4" aria-hidden="true" />
                    Retry this scan
                  </Link>
                )}
                <Link
                  href="/scan"
                  className="inline-flex items-center rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-elevated focus-ring"
                >
                  Scan a different URL
                </Link>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Risk score */}
          <div className="mt-8">
            <RiskScoreCard
              score={scan.risk_score}
              tier={scan.risk_tier}
              scoreSource={scan.score_source}
              showDetails
            />
          </div>

          {/* Observed response metadata (real, persisted values) */}
          {scan.metadata && (
            <div className="mt-6 rounded-xl border border-border bg-card p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-text-muted">
                Observed response
              </h2>
              <dl className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-5">
                <div className="rounded-lg bg-surface p-3">
                  <dt className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Globe className="h-3.5 w-3.5" aria-hidden="true" />
                    Status code
                  </dt>
                  <dd className="mt-1 font-mono text-lg font-semibold text-text-primary">
                    {scan.metadata.status_code}
                  </dd>
                </div>
                <div className="rounded-lg bg-surface p-3">
                  <dt className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Timer className="h-3.5 w-3.5" aria-hidden="true" />
                    Response time
                  </dt>
                  <dd className="mt-1 font-mono text-lg font-semibold text-text-primary">
                    {Math.round(scan.metadata.response_time_ms)} ms
                  </dd>
                </div>
                <div className="rounded-lg bg-surface p-3">
                  <dt className="flex items-center gap-1.5 text-xs text-text-muted">
                    <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
                    Redirects
                  </dt>
                  <dd className="mt-1 font-mono text-lg font-semibold text-text-primary">
                    {scan.metadata.redirect_count}
                  </dd>
                </div>
                <div className="rounded-lg bg-surface p-3">
                  <dt className="flex items-center gap-1.5 text-xs text-text-muted">
                    <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                    Body size
                  </dt>
                  <dd className="mt-1 font-mono text-lg font-semibold text-text-primary">
                    {formatBytes(scan.metadata.content_length)}
                  </dd>
                </div>
                <div className="col-span-2 rounded-lg bg-surface p-3 md:col-span-1">
                  <dt className="text-xs text-text-muted">Final URL</dt>
                  <dd className="mt-1 truncate font-mono text-xs text-text-secondary" title={scan.metadata.final_url}>
                    {scan.metadata.final_url}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {/* Findings */}
          <div className="mt-8">
            <FindingsList findings={scan.findings ?? []} />
          </div>
        </>
      )}
    </div>
  );
}

export default function ScanResultPage() {
  const params = useParams<{ scanId: string }>();
  const scanId = params?.scanId ?? '';
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; status: number } | null>(null);

  const load = useCallback(async () => {
    if (!scanId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getScan(scanId);
      setScan(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError({
          message: err.status === 404 ? 'This scan does not exist or has been removed.' : err.message,
          status: err.status,
        });
      } else {
        setError({ message: 'Failed to load the scan.', status: 0 });
      }
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="mt-4 h-9 w-2/3 max-w-lg" />
        <Skeleton className="mt-3 h-5 w-48" />
        <Skeleton className="mt-8 h-40 rounded-xl" />
        <div className="mt-8 space-y-6">
          <SkeletonSeveritySection />
          <SkeletonSeveritySection />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <ErrorState
          title={error.status === 404 ? 'Scan not found' : 'Failed to load scan'}
          message={error.message}
          onRetry={load}
          fullScreen
        />
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <EmptyState
          size="lg"
          title="Scan not found"
          description="The requested scan could not be found."
          action={{ label: 'Start a new scan', href: '/scan' }}
        />
      </div>
    );
  }

  return <ScanResults scan={scan} />;
}
