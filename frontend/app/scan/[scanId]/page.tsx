'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getScan } from '@/lib/api';
import { ScanResponse, Finding } from '@/lib/api';
import FindingsList from '@/components/FindingsList';

export default function ScanResultsPage() {
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
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <svg className="animate-spin mx-auto h-12 w-12 text-blue-600" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <p className="mt-4 text-gray-600">Loading scan results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <h2 className="mt-4 text-xl font-semibold text-gray-900">Failed to load scan</h2>
        <p className="mt-2 text-gray-600">{error}</p>
      </div>
    );
  }

  if (!scan) {
    return null;
  }

  const getTierColor = (tier: string | null) => {
    switch (tier?.toLowerCase()) {
      case 'critical':
        return 'bg-red-600 text-white';
      case 'high':
        return 'bg-red-500 text-white';
      case 'medium':
        return 'bg-yellow-500 text-white';
      case 'low':
        return 'bg-green-500 text-white';
      default:
        return 'bg-gray-300 text-gray-800';
    }
  };

  return (
    <div className="space-y-8">
      {/* Scan Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Scan Results</h1>
            <p className="mt-1 text-gray-600">Scan ID: {scan.scan_id}</p>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <span
              className={`px-4 py-2 rounded-full text-sm font-medium ${getTierColor(scan.risk_tier)}`}
            >
              {scan.risk_tier?.toUpperCase() || 'UNKNOWN'}
            </span>
            {scan.risk_score !== null && (
              <span className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                Risk Score: {scan.risk_score}/100
              </span>
            )}
            <span
              className={`px-4 py-2 rounded-full text-sm font-medium ${scan.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
            >
              {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
            </span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Target URL" value={scan.metadata?.final_url || 'N/A'} />
          <StatCard label="Status Code" value={scan.metadata?.status_code?.toString() || 'N/A'} />
          <StatCard
            label="Response Time"
            value={`${scan.metadata?.response_time_ms?.toFixed(0) || 0} ms`}
          />
          <StatCard label="Content Length" value={`${scan.metadata?.content_length || 0} bytes`} />
        </div>
      </div>

      {/* Findings */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <FindingsList findings={scan.findings || []} />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-medium text-gray-900 break-all">{value}</p>
    </div>
  );
}
