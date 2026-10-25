'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, ChevronRight, Search, X } from 'lucide-react';
import {
  ApiError,
  ScanResponse,
  ScanListResponse,
  listScans,
} from '@/lib/api';
import { formatDate, truncateUrl } from '@/lib/format';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { StatusBadge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonTable } from '@/components/ui/Skeleton';
import { PageHeader } from '@/components/ui/PageHeader';

const STATUS_OPTIONS = ['all', 'completed', 'failed', 'pending'] as const;
const TIER_OPTIONS = ['all', 'critical', 'high', 'medium', 'low'] as const;

type StatusFilter = (typeof STATUS_OPTIONS)[number];
type TierFilter = (typeof TIER_OPTIONS)[number];

interface HistoryFilters {
  status: StatusFilter;
  tier: TierFilter;
  search: string;
  page: number;
  limit: number;
}

const DEFAULT_FILTERS: HistoryFilters = {
  status: 'all',
  tier: 'all',
  search: '',
  page: 1,
  limit: 10,
};

export default function ScanHistoryPage() {
  const [scans, setScans] = useState<ScanResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<HistoryFilters>(DEFAULT_FILTERS);
  const [searchInput, setSearchInput] = useState('');

  const fetchScans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: ScanListResponse = await listScans({
        limit: filters.limit,
        offset: (filters.page - 1) * filters.limit,
        status: filters.status === 'all' ? undefined : filters.status,
        tier: filters.tier === 'all' ? undefined : filters.tier,
        search: filters.search || undefined,
      });
      setScans(data.scans);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Failed to load scan history.'
      );
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchScans();
  }, [fetchScans]);

  const hasActiveFilters =
    filters.status !== 'all' || filters.tier !== 'all' || filters.search !== '';

  const clearFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setSearchInput('');
  };

  const totalPages = Math.max(1, Math.ceil(total / filters.limit));

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <PageHeader
        title="Scan history"
        description="All website risk assessments run through this instance."
      />

      {/* Filters */}
      <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setFilters((prev) => ({ ...prev, search: searchInput.trim(), page: 1 }));
          }}
          className="grid gap-4 md:grid-cols-[1fr_auto_auto_auto]"
        >
          <div>
            <label htmlFor="history-search" className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-text-muted">
              Search URL
            </label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted"
                aria-hidden="true"
              />
              <input
                id="history-search"
                type="search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="e.g. example.com"
                className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-8 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchInput('');
                    setFilters((prev) => ({ ...prev, search: '', page: 1 }));
                  }}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-text-muted hover:text-text-primary focus-ring"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
          </div>
          <div>
            <label htmlFor="history-status" className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-text-muted">
              Status
            </label>
            <select
              id="history-status"
              value={filters.status}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  status: event.target.value as StatusFilter,
                  page: 1,
                }))
              }
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary md:w-36"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === 'all' ? 'All statuses' : option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="history-tier" className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-text-muted">
              Risk tier
            </label>
            <select
              id="history-tier"
              value={filters.tier}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  tier: event.target.value as TierFilter,
                  page: 1,
                }))
              }
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary md:w-36"
            >
              {TIER_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === 'all' ? 'All tiers' : option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-background transition-colors hover:bg-primary-hover focus-ring"
            >
              Apply
            </button>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:text-text-primary focus-ring"
              >
                Clear
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Results */}
      {loading && scans.length === 0 ? (
        <SkeletonTable className="mt-6" rows={6} />
      ) : error ? (
        <div className="mt-6">
          <ErrorState title="Failed to load scan history" message={error} onRetry={fetchScans} />
        </div>
      ) : (
        <div className="mt-6 overflow-hidden rounded-xl border border-border bg-card">
          {scans.length === 0 ? (
            <EmptyState
              size="lg"
              title={hasActiveFilters ? 'No scans match these filters' : 'No scans yet'}
              description={
                hasActiveFilters
                  ? 'Try adjusting or clearing the filters above.'
                  : 'Run your first scan to build up history.'
              }
              action={
                hasActiveFilters
                  ? { label: 'Clear filters', onClick: clearFilters, variant: 'secondary' }
                  : { label: 'Start your first scan', href: '/scan' }
              }
            />
          ) : (
            <>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="w-full min-w-[720px]">
                  <thead>
                    <tr className="border-b border-border bg-surface text-left">
                      <th scope="col" className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-text-muted">Target</th>
                      <th scope="col" className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-text-muted">Status</th>
                      <th scope="col" className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-text-muted">Risk tier</th>
                      <th scope="col" className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-text-muted">Score</th>
                      <th scope="col" className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-text-muted">Findings</th>
                      <th scope="col" className="px-6 py-3.5 text-xs font-semibold uppercase tracking-wider text-text-muted">Date</th>
                      <th scope="col" className="px-6 py-3.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {scans.map((scan) => (
                      <tr key={scan.scan_id} className="transition-colors hover:bg-surface">
                        <td className="max-w-xs px-6 py-4">
                          <Link
                            href={`/scan/${scan.scan_id}`}
                            className="block truncate text-sm font-medium text-text-primary hover:text-primary focus-ring rounded"
                            title={scan.url || undefined}
                          >
                            {truncateUrl(scan.url || scan.metadata?.final_url, 45)}
                          </Link>
                          <p className="mt-0.5 truncate font-mono text-[11px] text-text-muted">
                            {scan.scan_id}
                          </p>
                        </td>
                        <td className="px-6 py-4">
                          <StatusBadge status={scan.status} size="sm" />
                        </td>
                        <td className="px-6 py-4">
                          {scan.risk_tier ? (
                            <SeverityBadge severity={scan.risk_tier} size="sm" />
                          ) : (
                            <span className="text-sm text-text-muted">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          {scan.risk_score !== null ? (
                            <span className="text-sm font-semibold tabular-nums text-text-primary">
                              {scan.risk_score}<span className="text-text-muted">/100</span>
                            </span>
                          ) : (
                            <span className="text-sm text-text-muted">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm tabular-nums text-text-secondary">
                          {scan.findings?.length ?? 0}
                        </td>
                        <td className="px-6 py-4 text-sm text-text-secondary">
                          {formatDate(scan.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              href={`/scan/${scan.scan_id}`}
                              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-elevated focus-ring"
                            >
                              Results
                            </Link>
                            {scan.status === 'completed' && (
                              <Link
                                href={`/report/${scan.scan_id}`}
                                className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-elevated focus-ring"
                              >
                                Report
                              </Link>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex flex-col gap-3 border-t border-border px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-text-secondary">
                  Showing{' '}
                  <span className="font-medium text-text-primary">
                    {total === 0 ? 0 : (filters.page - 1) * filters.limit + 1}–
                    {Math.min(filters.page * filters.limit, total)}
                  </span>{' '}
                  of <span className="font-medium text-text-primary">{total}</span> scans
                </p>
                {totalPages > 1 && (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setFilters((prev) => ({ ...prev, page: prev.page - 1 }))}
                      disabled={filters.page === 1}
                      className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-primary transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40 focus-ring"
                    >
                      <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                      Previous
                    </button>
                    <span className="px-2 text-sm text-text-secondary">
                      Page {filters.page} of {totalPages}
                    </span>
                    <button
                      type="button"
                      onClick={() => setFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
                      disabled={filters.page >= totalPages}
                      className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-primary transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40 focus-ring"
                    >
                      Next
                      <ChevronRight className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
