'use client';

import { useEffect, useState } from 'react';
import { getScan } from '@/lib/api';
import { ScanDetail, Finding } from '@/lib/types';
import { FindingsList } from '@/components/FindingsList';

interface ScanResultsProps {
  scanId: string;
  onNewScan: () => void;
}

export function ScanResults({ scanId, onNewScan }: ScanResultsProps) {
  const [scan, setScan] = useState<ScanDetail | null>(null);
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
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-gray-600">Analyzing scan results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={onNewScan} className="text-blue-600 hover:underline">Start new scan</button>
      </div>
    );
  }

  if (!scan) return null;

  const tierColors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-800',
    MEDIUM: 'bg-yellow-100 text-yellow-800',
    HIGH: 'bg-orange-100 text-orange-800',
    CRITICAL: 'bg-red-100 text-red-800',
  };

  const tierColor = tierColors[scan.risk_tier || 'LOW'] || tierColors.LOW;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Scan Results</h2>
            <p className="text-gray-500 text-sm mt-1">{scan.canonical_url}</p>
          </div>
          <button onClick={onNewScan} className="text-blue-600 hover:underline text-sm">
            ← New Scan
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className={`inline-flex items-center px-4 py-2 rounded-lg ${tierColor} font-semibold`}>
            {scan.risk_tier || 'UNKNOWN'}
          </div>
          <div className="bg-gray-100 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-gray-900">{scan.risk_score ?? 0}</p>
            <p className="text-sm text-gray-500">Risk Score</p>
          </div>
          <div className="bg-gray-100 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-gray-900">{scan.findings.length}</p>
            <p className="text-sm text-gray-500">Findings</p>
          </div>
          <div className="bg-gray-100 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-gray-900">{scan.score_source?.replace('_', ' ') || '—'}</p>
            <p className="text-sm text-gray-500">Score Source</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Findings</h3>
        <FindingsList findings={scan.findings} />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Scan Metadata</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500">Feature Schema</dt>
            <dd className="font-mono">{scan.feature_schema_version}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Scan Time</dt>
            <dd>{new Date(scan.created_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Completed</dt>
            <dd>{scan.completed_at ? new Date(scan.completed_at).toLocaleString() : '—'}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Status</dt>
            <dd className="capitalize">{scan.status}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}