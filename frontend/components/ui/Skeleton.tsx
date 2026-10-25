export function Skeleton({
  className = '',
  variant = 'text',
}: {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
}) {
  const variantStyles = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-muted ${variantStyles[variant]} ${className}`}
    />
  );
}

export function SkeletonText({
  lines = 3,
  className = '',
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} variant="text" className={i === lines - 1 ? 'w-3/5' : 'w-full'} />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-card p-6 ${className}`}>
      <div className="mb-6 flex items-center gap-4">
        <Skeleton variant="circular" className="h-12 w-12" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" className="w-2/5" />
          <Skeleton variant="text" className="w-3/5" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg bg-surface p-4">
            <Skeleton variant="text" className="w-1/2" />
            <Skeleton variant="text" className="mt-2 w-4/5" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonStatCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-card p-6 ${className}`}>
      <Skeleton variant="text" className="w-24" />
      <Skeleton variant="text" className="mt-3 h-9 w-16" />
    </div>
  );
}

export function SkeletonFinding({ className = '' }: { className?: string }) {
  return (
    <div className={`p-4 ${className}`}>
      <div className="flex items-start gap-4">
        <Skeleton variant="rectangular" className="mt-1 h-6 w-20 flex-shrink-0" />
        <div className="min-w-0 flex-1 space-y-2.5">
          <Skeleton variant="text" className="w-3/4" />
          <Skeleton variant="text" className="w-full" />
          <Skeleton variant="text" className="w-2/3" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonSeveritySection({ className = '' }: { className?: string }) {
  return (
    <div
      className={`overflow-hidden rounded-xl border border-border bg-card ${className}`}
    >
      <div className="border-b border-border bg-surface px-6 py-4">
        <Skeleton variant="text" className="w-2/5" />
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonFinding key={i} />
        ))}
      </div>
    </div>
  );
}

export function SkeletonTable({
  rows = 5,
  className = '',
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={`overflow-hidden rounded-xl border border-border bg-card ${className}`}>
      <div className="border-b border-border bg-surface px-6 py-4">
        <Skeleton variant="text" className="w-40" />
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-6 px-6 py-4">
            <Skeleton variant="text" className="w-1/3" />
            <Skeleton variant="rectangular" className="h-6 w-20" />
            <Skeleton variant="text" className="w-16" />
            <Skeleton variant="text" className="ml-auto w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}
