export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface ScanMetadata {
  status_code: number;
  content_type: string | null;
  response_time_ms: number;
  redirect_count: number;
  final_url: string;
  content_length: number;
}

export interface FindingEvidence {
  [key: string]: any;
}

export interface Finding {
  id: string;
  rule_id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  evidence: FindingEvidence;
  recommendation: string;
  source: string;
  confidence: number;
  created_at: string;
}

export interface ScanResponse {
  scan_id: string;
  status: string;
  metadata: ScanMetadata | null;
  findings: Finding[];
  risk_score: number | null;
  risk_tier: string | null;
  score_source: string | null;
  error: string | null;
  error_code: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ScanListResponse {
  scans: ScanResponse[];
  total: number;
  limit: number;
  offset: number;
}

export async function createScan(url: string): Promise<ScanResponse> {
  const response = await fetch(`${API_BASE}/scans`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function getScan(scanId: string): Promise<ScanResponse> {
  const response = await fetch(`${API_BASE}/scans/${scanId}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function listScans(limit = 50, offset = 0): Promise<ScanListResponse> {
  const response = await fetch(`${API_BASE}/scans?limit=${limit}&offset=${offset}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'bg-red-600 text-white';
    case 'high':
      return 'bg-red-500 text-white';
    case 'medium':
      return 'bg-yellow-500 text-white';
    case 'low':
      return 'bg-blue-500 text-white';
    case 'info':
      return 'bg-gray-500 text-white';
    default:
      return 'bg-gray-300 text-gray-800';
  }
}

export function getSeverityLabel(severity: string): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}
