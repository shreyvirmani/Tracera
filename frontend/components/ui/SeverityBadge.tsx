import { FindingSeverity } from '@/lib/api';

interface SeverityBadgeProps {
  severity: FindingSeverity;
  size?: 'sm' | 'md' | 'lg';
}

export function SeverityBadge({ severity, size = 'md' }: SeverityBadgeProps) {
  const getSeverityConfig = (sev: FindingSeverity) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return {
          bg: 'bg-red-600',
          text: 'text-white',
          border: 'border-red-700',
          label: 'CRITICAL',
        };
      case 'high':
        return {
          bg: 'bg-red-500',
          text: 'text-white',
          border: 'border-red-600',
          label: 'HIGH',
        };
      case 'medium':
        return {
          bg: 'bg-yellow-500',
          text: 'text-white',
          border: 'border-yellow-600',
          label: 'MEDIUM',
        };
      case 'low':
        return {
          bg: 'bg-blue-500',
          text: 'text-white',
          border: 'border-blue-600',
          label: 'LOW',
        };
      case 'info':
        return {
          bg: 'bg-gray-500',
          text: 'text-white',
          border: 'border-gray-600',
          label: 'INFO',
        };
      default:
        return {
          bg: 'bg-gray-300',
          text: 'text-gray-800',
          border: 'border-gray-400',
          label: sev.toUpperCase(),
        };
    }
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-xs font-medium',
    lg: 'px-4 py-1.5 text-sm font-medium',
  };

  const config = getSeverityConfig(severity);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        config.bg
      } ${config.text} ${sizeClasses[size]}`}
    >
      {config.label}
    </span>
  );
}