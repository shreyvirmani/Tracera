export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface ScanMetadata {
  status_code: number;
  content_type: string | null;
  response_time_ms: number;
  redirect_count: number;
  final_url: string;
  content_length: number;
}

export interface FindingEvidence {
  [key: string]: unknown;
}

export type FindingSeverity =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'info'
  | string;

export type ScanStatus = 'pending' | 'completed' | 'failed' | string;

export interface Finding {
  id: string;
  rule_id: string;
  category: string;
  severity: FindingSeverity;
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
  status: ScanStatus;
  url: string | null;
  canonical_url: string | null;
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

export interface ScanListParams {
  limit?: number;
  offset?: number;
  status?: string;
  tier?: string;
  search?: string;
}

/** Error thrown for any failed API interaction. */
export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

const DEFAULT_TIMEOUT_MS = 60_000;

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(
        'The request timed out. The API may be slow or unreachable.',
        0,
        'TIMEOUT',
      );
    }
    throw new ApiError(
      'Could not reach the Tracera API. Check that the backend is running.',
      0,
      'NETWORK_ERROR',
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') {
        detail = body.detail;
      }
    } catch {
      // Malformed or empty error body: keep the generic message.
    }
    throw new ApiError(detail, response.status);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError('The API returned a malformed response.', response.status, 'MALFORMED_RESPONSE');
  }
}

export async function createScan(url: string): Promise<ScanResponse> {
  return request<ScanResponse>('/scans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
}

export async function getScan(scanId: string): Promise<ScanResponse> {
  return request<ScanResponse>(`/scans/${encodeURIComponent(scanId)}`);
}

export async function listScans(
  params: ScanListParams = {},
): Promise<ScanListResponse> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set('limit', String(params.limit));
  if (params.offset !== undefined) search.set('offset', String(params.offset));
  if (params.status) search.set('status', params.status);
  if (params.tier) search.set('tier', params.tier);
  if (params.search) search.set('search', params.search);
  const qs = search.toString();
  return request<ScanListResponse>(`/scans${qs ? `?${qs}` : ''}`);
}

/** Server-generated JSON export download URL for a scan. */
export function getScanExportUrl(scanId: string): string {
  return `${API_BASE}/scans/${encodeURIComponent(scanId)}/export`;
}

/** Client-side URL sanity check mirroring backend rules (scheme + shape). */
export function isValidScanUrl(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > 2048) return false;
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return false;
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false;
  if (!parsed.hostname) return false;
  return true;
}

export const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'] as const;

export type SeverityLevel = (typeof SEVERITY_ORDER)[number];

export function isSeverityLevel(value: string): value is SeverityLevel {
  return (SEVERITY_ORDER as readonly string[]).includes(value);
}

export function getSeverityLabel(severity: string): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}
