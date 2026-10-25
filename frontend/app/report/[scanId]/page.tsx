'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  FileText,
  Printer,
} from 'lucide-react';
import {
  ApiError,
  Finding,
  ScanResponse,
  getScan,
  getScanExportUrl,
} from '@/lib/api';
import { formatBytes, formatDate } from '@/lib/format';
import { RiskScoreCard } from '@/components/ui/RiskScoreCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { StatusBadge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton, SkeletonSeveritySection } from '@/components/ui/Skeleton';

function ReportFinding({ finding }: { finding: Finding }) {
  const hasEvidence = finding.evidence && Object.keys(finding.evidence).length > 0;
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-text-primary">{finding.title}</h3>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-muted">
            <span>
              Rule <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-text-secondary">{finding.rule_id}</code>
            </span>
            <span className="capitalize">{finding.category}</span>
            <span>Confidence {Math.round(finding.confidence * 100)}%</span>
          </div>
        </div>
        <SeverityBadge severity={finding.severity} size="md" />
      </div>
      <p className="mt-3 text-sm leading-relaxed text-text-secondary">
        {finding.description}
      </p>
      {hasEvidence && (
        <details className="mt-3 group">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 text-sm font-medium text-primary transition-colors hover:text-primary-hover focus-ring rounded">
            <FileText className="h-4 w-4" aria-hidden="true" />
            View evidence
          </summary>
          <pre className="scrollbar-thin mt-2 max-h-56 overflow-auto rounded-lg border border-border bg-background p-3 text-xs leading-relaxed text-text-secondary">
            {JSON.stringify(finding.evidence, null, 2)}
          </pre>
        </details>
      )}
      <div className="mt-3 border-t border-border pt-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-text-muted">
          Recommendation
        </p>
        <p className="mt-1 text-sm leading-relaxed text-text-secondary">
          {finding.recommendation}
        </p>
      </div>
    </div>
  );
}

function ReportContent({ scan }: { scan: ScanResponse }) {
  const recommendations = Array.from(
    new Set((scan.findings ?? []).map((f) => f.recommendation))
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between print:hidden">
        <Link
          href={`/scan/${scan.scan_id}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-text-secondary transition-colors hover:text-text-primary focus-ring rounded"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to results
        </Link>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3.5 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-elevated focus-ring"
          >
            <Printer className="h-4 w-4" aria-hidden="true" />
            Print / PDF
          </button>
          <a
            href={getScanExportUrl(scan.scan_id)}
            download
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-semibold text-background transition-colors hover:bg-primary-hover focus-ring"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download JSON
          </a>
        </div>
      </div>

      {/* Report header */}
      <header className="mt-6 rounded-2xl border border-border bg-card p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-primary">
              Tracera risk assessment report
            </p>
            <h1 className="mt-2 break-all text-2xl font-bold tracking-tight text-text-primary">
              {scan.url || scan.canonical_url || 'Unknown target'}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-text-secondary">
              <span>Scanned {formatDate(scan.created_at)}</span>
              <StatusBadge status={scan.status} size="sm" />
              <span className="font-mono text-xs text-text-muted">
                ID {scan.scan_id}
              </span>
            </div>
          </div>
        </div>
        {scan.metadata && (
          <dl className="mt-6 grid grid-cols-2 gap-3 border-t border-border pt-5 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-text-muted">Status code</dt>
              <dd className="mt-0.5 font-mono font-semibold text-text-primary">
                {scan.metadata.status_code}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-text-muted">Response time</dt>
              <dd className="mt-0.5 font-mono font-semibold text-text-primary">
                {Math.round(scan.metadata.response_time_ms)} ms
              </dd>
            </div>
            <div>
              <dt className="text-xs text-text-muted">Redirects</dt>
              <dd className="mt-0.5 font-mono font-semibold text-text-primary">
                {scan.metadata.redirect_count}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-text-muted">Body size</dt>
              <dd className="mt-0.5 font-mono font-semibold text-text-primary">
                {formatBytes(scan.metadata.content_length)}
              </dd>
            </div>
          </dl>
        )}
      </header>

      {/* Score */}
      <div className="mt-6">
        <RiskScoreCard
          score={scan.risk_score}
          tier={scan.risk_tier}
          scoreSource={scan.score_source}
          showDetails
        />
      </div>

      {/* Findings */}
      <section className="mt-8" aria-label="Findings">
        <h2 className="text-xl font-bold text-text-primary">
          Findings{' '}
          <span className="text-base font-medium text-text-muted">
            ({scan.findings?.length ?? 0})
          </span>
        </h2>
        {scan.findings && scan.findings.length > 0 ? (
          <div className="mt-4 space-y-4">
            {scan.findings.map((finding) => (
              <ReportFinding key={finding.id} finding={finding} />
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-border bg-card p-8 text-center">
            <p className="font-medium text-text-primary">No findings recorded</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-text-secondary">
              The checks that ran did not identify any issues on this target.
              This reflects only the rules that executed — it is not a guarantee
              that the site is secure.
            </p>
          </div>
        )}
      </section>

      {/* Consolidated recommendations */}
      {recommendations.length > 0 && (
        <section className="mt-8" aria-label="Recommendations">
          <h2 className="text-xl font-bold text-text-primary">Recommendations</h2>
          <ol className="mt-4 space-y-3">
            {recommendations.map((recommendation, index) => (
              <li key={index} className="flex gap-3 rounded-xl border border-border bg-card p-4">
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
                  {index + 1}
                </span>
                <p className="text-sm leading-relaxed text-text-secondary">
                  {recommendation}
                </p>
              </li>
            ))}
          </ol>
        </section>
      )}

      <footer className="mt-10 rounded-xl border border-border bg-surface p-5 text-xs leading-relaxed text-text-muted">
        <p>
          This report reflects only the checks Tracera executed at scan time
          against publicly observable responses. A lack of findings is not a
          guarantee of security. The JSON export contains the same data shown
          on this page, generated by the API from stored scan results.
        </p>
      </footer>
    </div>
  );
}

export default function ReportPage() {
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
          message:
            err.status === 404
              ? 'This scan does not exist or has been removed.'
              : err.message,
          status: err.status,
        });
      } else {
        setError({ message: 'Failed to load the report.', status: 0 });
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
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
        <Skeleton className="h-9 w-2/3 max-w-lg" />
        <Skeleton className="mt-3 h-5 w-56" />
        <Skeleton className="mt-8 h-36 rounded-xl" />
        <div className="mt-8 space-y-4">
          <SkeletonSeveritySection />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
        <ErrorState
          title={error.status === 404 ? 'Report not found' : 'Failed to load report'}
          message={error.message}
          onRetry={load}
          fullScreen
        />
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
        <EmptyState
          size="lg"
          title="Report not found"
          description="The requested report could not be found."
          action={{ label: 'Start a new scan', href: '/scan' }}
        />
      </div>
    );
  }

  if (scan.status !== 'completed') {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
        <EmptyState
          size="lg"
          title="No report available"
          description={
            scan.status === 'failed'
              ? 'This scan did not complete, so there is no report to show. You can retry it from the results page.'
              : 'This scan has not completed yet.'
          }
          action={{ label: 'View scan status', href: `/scan/${scan.scan_id}` }}
        />
      </div>
    );
  }

  return <ReportContent scan={scan} />;
}
