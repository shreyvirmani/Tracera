'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

import type { ScanListResponse, ScanResponse } from '@/lib/api';

import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Skeleton } from '@/components/ui/Skeleton';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000/api/v1';

const STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-100 text-green-700',
  running: 'bg-blue-100 text-blue-700',
  pending: 'bg-yellow-100 text-yellow-700',
  failed: 'bg-red-100 text-red-700',
};

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentScans, setRecentScans] = useState<ScanResponse[]>([]);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const response = await fetch(
          `${API_URL}/scans?limit=5&offset=0`
        );

        if (!response.ok) {
          throw new Error('Failed to load dashboard');
        }

        const data: ScanListResponse = await response.json();

        setRecentScans(data.scans);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load dashboard'
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const stats = useMemo(() => {
    const totalScans = recentScans.length;

    const totalFindings = recentScans.reduce(
      (sum, scan) => sum + (scan.findings?.length ?? 0),
      0
    );

    const criticalFindings = recentScans.reduce(
      (sum, scan) =>
        sum +
        (scan.findings?.filter(
          (f) => f.severity === 'critical'
        ).length ?? 0),
      0
    );

    const highFindings = recentScans.reduce(
      (sum, scan) =>
        sum +
        (scan.findings?.filter(
          (f) => f.severity === 'high'
        ).length ?? 0),
      0
    );

    const avgRiskScore =
      totalScans === 0
        ? 0
        : Math.round(
            recentScans.reduce(
              (sum, scan) => sum + (scan.risk_score ?? 0),
              0
            ) / totalScans
          );

    return {
      totalScans,
      totalFindings,
      criticalFindings,
      highFindings,
      avgRiskScore,
    };
  }, [recentScans]);

  function formatDate(date: string) {
    return new Date(date).toLocaleString();
  }

  function truncate(url: string, length = 45) {
    if (!url) return '-';

    if (url.length <= length) return url;

    return url.slice(0, length) + '...';
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <Skeleton className="h-12 w-64 rounded-lg" />

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton
                key={i}
                className="h-36 rounded-xl"
              />
            ))}
          </div>

          <Skeleton className="h-96 rounded-xl" />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold">
            Dashboard Error
          </h1>

          <p className="text-gray-500 mt-3">
            {error}
          </p>

          <button
            onClick={() => window.location.reload()}
            className="mt-6 rounded-lg bg-blue-600 px-5 py-2 text-white"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-10">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">
              Tracera Dashboard
            </h1>

            <p className="mt-2 text-gray-600">
              Monitor your recent security scans and risk posture.
            </p>
          </div>

          <Link
            href="/scan"
            className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 transition"
          >
            + New Scan
          </Link>
        </div>

        {/* Stats */}

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">

          <div className="bg-white rounded-xl border shadow-sm p-6">
            <p className="text-gray-500 text-sm">
              Total Scans
            </p>

            <h2 className="mt-3 text-4xl font-bold">
              {stats.totalScans}
            </h2>
          </div>

          <div className="bg-white rounded-xl border shadow-sm p-6">
            <p className="text-gray-500 text-sm">
              Total Findings
            </p>

            <h2 className="mt-3 text-4xl font-bold text-amber-600">
              {stats.totalFindings}
            </h2>
          </div>

          <div className="bg-white rounded-xl border shadow-sm p-6">
            <p className="text-gray-500 text-sm">
              Critical Findings
            </p>

            <h2 className="mt-3 text-4xl font-bold text-red-600">
              {stats.criticalFindings}
            </h2>
          </div>

          <div className="bg-white rounded-xl border shadow-sm p-6">
            <p className="text-gray-500 text-sm">
              Average Risk Score
            </p>

            <h2 className="mt-3 text-4xl font-bold text-blue-600">
              {stats.avgRiskScore}
            </h2>
          </div>

        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* Left Sidebar */}

          <div className="space-y-8">

            <div className="bg-white rounded-xl border shadow-sm p-6">

              <h2 className="text-xl font-semibold mb-5">
                Quick Actions
              </h2>

              <div className="space-y-3">

                <Link
                  href="/scan"
                  className="block rounded-lg border p-4 hover:bg-blue-50 transition"
                >
                  <h3 className="font-semibold">
                    Start New Scan
                  </h3>

                  <p className="text-sm text-gray-500 mt-1">
                    Submit a website for analysis.
                  </p>
                </Link>

                <Link
                  href="/history"
                  className="block rounded-lg border p-4 hover:bg-green-50 transition"
                >
                  <h3 className="font-semibold">
                    Scan History
                  </h3>

                  <p className="text-sm text-gray-500 mt-1">
                    Browse previous scans.
                  </p>
                </Link>

              </div>

            </div>

            <div className="bg-white rounded-xl border shadow-sm p-6">

              <h2 className="text-xl font-semibold mb-6">
                Risk Distribution
              </h2>

              {[
                {
                  label: 'Critical',
                  count: stats.criticalFindings,
                  color: 'bg-red-500'
                },
                {
                  label: 'High',
                  count: stats.highFindings,
                  color: 'bg-orange-500'
                },
                {
                  label: 'Others',
                  count:
                    stats.totalFindings -
                    stats.criticalFindings -
                    stats.highFindings,
                  color: 'bg-green-500'
                }
              ].map((item) => {

                const percent =
                  stats.totalFindings === 0
                    ? 0
                    : (item.count / stats.totalFindings) * 100;

                return (

                  <div
                    key={item.label}
                    className="mb-5"
                  >

                    <div className="flex justify-between text-sm mb-2">
                      <span>{item.label}</span>

                      <span>{item.count}</span>
                    </div>

                    <div className="h-3 rounded-full bg-gray-200 overflow-hidden">

                      <div
                        className={`${item.color} h-full transition-all duration-700`}
                        style={{
                          width: `${percent}%`
                        }}
                      />

                    </div>

                  </div>

                );

              })}

            </div>

          </div>

          {/* Right Side */}

          <div className="lg:col-span-2">

            <div className="bg-white rounded-xl border shadow-sm overflow-hidden">

              <div className="flex items-center justify-between px-6 py-5 border-b">

                <h2 className="text-xl font-semibold">
                  Recent Scans
                </h2>

                <Link
                  href="/history"
                  className="text-blue-600 hover:underline"
                >
                  View All
                </Link>

              </div>

                            {recentScans.length === 0 ? (
                <div className="p-12 text-center">
                  <h3 className="text-xl font-semibold text-gray-900">
                    No scans yet
                  </h3>

                  <p className="mt-2 text-gray-500">
                    Start your first scan to populate the dashboard.
                  </p>

                  <Link
                    href="/scan"
                    className="inline-flex mt-6 rounded-lg bg-blue-600 px-5 py-3 text-white font-medium hover:bg-blue-700 transition"
                  >
                    Start Scan
                  </Link>
                </div>
              ) : (
                <div className="overflow-x-auto">

                  <table className="min-w-full divide-y divide-gray-200">

                    <thead className="bg-gray-50">

                      <tr>

                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                          Target
                        </th>

                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                          Status
                        </th>

                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                          Risk
                        </th>

                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                          Score
                        </th>

                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                          Findings
                        </th>

                        <th className="px-6 py-3 text-left text-xs font-semibold uppercase text-gray-500">
                          Date
                        </th>

                        <th className="px-6 py-3 text-right text-xs font-semibold uppercase text-gray-500">
                          Actions
                        </th>

                      </tr>

                    </thead>

                    <tbody className="divide-y divide-gray-100">

                      {recentScans.map((scan) => (

                        <tr
                          key={scan.scan_id}
                          className="hover:bg-gray-50 transition"
                        >

                          <td className="px-6 py-4">
                            <div
                              className="max-w-xs truncate font-medium text-gray-900"
                              title={scan.metadata?.final_url}
                            >
                              {truncate(scan.metadata?.final_url ?? "-")}
                            </div>
                          </td>

                          <td className="px-6 py-4">
                            <span
                              className={`rounded-full px-3 py-1 text-xs font-medium ${
                                STATUS_COLORS[scan.status] ??
                                "bg-gray-100 text-gray-700"
                              }`}
                            >
                              {scan.status}
                            </span>
                          </td>

                          <td className="px-6 py-4">
                            <SeverityBadge
                              severity={scan.risk_tier ?? "info"}
                              size="sm"
                            />
                          </td>

                          <td className="px-6 py-4 font-semibold">
                            {scan.risk_score ?? "--"}
                          </td>

                          <td className="px-6 py-4">
                            {scan.findings?.length ?? 0}
                          </td>

                          <td className="px-6 py-4 text-gray-500">
                            {formatDate(scan.created_at)}
                          </td>

                          <td className="px-6 py-4">

                            <div className="flex justify-end gap-2">

                              <Link
                                href={`/scan/${scan.scan_id}`}
                                className="rounded-lg border px-3 py-2 text-sm hover:bg-gray-100 transition"
                              >
                                View
                              </Link>

                              <Link
                                href={`/report/${scan.scan_id}`}
                                className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 transition"
                              >
                                Report
                              </Link>

                            </div>

                          </td>

                        </tr>

                      ))}

                    </tbody>

                  </table>

                </div>
              )}

            </div>

          </div>

        </div>

      </div>

    </main>
  );
}