'use client';

import { Finding } from '@/lib/types';

const severityColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
  info: 'bg-gray-100 text-gray-800 border-gray-200',
};

const categoryIcons: Record<string, string> = {
  security: '🔒',
  configuration: '⚙️',
  performance: '⚡',
  privacy: '🛡️',
};

export function FindingsList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="text-4xl mb-2">✅</div>
        <p className="text-gray-600">No findings detected. The site looks clean!</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {findings.map((finding) => (
        <FindingCard key={finding.id} finding={finding} />
      ))}
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const severityClass = severityColors[finding.severity] || severityColors.info;
  const categoryIcon = categoryIcons[finding.category] || '📋';

  return (
    <details className="border rounded-lg overflow-hidden">
      <summary className="flex items-center p-4 cursor-pointer bg-gray-50">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${severityClass}`}>
          {finding.severity.toUpperCase()}
        </span>
        <span className="ml-3 text-lg">{categoryIcon}</span>
        <h3 className="ml-3 font-medium text-gray-900 flex-1">{finding.title}</h3>
        <span className="text-xs text-gray-500">{finding.rule_id}</span>
      </summary>
      <div className="p-4 border-t bg-white">
        <p className="text-gray-600 mb-3">{finding.description}</p>
        
        <div className="mb-3">
          <h4 className="font-medium text-sm text-gray-700 mb-1">Evidence</h4>
          <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto">{JSON.stringify(finding.evidence, null, 2)}</pre>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h4 className="font-medium text-sm text-blue-800 mb-1">Recommendation</h4>
          <p className="text-blue-700 text-sm">{finding.recommendation}</p>
        </div>

        <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
          <span>Source: {finding.source}</span>
          <span>Confidence: {(finding.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    </details>
  );
}