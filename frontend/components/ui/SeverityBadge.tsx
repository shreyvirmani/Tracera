import { FindingSeverity } from '@/lib/api';

type SeverityStyle = {
  container: string;
  dot: string;
  label: string;
};

const SEVERITY_STYLES: Record<string, SeverityStyle> = {
  critical: {
    container: 'bg-danger/15 text-danger border border-danger/30',
    dot: 'bg-danger',
    label: 'Critical',
  },
  high: {
    container: 'bg-severity-high/15 text-severity-high border border-severity-high/30',
    dot: 'bg-severity-high',
    label: 'High',
  },
  medium: {
    container: 'bg-warning/15 text-warning border border-warning/30',
    dot: 'bg-warning',
    label: 'Medium',
  },
  low: {
    container: 'bg-severity-low/15 text-severity-low border border-severity-low/30',
    dot: 'bg-severity-low',
    label: 'Low',
  },
  info: {
    container: 'bg-muted text-text-secondary border border-border',
    dot: 'bg-text-muted',
    label: 'Info',
  },
};

const FALLBACK: SeverityStyle = {
  container: 'bg-muted text-text-secondary border border-border',
  dot: 'bg-text-muted',
  label: 'Unknown',
};

interface SeverityBadgeProps {
  severity: FindingSeverity;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

export function SeverityBadge({
  severity,
  size = 'md',
  showDot = true,
}: SeverityBadgeProps) {
  const key = severity?.toLowerCase?.() ?? '';
  const style = SEVERITY_STYLES[key] ?? FALLBACK;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px] gap-1.5',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-sm gap-2',
  };

  const dotSizes = { sm: 'w-1.5 h-1.5', md: 'w-2 h-2', lg: 'w-2.5 h-2.5' };

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium tracking-wide ${style.container} ${sizeClasses[size]}`}
    >
      {showDot && (
        <span aria-hidden="true" className={`rounded-full ${style.dot} ${dotSizes[size]}`} />
      )}
      {style.label}
    </span>
  );
}
