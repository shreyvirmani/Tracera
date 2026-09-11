export interface Finding {
  id: string;
  rule_id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  recommendation: string;
  source: string;
  confidence: number;
}

export interface ScanSummary {
  total: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  by_category: Record<string, number>;
}

export interface ScanDetail {
  id: string;
  url: string;
  canonical_url: string;
  status: string;
  feature_schema_version: string;
  risk_score: number | null;
  risk_tier: string | null;
  score_source: string | null;
  created_at: string;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  findings: Finding[];
}

export interface Report {
  scan_id: string;
  url: string;
  canonical_url: string;
  risk_score: number | null;
  risk_tier: string | null;
  score_source: string | null;
  feature_schema_version: string;
  scan_time: string;
  completed_time: string | null;
  finding_summary: ScanSummary;
  findings: Array<{
    rule_id: string;
    category: string;
    severity: string;
    title: string;
    description: string;
    evidence: Record<string, unknown>;
    recommendation: string;
    source: string;
  }>;
}