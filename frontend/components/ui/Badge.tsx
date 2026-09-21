import { HTMLAttributes, forwardRef } from 'react';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  removable?: boolean;
  onRemove?: () => void;
}

const variantStyles = {
  default: 'bg-gray-100 text-gray-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  neutral: 'bg-gray-100 text-gray-700',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const dotColors = {
  default: 'bg-gray-400',
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
  neutral: 'bg-gray-400',
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = 'default',
      size = 'md',
      dot = false,
      removable = false,
      onRemove,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={`
          inline-flex items-center gap-1.5 font-medium rounded-full
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${className}
        `}
        {...props}
      >
        {dot && (
          <span
            className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`}
            aria-hidden="true"
          />
        )}
        {children}
        {removable && onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="ml-1 p-0.5 rounded-full hover:bg-black/10 transition-colors"
            aria-label="Remove"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

interface StatusBadgeProps {
  status: 'active' | 'inactive' | 'pending' | 'processing' | 'completed' | 'failed' | 'warning';
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

const statusConfig = {
  active: { variant: 'success' as const, label: 'Active' },
  inactive: { variant: 'neutral' as const, label: 'Inactive' },
  pending: { variant: 'warning' as const, label: 'Pending' },
  processing: { variant: 'info' as const, label: 'Processing' },
  completed: { variant: 'success' as const, label: 'Completed' },
  failed: { variant: 'danger' as const, label: 'Failed' },
  warning: { variant: 'warning' as const, label: 'Warning' },
};

export function StatusBadge({ status, size = 'md', showDot = true }: StatusBadgeProps) {
  const config = statusConfig[status];
  return (
    <Badge variant={config.variant} size={size} dot={showDot}>
      {config.label}
    </Badge>
  );
}