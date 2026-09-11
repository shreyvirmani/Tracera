'use client';

import { useState } from 'react';
import { ScanDetail } from '@/lib/types';
import { FindingsList } from '@/components/FindingsList';
import Link from 'next/link';

interface ScanResultsClientProps {
  initialScan: ScanDetail;
}

export function ScanResultsClient({ initialScan }: ScanResultsClientProps) {
  const [scan, setScan] = useState<ScanDetail>(initialScan);

  const tierColors: Record<string, string> = {
    LOW: 'bg-green-100 text-green-800',
    MEDIUM: 'bg-yellow-100 text-yellow-800',
    HIGH: 'bg-orange-100 text-orange-800',
    CRITICAL: 'bg-red-100 text-red-800',
  };

  const tierColor = tierColors[scan.risk_tier || 'LOW'] || tierColors.LOW;

  return (
    <main className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Scan Results</h1>
            <p className="text-gray-500 mt-1">{scan.canonical_url}</p>
          </div>
          <Link href="/" className="text-blue-600 hover:underline">
            ← New Scan
          </Link>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
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
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Findings</h2>
          <FindingsList findings={scan.findings} />
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Scan Metadata</h2>
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
            <div>
              <dt className="text-gray-500">Score Source</dt>
              <dd>{scan.score_source?.replace('_', ' ') || '—'}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Error</dt>
              <dd className="text-red-600">{scan.error_message || 'None'}</dd>
            </div>
          </dl>
        </div>
      </div>
    </main>
  );
}