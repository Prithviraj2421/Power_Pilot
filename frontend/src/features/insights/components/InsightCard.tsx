import React from 'react';
import { Insight } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { AlertCircle, CheckSquare } from 'lucide-react';

export interface InsightCardProps {
  insight: Insight;
}

export const InsightCard: React.FC<InsightCardProps> = ({ insight }) => {
  const severityVariants = {
    CRITICAL: 'danger' as const,
    HIGH: 'warning' as const,
    MEDIUM: 'primary' as const,
    LOW: 'success' as const,
  };

  const sevKey = (insight.severity || 'MEDIUM').toString().toUpperCase() as keyof typeof severityVariants;
  const badgeVariant = severityVariants[sevKey] || 'primary';

  return (
    <Card hoverable className="p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-primary flex-shrink-0" />
            <h4 className="text-base font-semibold text-white">{insight.title}</h4>
          </div>
          <Badge variant={badgeVariant}>{sevKey}</Badge>
        </div>

        <p className="text-sm text-gray-300 mb-4">{insight.description}</p>

        {insight.business_impact && (
          <div className="p-3 bg-surface rounded-lg border border-border mb-3 text-xs">
            <span className="font-semibold text-gray-400 uppercase tracking-wider block mb-1">
              Business Impact:
            </span>
            <span className="text-gray-200">{insight.business_impact}</span>
          </div>
        )}
      </div>

      {insight.recommendation && (
        <div className="mt-2 pt-3 border-t border-border flex items-start gap-2 text-xs">
          <CheckSquare className="w-4 h-4 text-success flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-success">
              Recommendation: {insight.recommendation.action_title}
            </span>
            <p className="text-gray-400 mt-0.5">{insight.recommendation.description}</p>
          </div>
        </div>
      )}
    </Card>
  );
};
