'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  FileJson,
  Gauge,
  ListChecks,
  Plus,
} from 'lucide-react';
import {
  ApiError,
  ScanResponse,
  SEVERITY_ORDER,
  SeverityLevel,
  listScans,
} from '@/lib/api';
import {
  formatRelativeDate,
  truncateUrl,
} from '@/lib/format';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { StatusBadge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton, SkeletonStatCard, SkeletonTable } from '@/components/ui/Skeleton';
import { PageHeader } from '@/components/ui/PageHeader';

const PAGE_SIZE = 8;

type SeverityCounts = Record<SeverityLevel, number>;

export default function DashboardPage() {
  const [scans, setScans] = useState<ScanResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listScans({ limit: PAGE_SIZE, offset: 0 });
      setScans(data.scans);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Failed to load dashboard data.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const stats = useMemo(() => {
    const completed = scans.filter((s) => s.status === 'completed');
    const findings = scans.flatMap((s) => s.findings ?? []);
    const severityCounts: SeverityCounts = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    };
    for (const finding of findings) {
      const key = finding.severity.toLowerCase();
      if (key in severityCounts) severityCounts[key as SeverityLevel] += 1;
    }
    const scored = completed.filter((s) => s.risk_score !== null);
    const avgRisk =
      scored.length > 0
        ? Math.round(
            scored.reduce((sum, s) => sum + (s.risk_score ?? 0), 0) / scored.length
          )
        : null;
    return {
      totalScans: total,
      completedCount: completed.length,
      failedCount: scans.filter((s) => s.status === 'failed').length,
      totalFindings: findings.length,
      severityCounts,
      avgRisk,
    };
  }, [scans, total]);

  const maxSeverityCount = useMemo(
    () => Math.max(1, ...(Object.values(stats.severityCounts) as number[])),
    [stats.severityCounts]
  );

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="mt-2 h-5 w-96" />
        <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonStatCard key={i} />
          ))}
        </div>
        <SkeletonTable className="mt-8" rows={5} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <ErrorState title="Failed to load dashboard" message={error} onRetry={load} fullScreen />
      </div>
    );
  }

  const statCards = [
    {
      label: 'Total scans',
      value: stats.totalScans,
      icon: Activity,
      accent: 'text-primary bg-primary/10',
      href: '/history',
    },
    {
      label: 'Findings (recent scans)',
      value: stats.totalFindings,
      icon: ListChecks,
      accent: 'text-warning bg-warning/10',
      href: '/history',
    },
    {
      label: 'High or critical findings',
      value: stats.severityCounts.critical + stats.severityCounts.high,
      icon: AlertTriangle,
      accent: 'text-danger bg-danger/10',
      href: '/history',
    },
    {
      label: 'Avg risk score',
      value: stats.avgRisk === null ? '—' : `${stats.avgRisk}/100`,
      icon: Gauge,
      accent: 'text-secondary bg-secondary/10',
      href: '/history',
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <PageHeader
        title="Dashboard"
        description="Overview of your website risk assessments."
        actions={
          <Link
            href="/scan"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-background transition-colors hover:bg-primary-hover focus-ring"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New scan
          </Link>
        }
      />

      {stats.totalScans === 0 ? (
        <div className="mt-8 rounded-xl border border-border bg-card">
          <EmptyState
            size="lg"
            title="No scans yet"
            description="Run your first scan to see risk scores, findings, and reports here."
            action={{ label: 'Start your first scan', href: '/scan' }}
          />
        </div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {statCards.map((card) => (
              <Link
                key={card.label}
                href={card.href}
                className="group rounded-xl border border-border bg-card p-6 transition-all hover:border-border-strong hover:shadow-card-hover focus-ring"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-text-secondary">{card.label}</p>
                    <p className="mt-2 text-3xl font-bold tabular-nums text-text-primary">
                      {card.value}
                    </p>
                  </div>
                  <span className={`rounded-lg p-2.5 ${card.accent}`}>
                    <card.icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                </div>
              </Link>
            ))}
          </div>

          <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3">
            {/* Severity distribution */}
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="text-lg font-semibold text-text-primary">
                Severity distribution
              </h2>
              <p className="mt-1 text-xs text-text-muted">
                Across the {PAGE_SIZE} most recent scans shown below.
              </p>
              <div className="mt-6 space-y-4">
                {SEVERITY_ORDER.map((severity) => {
                  const count = stats.severityCounts[severity];
                  return (
                    <div key={severity} className="flex items-center gap-3">
                      <span className="w-16 text-xs font-medium capitalize text-text-secondary">
                        {severity}
                      </span>
                      <div
                        className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
                        role="img"
                        aria-label={`${severity}: ${count} findings`}
                      >
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            {
                              critical: 'bg-danger',
                              high: 'bg-severity-high',
                              medium: 'bg-warning',
                              low: 'bg-severity-low',
                              info: 'bg-text-muted',
                            }[severity]
                          }`}
                          style={{ width: `${(count / maxSeverityCount) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 text-right text-sm font-semibold tabular-nums text-text-primary">
                        {count}
                      </span>
                    </div>
                  );
                })}
                {stats.totalFindings === 0 && (
                  <p className="text-sm text-text-secondary">
                    No findings recorded in recent scans.
                  </p>
                )}
              </div>
            </div>

            {/* Recent scans */}
            <div className="overflow-hidden rounded-xl border border-border bg-card lg:col-span-2">
              <div className="flex items-center justify-between border-b border-border px-6 py-4">
                <h2 className="text-lg font-semibold text-text-primary">Recent scans</h2>
                <Link
                  href="/history"
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary transition-colors hover:text-primary-hover focus-ring rounded"
                >
                  View all
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </div>
              {scans.length === 0 ? (
                <EmptyState
                  title="No scans found"
                  description="Scans you run will appear here."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {scans.map((scan) => (
                    <li key={scan.scan_id}>
                      <Link
                        href={`/scan/${scan.scan_id}`}
                        className="flex items-center gap-4 px-6 py-4 transition-colors hover:bg-surface focus-ring-inset"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-text-primary">
                            {truncateUrl(scan.url || scan.metadata?.final_url || scan.scan_id, 45)}
                          </p>
                          <p className="mt-0.5 text-xs text-text-muted">
                            {formatRelativeDate(scan.created_at)} ·{' '}
                            {scan.findings?.length ?? 0} findings
                          </p>
                        </div>
                        <StatusBadge status={scan.status} size="sm" />
                        {scan.risk_tier ? (
                          <SeverityBadge severity={scan.risk_tier} size="sm" />
                        ) : (
                          <span className="w-16" />
                        )}
                        <span className="w-14 text-right text-sm font-semibold tabular-nums text-text-primary">
                          {scan.risk_score !== null ? scan.risk_score : '—'}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Quick actions */}
          <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
            <Link
              href="/scan"
              className="group rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-card focus-ring"
            >
              <Plus className="h-5 w-5 text-primary" aria-hidden="true" />
              <p className="mt-3 font-medium text-text-primary">Start a new scan</p>
              <p className="mt-1 text-sm text-text-secondary">
                Submit a URL for passive analysis.
              </p>
            </Link>
            <Link
              href="/history"
              className="group rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-card focus-ring"
            >
              <Activity className="h-5 w-5 text-primary" aria-hidden="true" />
              <p className="mt-3 font-medium text-text-primary">Browse scan history</p>
              <p className="mt-1 text-sm text-text-secondary">
                Filter and revisit previous reports.
              </p>
            </Link>
            <div className="rounded-xl border border-border bg-card p-5">
              <FileJson className="h-5 w-5 text-text-muted" aria-hidden="true" />
              <p className="mt-3 font-medium text-text-primary">Export reports</p>
              <p className="mt-1 text-sm text-text-secondary">
                Every completed scan can be downloaded as JSON from its report page.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
