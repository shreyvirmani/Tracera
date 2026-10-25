'use client';

import { HTMLAttributes, forwardRef } from 'react';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?:
    | 'default'
    | 'success'
    | 'warning'
    | 'danger'
    | 'info'
    | 'neutral'
    | 'primary'
    | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
}

const variantStyles: Record<string, string> = {
  default: 'bg-muted text-text-secondary border-border',
  success: 'bg-success-light text-success border-success/20',
  warning: 'bg-warning-light text-warning border-warning/20',
  danger: 'bg-danger-light text-danger border-danger/20',
  info: 'bg-info-light text-severity-low border-severity-low/20',
  neutral: 'bg-muted text-text-secondary border-border',
  primary: 'bg-primary/10 text-primary border-primary/20',
  secondary: 'bg-secondary/10 text-secondary border-secondary/20',
};

const sizeStyles: Record<string, string> = {
  sm: 'px-2 py-0.5 text-[11px]',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const dotColors: Record<string, string> = {
  default: 'bg-text-muted',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  info: 'bg-severity-low',
  neutral: 'bg-text-muted',
  primary: 'bg-primary',
  secondary: 'bg-secondary',
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = 'default',
      size = 'md',
      dot = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {dot && (
          <span
            aria-hidden="true"
            className={`h-1.5 w-1.5 rounded-full ${dotColors[variant]}`}
          />
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

const SCAN_STATUS_CONFIG: Record<string, { variant: Parameters<typeof Badge>[0]['variant']; label: string }> = {
  pending: { variant: 'warning', label: 'Pending' },
  running: { variant: 'info', label: 'Running' },
  completed: { variant: 'success', label: 'Completed' },
  failed: { variant: 'danger', label: 'Failed' },
};

export function StatusBadge({ status, size = 'md', showDot = true }: StatusBadgeProps) {
  const config = SCAN_STATUS_CONFIG[status] ?? {
    variant: 'neutral' as const,
    label: status || 'Unknown',
  };
  return (
    <Badge variant={config.variant} size={size} dot={showDot}>
      {config.label}
    </Badge>
  );
}
