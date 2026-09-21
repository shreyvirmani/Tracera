'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ScanResponse, ScanListResponse } from '@/lib/api';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';

const STATUS_COLORS = {
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  running: 'bg-blue-100 text-blue-800',
  pending: 'bg-yellow-100 text-yellow-800',
};

export default function DashboardPage() {
  const [recentScans, setRecentScans] = useState<ScanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalScans: 0,
    totalFindings: 0,
    criticalFindings: 0,
    highFindings: 0,
    avgRiskScore: 0,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/scans?limit=5&offset=0`
        );
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data: ScanListResponse = await response.json();
        setRecentScans(data.scans);
        setStats({
          totalScans: data.total,
          totalFindings: data.scans.reduce((sum, s) => sum + (s.findings?.length || 0), 0),
          criticalFindings: data.scans.reduce(
            (sum, s) => sum + (s.findings?.filter(f => f.severity === 'critical').length || 0),
            0
          ),
          highFindings: data.scans.reduce(
            (sum, s) => sum + (s.findings?.filter(f => f.severity === 'high').length || 0),
            0
          ),
          avgRiskScore:
            data.scans.length > 0
              ? Math.round(
                  data.scans.reduce((sum, s) => sum + (s.risk_score || 0), 0) / data.scans.length
                )
              : 0,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const truncateUrl = (url: string, maxLength = 40) => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
  };

  const statCards = [
    {
      label: 'Total Scans',
      value: stats.totalScans,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
      ),
      color: 'bg-blue-100 text-blue-600',
      link: '/history',
    },
    {
      label: 'Total Findings',
      value: stats.totalFindings,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      color: 'bg-amber-100 text-amber-600',
      link: '/history',
    },
    {
      label: 'Critical Issues',
      value: stats.criticalFindings,
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      color: 'bg-red-100 text-red-600',
      link: '/history',
    },
    {
      label: 'Avg Risk Score',
      value: stats.avgRiskScore,
      suffix: '/100',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      color: 'bg-purple-100 text-purple-600',
      link: '/history',
    },
  ];

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="mt-2 text-gray-600">Overview of your security scanning activity</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">Recent Scans</h2>
              <Link href="/history" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                View All
              </Link>
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} variant="rectangular" height="60" className="mt-4 rounded-lg" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h2 className="mt-4 text-xl font-semibold text-gray-900">Failed to load dashboard</h2>
          <p className="mt-2 text-gray-600">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="mt-2 text-gray-600">Overview of your security scanning activity</p>
          </div>
          <Link
            href="/scan"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Scan
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((card) => (
            <Link key={card.label} href={card.link} className="block">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">{card.label}</p>
                    <p className="mt-2 text-3xl font-bold text-gray-900">
                      {card.value}
                      {card.suffix && <span className="text-lg font-normal text-gray-500">{card.suffix}</span>}
                    </p>
                  </div>
                  <div className={`p-3 rounded-lg ${card.color}`}>{card.icon}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Quick Actions & Recent Scans */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Quick Actions */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Quick Actions</h2>
              <div className="space-y-3">
                <Link
                  href="/scan"
                  className="block p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Start New Scan</p>
                      <p className="text-sm text-gray-500">Submit a URL for security analysis</p>
                    </div>
                  </div>
                </Link>
                <Link
                  href="/history"
                  className="block p-4 border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-green-100 text-green-600 rounded-lg">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">View Scan History</p>
                      <p className="text-sm text-gray-500">Browse all previous scans</p>
                    </div>
                  </div>
                </Link>
                <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 text-gray-500 rounded-lg">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">API Documentation</p>
                      <p className="text-sm text-gray-500">Integrate Tracera into your workflow</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Risk Distribution */}
            <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Risk Distribution</h2>
              <div className="space-y-4">
                {[
                  { label: 'Critical', count: stats.criticalFindings, color: 'bg-red-500' },
                  { label: 'High', count: stats.highFindings, color: 'bg-orange-500' },
                  { label: 'Medium', count: stats.totalFindings - stats.criticalFindings - stats.highFindings, color: 'bg-yellow-500' },
                  { label: 'Low / Info', count: Math.max(0, stats.totalFindings - stats.criticalFindings - stats.highFindings), color: 'bg-green-500' },
                ].map((tier) => (
                  <div key={tier.label} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: tier.color }}>
                      <span className="text-white text-xs font-bold">{tier.count}</span>
                    </div>
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          backgroundColor: tier.color,
                          width: stats.totalFindings > 0 ? `${(tier.count / stats.totalFindings) * 100}%` : '0%',
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700 w-16 text-right">
                      {tier.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Scans */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Recent Scans</h2>
                <Link href="/history" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                  View All
                </Link>
              </div>
              {recentScans.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Tier</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Findings</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {recentScans.map((scan) => (
                        <tr key={scan.scan_id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-6 py-4">
                            <p className="text-sm font-medium text-gray-900 truncate max-w-xs" title={scan.metadata?.final_url || ''}>
                              {truncateUrl(scan.metadata?.final_url || 'N/A')}
                            </p>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[scan.status as keyof typeof STATUS_COLORS] || 'bg-gray-100 text-gray-800'}`}>
                              {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <SeverityBadge severity={scan.risk_tier || 'info'} size="sm" />
                          </td>
                          <td className="px-6 py-4">
                            {scan.risk_score !== null ? (
                              <span className="text-sm font-medium text-gray-900">{scan.risk_score}/100</span>
                            ) : (
                              <span className="text-sm text-gray-400">N/A</span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-sm text-gray-700">{scan.findings?.length || 0}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-sm text-gray-500">{formatDate(scan.created_at)}</span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <Link
                                href={`/scan/${scan.scan_id}`}
                                className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                              >
                                View
                              </Link>
                              <Link
                                href={`/report/${scan.scan_id}`}
                                className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
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
              ) : (
                <div className="p-12 text-center">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <h3 className="mt-4 text-lg font-medium text-gray-900">No scans yet</h3>
                  <p className="mt-2 text-gray-500">Start your first security scan to see results here</p>
                  <Link
                    href="/scan"
                    className="mt-6 inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Start Scan
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}