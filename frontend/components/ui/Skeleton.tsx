interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  className = '',
  variant = 'text',
  width,
  height,
  animation = 'pulse',
}: SkeletonProps) {
  const baseStyles = 'bg-gray-200 dark:bg-gray-700 rounded';
  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-[shimmer_1.5s_infinite]',
    none: '',
  };

  const variantStyles = {
    text: 'h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={`${baseStyles} ${variantStyles[variant]} ${animationClasses[animation]} ${className}`}
      style={style}
    />
  );
}

export function SkeletonText({ lines = 3, className = '', ...props }: { lines?: number; className?: string } & Omit<SkeletonProps, 'variant'>) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} variant="text" width={i === lines - 1 ? '60%' : '100%'} {...props} />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-white border border-gray-200 rounded-xl p-6 ${className}`}>
      <div className="flex items-center gap-4 mb-6">
        <Skeleton variant="circular" width="48" height="48" />
        <div className="flex-1">
          <Skeleton variant="text" width="40%" height="24" />
          <Skeleton variant="text" width="60%" height="16" className="mt-2" />
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-gray-50 rounded-lg p-4">
            <Skeleton variant="text" width="50%" height="14" />
            <Skeleton variant="text" width="80%" height="24" className="mt-2" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonFinding({ className = '' }: { className?: string }) {
  return (
    <div className={`p-4 hover:bg-gray-50 transition-colors ${className}`}>
      <div className="flex items-start gap-4">
        <Skeleton variant="text" width="80" height="24" className="flex-shrink-0 mt-1" />
        <div className="flex-1 min-w-0 space-y-3">
          <Skeleton variant="text" width="70%" height="16" />
          <Skeleton variant="text" width="100%" height="16" />
          <Skeleton variant="text" width="100%" height="14" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonSeveritySection({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-100 animate-pulse">
        <Skeleton variant="text" width="40%" height="20" />
      </div>
      <div className="divide-y divide-gray-100">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonFinding key={i} />
        ))}
      </div>
    </div>
  );
}