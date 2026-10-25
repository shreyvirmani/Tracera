type TierStyle = { container: string; ring: string; label: string; description: string };
const TIER_STYLES: Record<string, TierStyle> = {
  low: {
    container: 'text-success',
    ring: 'stroke-success',
    label: 'Low risk',
    description:
      'Few or only minor issues were found by the checks that ran. This is not a guarantee of security — it reflects only what these rules observed.',
  },
  medium: {
    container: 'text-warning',
    ring: 'stroke-warning',
    label: 'Medium risk',
    description:
      'Several configuration or quality issues were found. Review the findings and address the higher-severity items first.',
  },
  high: {
    container: 'text-severity-high',
    ring: 'stroke-severity-high',
    label: 'High risk',
    description:
      'Multiple significant issues were found. Prioritise remediation of the high-severity findings listed below.',
  },
  critical: {
    container: 'text-danger',
    ring: 'stroke-danger',
    label: 'Critical risk',
    description:
      'Serious issues were found. Treat remediation of the critical and high-severity findings as urgent.',
  },
};

const FALLBACK: TierStyle = {
  container: 'text-text-secondary',
  ring: 'stroke-text-muted',
  label: 'Unknown tier',
  description: 'No risk score is available for this scan.',
};

const SCORE_CIRCUMFERENCE = 2 * Math.PI * 52;

export function RiskScoreCard({
  score,
  tier,
  scoreSource,
  showDetails = true,
}: {
  score: number | null;
  tier: string | null;
  scoreSource?: string | null;
  showDetails?: boolean;
}) {
  const key = tier?.toLowerCase?.() ?? '';
  const style = TIER_STYLES[key] ?? FALLBACK;
  const clamped = Math.max(0, Math.min(100, score ?? 0));
  const dashOffset = SCORE_CIRCUMFERENCE * (1 - clamped / 100);

  if (score === null || tier === null) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center">
        <p className="text-text-secondary">No risk score available for this scan.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-card">
      <div className="flex flex-col gap-6 md:flex-row md:items-center">
        <div className="flex items-center gap-5">
          <div className="relative h-28 w-28 flex-shrink-0" role="img" aria-label={`Risk score ${score} out of 100, ${style.label}`}>
            <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                strokeWidth="10"
                className="stroke-border"
              />
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                strokeWidth="10"
                strokeLinecap="round"
                className={`${style.ring} transition-[stroke-dashoffset] duration-700`}
                strokeDasharray={SCORE_CIRCUMFERENCE}
                strokeDashoffset={dashOffset}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-3xl font-bold tabular-nums ${style.container}`}>
                {score}
              </span>
              <span className="text-[11px] font-medium uppercase tracking-wider text-text-muted">
                / 100
              </span>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
              Risk tier
            </p>
            <p className={`text-2xl font-bold ${style.container}`}>{style.label}</p>
            {scoreSource && (
              <p className="mt-1 inline-flex items-center gap-1.5 rounded-full border border-border bg-muted px-2.5 py-0.5 text-[11px] text-text-secondary">
                Score source: {scoreSource.replace(/_/g, ' ')}
              </p>
            )}
          </div>
        </div>

        {showDetails && (
          <div className="md:ml-auto md:max-w-md">
            <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
              How to read this
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-text-secondary">
              {style.description}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
