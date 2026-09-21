'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getScan, ScanResponse } from '@/lib/api';
import { Finding } from '@/lib/api';
import { RiskScoreCard } from '@/components/ui/RiskScoreCard';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { Skeleton, SkeletonCard, SkeletonSeveritySection } from '@/components/ui/Skeleton';

const severityOrder = ['critical', 'high', 'medium', 'low', 'info'] as const;

function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'bg-red-500 text-white';
    case 'high':
      return 'bg-red-600 text-white';
    case 'medium':
      return 'bg-yellow-500 text-white';
    case 'low':
      return 'bg-green-500 text-white';
    case 'info':
      return 'bg-gray-500 text-white';
    default:
      return 'bg-gray-500 text-white';
  }
}

function FindingCard({ finding, expanded = false, onToggle }: { finding: Finding; expanded?: boolean; onToggle?: () => void }) {
  return (
    <details className="group" open={expanded}>
      <summary
        className="w-full p-4 hover:bg-gray-50 transition-colors text-left flex items-start gap-4 cursor-pointer list-none"
        onClick={onToggle}
      >
        <SeverityBadge severity={finding.severity} size="md" />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900">{finding.title}</h4>
          <p className="mt-1 text-sm text-gray-600 line-clamp-2">{finding.description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
            <span>Rule: <code className="bg-gray-100 px-1.5 py-0.5 rounded">{finding.rule_id}</code></span>
            <span>Category: {finding.category}</span>
            <span>Source: {finding.source}</span>
            <span>Confidence: {finding.confidence}%</span>
          </div>
        </div>
        <svg
          className="flex-shrink-0 w-5 h-5 text-gray-400 transition-transform duration-200 group-open:rotate-180"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </summary>
      <div className="px-4 pb-4 border-t border-gray-100 mt-2 animate-in fade-in-50 slide-in-from-top-2">
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Description</p>
            <p className="mt-1 text-sm text-gray-700">{finding.description}</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Rule ID</p>
              <p className="mt-1 font-mono text-gray-900">{finding.rule_id}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Category</p>
              <p className="mt-1 text-gray-900">{finding.category}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Source</p>
              <p className="mt-1 text-gray-900">{finding.source}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Confidence</p>
              <p className="mt-1 text-gray-900">{finding.confidence}%</p>
            </div>
          </div>
          {finding.evidence && Object.keys(finding.evidence).length > 0 && (
            <details className="group">
              <summary className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 cursor-pointer">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>View Evidence</span>
                <svg className="ml-auto w-4 h-4 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <pre className="mt-3 p-3 bg-gray-900 rounded text-xs text-green-300 overflow-x-auto max-h-64">
                {JSON.stringify(finding.evidence, null, 2)}
              </pre>
            </details>
          )}
          <div className="pt-2 border-t border-gray-200">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Recommendation</p>
            <p className="mt-1 text-sm text-gray-700">{finding.recommendation}</p>
          </div>
        </div>
      </div>
    </details>
  );
}

function ScanReportPageContent({ scan }: { scan: ScanResponse }) {
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set());

  // Group findings by severity
  const findingsBySeverity = (scan.findings || []).reduce((acc: Record<string, Finding[]>, finding: Finding) => {
    const severity = finding.severity.toLowerCase();
    if (!acc[severity]) acc[severity] = [];
    acc[severity].push(finding);
    return acc;
  }, {} as Record<string, Finding[]>);

  const severityCounts = severityOrder.reduce((acc, sev) => {
    acc[sev] = findingsBySeverity[sev]?.length || 0;
    return acc;
  }, {} as Record<string, number>);

const totalFindings = scan.findings?.length || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between h-16">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">Tracera</h1>
              <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded">Report</span>
            </div>
            <div className="mt-4 sm:mt-0 flex items-center gap-4">
              <span className="text-sm text-gray-500">Scan ID: {scan.scan_id.slice(0, 8)}...</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Severity Overview Cards */}
        <div className="mb-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {severityOrder.map((severity) => {
            const count = severityCounts[severity];
            if (count === 0 && severity !== 'info') return null;
            return (
              <div
                key={severity}
                className={`rounded-xl p-4 text-center transition-all hover:shadow-md ${
                  count > 0 ? getSeverityColor(severity) : 'bg-gray-50 border border-gray-200'
                }`}
              >
                <p className={`text-2xl font-bold ${count > 0 ? 'text-white' : 'text-gray-400'}`}>
                  {count}
                </p>
                <p className={`text-sm font-medium mt-1 ${count > 0 ? 'text-white/90' : 'text-gray-500'}`}>
                  {severity.charAt(0).toUpperCase() + severity.slice(1)}
                </p>
              </div>
            );
          })}
        </div>

        {/* Risk Score Card - Sticky on scroll */}
        <div className="mb-8 sticky top-20 z-10">
          <RiskScoreCard
            score={scan.risk_score}
            tier={scan.risk_tier}
            scoreSource={scan.score_source}
            showDetails={true}
          />
        </div>

        {/* Scan Metadata */}
        {scan.metadata && (
          <div className="mb-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Scan Details</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Target URL</p>
                <p className="mt-1 text-lg font-medium text-gray-900 break-all">
                  {scan.metadata.final_url}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Status Code</p>
                <p className="mt-1 text-lg font-medium text-gray-900">
                  {scan.metadata.status_code}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Response Time</p>
                <p className="mt-1 text-lg font-medium text-gray-900">
                  {scan.metadata.response_time_ms.toFixed(0)} ms
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500">Content Length</p>
                <p className="mt-1 text-lg font-medium text-gray-900">
                  {scan.metadata.content_length.toLocaleString()} bytes
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Findings by Severity */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Findings ({totalFindings})
            </h2>
            {totalFindings > 0 && (
              <button
                onClick={() => setExpandedFindings(
                  new Set(scan.findings?.map(f => f.id) || [])
                )}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Expand All
              </button>
            )}
          </div>

          {totalFindings > 0 ? (
            <div className="space-y-6">
              {severityOrder
                .filter((severity) => findingsBySeverity[severity]?.length > 0)
                .map((severity) => {
                  const findings = findingsBySeverity[severity];
                  return (
                    <div key={severity} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                      <div
                        className={`px-6 py-4 border-b border-gray-200 ${getSeverityColor(severity)}`}
                      >
                        <div className="flex items-center justify-between">
                          <h3 className="text-lg font-semibold">
                            {severity.charAt(0).toUpperCase() + severity.slice(1)} ({findings.length})
                          </h3>
                        </div>
                      </div>
                      <div className="divide-y divide-gray-100">
                        {findings.map((finding: Finding) => {
                          const isExpanded = expandedFindings.has(finding.id);
                          return (
                            <FindingCard
                              key={finding.id}
                              finding={finding}
                              expanded={isExpanded}
                              onToggle={() => {
                                setExpandedFindings(prev => {
                                  const next = new Set(prev);
                                  if (next.has(finding.id)) next.delete(finding.id);
                                  else next.add(finding.id);
                                  return next;
                                });
                              }}
                            />
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <EmptyState title="No findings" description="This scan didn't detect any issues." />
          )}
        </div>

        {/* Recommendations */}
        {totalFindings > 0 && (
          <div className="mb-8 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h2 className="text-xl font-semibold text-gray-900">Recommendations</h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {Array.from(
                  new Set<string>(
                    (scan.findings || [])
                      .sort((a: Finding, b: Finding) => {
                        const severityOrderMap = { critical: 0, high: 1, medium: 2, low: 3, info: 4 } as Record<string, number>;
                        return (severityOrderMap[a.severity.toLowerCase()] ?? 99) -
                               (severityOrderMap[b.severity.toLowerCase()] ?? 99);
                      })
                      .map((f: Finding) => f.recommendation)
                  )
                ).map((recommendation, idx) => (
                  <div key={idx} className="flex gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">
                      {idx + 1}
                    </span>
                    <p className="text-gray-700 mt-0.5">{recommendation}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ScanReportPage() {
  const params = useParams();
  const scanId = params.scanId as string;

  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchScan = async () => {
      try {
        const data = await getScan(scanId);
        setScan(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load scan');
      } finally {
        setLoading(false);
      }
    };

    fetchScan();
  }, [scanId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between h-16">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-900">Tracera</h1>
                <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded">Report</span>
              </div>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <SkeletonCard />
          <SkeletonCard className="mt-8" />
          <div className="mt-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton variant="rectangular" key={i} height="80" className="rounded-xl p-4" />
            ))}
          </div>
          <div className="mt-8 space-y-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <SkeletonSeveritySection key={i} />
            ))}
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <ErrorState
          message="Failed to load scan report"
          onRetry={() => window.location.reload()}
          fullScreen
        />
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <EmptyState title="Scan not found" description="The requested scan could not be found." size="lg" />
      </div>
    );
  }

  return <ScanReportPageContent scan={scan} />;
}