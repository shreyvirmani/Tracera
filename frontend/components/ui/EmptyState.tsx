import { ShieldCheck } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
    variant?: 'primary' | 'secondary';
  };
  size?: 'sm' | 'md' | 'lg';
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  size = 'md',
}: EmptyStateProps) {
  const sizeClasses = {
    sm: 'py-6 px-4',
    md: 'py-12 px-4',
    lg: 'py-16 px-4',
  };

  return (
    <div className={`text-center ${sizeClasses[size]}`}>
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-border bg-surface">
        {icon || <ShieldCheck className="h-6 w-6 text-text-muted" aria-hidden="true" />}
      </div>
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      {description && <p className="mt-1.5 text-sm text-text-secondary">{description}</p>}
      {action && (
        <div className="mt-6">
          {action.href ? (
            <a
              href={action.href}
              className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-ring ${
                action.variant === 'secondary'
                  ? 'border border-border bg-surface text-text-primary hover:bg-elevated'
                  : 'bg-primary text-background hover:bg-primary-hover'
              }`}
            >
              {action.label}
            </a>
          ) : (
            <Button
              variant={action.variant === 'secondary' ? 'secondary' : 'primary'}
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export function NoFindingsState() {
  return (
    <EmptyState
      title="No findings recorded"
      description="The checks that ran did not identify any issues on this target. This reflects only the rules that executed — it is not a guarantee of security."
    />
  );
}
