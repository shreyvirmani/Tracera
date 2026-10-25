'use client';

import { AlertTriangle, RotateCw } from 'lucide-react';
import { Button } from './Button';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  fullScreen?: boolean;
  title?: string;
}

export function ErrorState({
  message,
  onRetry,
  fullScreen = false,
  title = 'Something went wrong',
}: ErrorStateProps) {
  const content = (
    <div
      role="alert"
      className="mx-auto max-w-md rounded-xl border border-danger/30 bg-danger-light/40 p-6 text-center"
    >
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-danger/30 bg-danger/10">
        <AlertTriangle className="h-6 w-6 text-danger" aria-hidden="true" />
      </div>
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      <p className="mt-1.5 text-sm text-text-secondary">{message}</p>
      {onRetry && (
        <div className="mt-5">
          <Button variant="secondary" onClick={onRetry}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </Button>
        </div>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-4">{content}</div>
    );
  }
  return <div className="p-4">{content}</div>;
}
