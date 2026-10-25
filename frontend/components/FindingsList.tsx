'use client';

import { useMemo, useState } from 'react';
import {
  ChevronDown,
  Code2,
  Lightbulb,
  ShieldQuestion,
} from 'lucide-react';
import {
  Finding,
  SEVERITY_ORDER,
  SeverityLevel,
  isSeverityLevel,
} from '@/lib/api';
import { SeverityBadge } from '@/components/ui/SeverityBadge';

const SOURCE_LABELS: Record<string, { label: string; description: string }> = {
  rule_engine: {
    label: 'Rule-based finding',
    description:
      'Produced by a deterministic check against the observed response.',
  },
  ml_model: {
    label: 'ML model output',
    description: 'Statistical output from a trained model. Not a deterministic rule.',
  },
  cve_correlator: {
    label: 'CVE correlation',
    description: 'Correlated against known vulnerability data.',
  },
};

function SourceTag({ source }: { source: string }) {
  const config = SOURCE_LABELS[source] ?? {
    label: source,
    description: 'Detection source reported by the analysis engine.',
  };
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-0.5 text-[11px] text-text-secondary"
      title={config.description}
    >
      <ShieldQuestion className="h-3 w-3 text-text-muted" aria-hidden="true" />
      {config.label}
    </span>
  );
}

function EvidencePanel({ evidence }: { evidence: Finding['evidence'] }) {
  const entries = Object.entries(evidence ?? {});
  if (entries.length === 0) return null;

  return (
    <div>
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
        <Code2 className="h-3.5 w-3.5" aria-hidden="true" />
        Evidence
      </p>
      <pre className="scrollbar-thin max-h-64 overflow-auto rounded-lg border border-border bg-background p-3 text-xs leading-relaxed text-text-secondary">
        {JSON.stringify(evidence, null, 2)}
      </pre>
    </div>
  );
}

export function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false);
  const hasEvidence = finding.evidence && Object.keys(finding.evidence).length > 0;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <button
        type="button"
        onClick={() => setExpanded((open) => !open)}
        aria-expanded={expanded}
        className="flex w-full items-start gap-4 p-4 text-left transition-colors hover:bg-surface focus-ring-inset"
      >
        <SeverityBadge severity={finding.severity} size="md" />
        <div className="min-w-0 flex-1">
          <h4 className="font-medium text-text-primary">{finding.title}</h4>
          <p className="mt-1 line-clamp-2 text-sm text-text-secondary">
            {finding.description}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-muted">
            <span>
              Rule <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-text-secondary">{finding.rule_id}</code>
            </span>
            <span className="capitalize">{finding.category}</span>
            <span>Confidence {Math.round(finding.confidence * 100)}%</span>
          </div>
        </div>
        <ChevronDown
          aria-hidden="true"
          className={`mt-1 h-4 w-4 flex-shrink-0 text-text-muted transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {expanded && (
        <div className="animate-fade-up space-y-4 border-t border-border bg-surface p-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-text-muted">
              What was observed
            </p>
            <p className="text-sm leading-relaxed text-text-secondary">
              {finding.description}
            </p>
          </div>

          {hasEvidence && <EvidencePanel evidence={finding.evidence} />}

          <div>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
              <Lightbulb className="h-3.5 w-3.5" aria-hidden="true" />
              Recommended remediation
            </p>
            <p className="text-sm leading-relaxed text-text-secondary">
              {finding.recommendation}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
            <SourceTag source={finding.source} />
            <span className="text-[11px] text-text-muted">
              Detected {new Date(finding.created_at).toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export interface SeverityGroup {
  severity: SeverityLevel;
  findings: Finding[];
}

export function groupFindingsBySeverity(findings: Finding[]): SeverityGroup[] {
  const groups = new Map<SeverityLevel, Finding[]>();
  for (const finding of findings) {
    const lower = finding.severity.toLowerCase();
    const key: SeverityLevel = isSeverityLevel(lower) ? lower : 'info';
    const list = groups.get(key) ?? [];
    list.push(finding);
    groups.set(key, list);
  }
  return SEVERITY_ORDER.filter((s) => groups.has(s)).map((severity) => ({
    severity,
    findings: groups.get(severity)!,
  }));
}

interface FindingsListProps {
  findings: Finding[];
  title?: string;
}

export default function FindingsList({ findings, title }: FindingsListProps) {
  const [filter, setFilter] = useState<'all' | SeverityLevel>('all');

  const groups = useMemo(() => groupFindingsBySeverity(findings), [findings]);
  const availableSeverities = groups.map((g) => g.severity);

  const visibleGroups = useMemo(() => {
    if (filter === 'all') return groups;
    return groups.filter((g) => g.severity === filter);
  }, [groups, filter]);

  if (findings.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-10 text-center">
        <h3 className="text-lg font-semibold text-text-primary">
          No findings recorded
        </h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-text-secondary">
          The checks that ran did not identify any issues on this target. This
          reflects only the rules that executed during the scan — it is not a
          guarantee that the site is secure.
        </p>
      </div>
    );
  }

  return (
    <section aria-label="Findings">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold text-text-primary">
          {title || 'Findings'}{' '}
          <span className="ml-1 text-base font-medium text-text-muted">
            ({findings.length})
          </span>
        </h2>
        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter findings by severity">
          <button
            type="button"
            onClick={() => setFilter('all')}
            aria-pressed={filter === 'all'}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-ring ${
              filter === 'all'
                ? 'border-primary/40 bg-primary/10 text-primary'
                : 'border-border bg-surface text-text-secondary hover:text-text-primary'
            }`}
          >
            All ({findings.length})
          </button>
          {availableSeverities.map((severity) => {
            const count = groups.find((g) => g.severity === severity)?.findings.length ?? 0;
            return (
              <button
                key={severity}
                type="button"
                onClick={() => setFilter(severity)}
                aria-pressed={filter === severity}
                className={`rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors focus-ring ${
                  filter === severity
                    ? 'border-primary/40 bg-primary/10 text-primary'
                    : 'border-border bg-surface text-text-secondary hover:text-text-primary'
                }`}
              >
                {severity} ({count})
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-6">
        {visibleGroups.map((group) => (
          <div key={group.severity}>
            <div className="mb-2 flex items-center gap-2">
              <SeverityBadge severity={group.severity} size="sm" showDot={false} />
              <span className="text-xs font-medium text-text-muted">
                {group.findings.length}{' '}
                {group.findings.length === 1 ? 'finding' : 'findings'}
              </span>
            </div>
            <div className="space-y-3">
              {group.findings.map((finding) => (
                <FindingCard key={finding.id} finding={finding} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
