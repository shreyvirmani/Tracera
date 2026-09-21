interface RiskScoreCardProps {
  score: number | null;
  tier: string | null;
  scoreSource?: string | null;
  showDetails?: boolean;
}

export function RiskScoreCard({
  score,
  tier,
  scoreSource,
  showDetails = true,
}: RiskScoreCardProps) {
  const getTierBadgeClass = (tier: string | null) => {
    switch (tier?.toLowerCase()) {
      case 'critical':
        return 'bg-red-600 text-white';
      case 'high':
        return 'bg-red-500 text-white';
      case 'medium':
        return 'bg-yellow-500 text-white';
      case 'low':
        return 'bg-green-500 text-white';
      default:
        return 'bg-gray-300 text-gray-800';
    }
  };

  const getTierBadgeClassSmall = (tier: string | null) => {
    switch (tier?.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTierClass = (tier: string | null, variant: 'large' | 'small' = 'large') => {
    if (variant === 'small') {
      return getTierBadgeClassSmall(tier);
    }
    return getTierBadgeClass(tier);
  };

  const tierClass = tier ? getTierClass(tier, 'large') : 'bg-gray-300 text-gray-800';
  const tierBadgeClass = tier ? getTierClass(tier, 'small') : 'bg-gray-100 text-gray-800';

  if (score === null || tier === null) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center">
        <p className="text-gray-500">No risk score available</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="flex items-center gap-4">
          <div
            className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold ${tierClass}`}
          >
            {score}
          </div>
          <div>
            <p className="text-sm text-gray-500">Risk Tier</p>
            <p className="text-2xl font-bold text-gray-900">
              {tier?.toUpperCase() || 'UNKNOWN'}
            </p>
          </div>
        </div>

        {showDetails && (
          <div className="flex flex-wrap items-center gap-4 md:ml-auto">
            <div className={`px-4 py-2 rounded-full text-sm font-medium ${tierBadgeClass}`}>
              {tier?.toUpperCase() || 'UNKNOWN'}
            </div>
            {score !== null && (
              <div className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                Score: {score}/100
              </div>
            )}
            {scoreSource && (
              <div className="px-4 py-2 bg-gray-100 text-gray-700 rounded-full text-sm">
                Source: {scoreSource.replace('_', ' ')}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}