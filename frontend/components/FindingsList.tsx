'use client';

import { useState } from 'react';
import { Finding } from '@/lib/api';
import { getSeverityColor, getSeverityLabel } from '@/lib/api';

interface FindingsListProps {
  findings: Finding[];
}

export default function FindingsList({ findings }: FindingsListProps) {
  if (findings.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-green-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h3 className="mt-2 text-lg font-medium text-gray-900">No findings</h3>
        <p className="mt-1 text-sm text-gray-500">This scan didn't detect any issues.</p>
      </div>
    );
  }

  const sortedFindings = [...findings].sort((a, b) => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    return (
      (severityOrder[a.severity as keyof typeof severityOrder] ?? 5) -
      (severityOrder[b.severity as keyof typeof severityOrder] ?? 5)
    );
  });

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">Findings ({findings.length})</h2>
      <div className="space-y-3">
        {sortedFindings.map((finding) => (
          <FindingCard key={finding.id} finding={finding} />
        ))}
      </div>
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start gap-4 hover:bg-gray-50 transition-colors text-left"
      >
        <div
          className={`flex-shrink-0 px-3 py-1 text-xs font-medium rounded-full ${getSeverityColor(finding.severity)}`}
        >
          {getSeverityLabel(finding.severity)}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-medium text-gray-900">{finding.title}</h3>
          <p className="mt-1 text-sm text-gray-600 line-clamp-2">{finding.description}</p>
          <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
            <span>Rule: {finding.rule_id}</span>
            <span>Category: {finding.category}</span>
            <span>Source: {finding.source}</span>
          </div>
        </div>
        <svg
          className={`flex-shrink-0 h-5 w-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-gray-200 bg-gray-50 p-4">
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Recommendation</h4>
              <p className="text-sm text-gray-700">{finding.recommendation}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Evidence</h4>
              <pre className="text-xs text-gray-600 bg-white p-3 rounded overflow-x-auto max-h-48">
                {JSON.stringify(finding.evidence, null, 2)}
              </pre>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Confidence: </span>
                <span className="font-medium">{finding.confidence}%</span>
              </div>
              <div>
                <span className="text-gray-500">Detected: </span>
                <span className="font-medium">{new Date(finding.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
