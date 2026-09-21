interface ErrorStateProps {
  message: string;
  error?: Error | null;
  onRetry?: () => void;
  retryLabel?: string;
  fullScreen?: boolean;
  icon?: React.ReactNode;
}

export function ErrorState({
  message,
  error,
  onRetry,
  retryLabel = 'Try Again',
  fullScreen = false,
  icon,
}: ErrorStateProps) {
  const containerClasses = fullScreen
    ? 'fixed inset-0 z-50 flex items-center justify-center bg-gray-50 p-4'
    : 'w-full';

  return (
    <div className={containerClasses}>
      <div className="w-full max-w-md mx-auto text-center py-12 px-4">
        {icon || (
          <svg
            className="mx-auto h-12 w-12 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        )}
        <h2 className="mt-4 text-xl font-semibold text-gray-900">
          Something went wrong
        </h2>
        <p className="mt-2 text-gray-600">{message}</p>
        {error && (
          <details className="mt-4 text-left">
            <summary className="text-sm text-gray-500 cursor-pointer">
              Show error details
            </summary>
            <pre className="mt-2 p-3 bg-gray-100 rounded text-xs text-gray-700 overflow-x-auto">
              {error instanceof Error ? error.message : String(error)}
              {error instanceof Error && error.stack && (
                <>
                  {'\n\nStack:\n'}
                  {error.stack}
                </>
              )}
            </pre>
          </details>
        )}
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-6 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
          >
            {retryLabel}
          </button>
        )}
      </div>
    </div>
  );
}

export function InlineError({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss?: () => void;
}) {
  return (
    <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
      <svg
        className="flex-shrink-0 h-5 w-5 text-red-400"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293a1 1 0 00-1.414 0z"
          clipRule="evenodd"
        />
      </svg>
      <div className="flex-1">
        <p className="text-sm text-red-700">{message}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-red-500 hover:text-red-700"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}