interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
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

  const defaultIcon = (
    <svg
      className="mx-auto h-12 w-12 text-gray-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );

  return (
    <div className={`text-center ${sizeClasses[size]}`}>
      <div className="mx-auto w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        {icon || defaultIcon}
      </div>
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      {description && (
        <p className="mt-2 text-gray-500">{description}</p>
      )}
      {action && (
        <div className="mt-6">
          <button
            onClick={action.onClick}
            className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              action.variant === 'secondary'
                ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {action.label}
          </button>
        </div>
      )}
    </div>
  );
}

export function NoFindingsState() {
  return (
    <EmptyState
      title="No findings"
      description="This scan didn't detect any issues."
      icon={
        <svg
          className="mx-auto h-12 w-12 text-green-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      }
    />
  );
}

export function NoScansState(onScan?: () => void) {
  return (
    <EmptyState
      title="No scans yet"
      description="Submit a URL to start your first security scan."
      action={onScan ? { label: 'Start Scan', onClick: onScan } : undefined}
    />
  );
}

export function APIUnavailableState(onRetry?: () => void) {
  return (
    <EmptyState
      title="API Unavailable"
      description="Unable to connect to the scanning service. Please try again later."
      action={onRetry ? { label: 'Retry', onClick: onRetry, variant: 'primary' } : undefined}
      size="lg"
    />
  );
}