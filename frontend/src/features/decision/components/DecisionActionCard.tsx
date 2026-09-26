import React from 'react';
import { DecisionAction } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { ShieldAlert, TrendingUp, Clock, Target } from 'lucide-react';

export interface DecisionActionCardProps {
  decision: DecisionAction;
}

export const DecisionActionCard: React.FC<DecisionActionCardProps> = ({ decision }) => {
  const urgencyVariants = {
    IMMEDIATE: 'danger' as const,
    SHORT_TERM: 'warning' as const,
    MEDIUM_TERM: 'primary' as const,
    LONG_TERM: 'success' as const,
  };

  return (
    <Card hoverable className="p-6 flex flex-col justify-between border-primary/20">
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-primary flex-shrink-0" />
            <h4 className="text-base font-bold text-white">{decision.action_title}</h4>
          </div>
          <Badge variant={urgencyVariants[decision.urgency as keyof typeof urgencyVariants] || 'primary'}>
            {decision.urgency}
          </Badge>
        </div>

        <p className="text-sm text-gray-300 mb-4">{decision.description}</p>

        <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
          <div className="p-3 bg-surface rounded-lg border border-border">
            <span className="text-gray-400 font-medium block mb-1">Expected ROI</span>
            <span className="text-sm font-bold text-success flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              {decision.expected_roi}
            </span>
          </div>

          <div className="p-3 bg-surface rounded-lg border border-border">
            <span className="text-gray-400 font-medium block mb-1">Risk Level</span>
            <span className="text-sm font-bold text-warning flex items-center gap-1">
              <ShieldAlert className="w-4 h-4" />
              {decision.risk_level}
            </span>
          </div>
        </div>

        <div className="p-3 bg-surface/50 rounded-lg border border-border text-xs text-gray-300 mb-3">
          <span className="font-semibold text-gray-400 uppercase tracking-wider block mb-1">
            Target Entity / Department:
          </span>
          <span>{decision.target_entity}</span>
        </div>
      </div>

      <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-gray-400">
        <span>Confidence Score:</span>
        <span className="font-semibold text-white">{(decision.confidence * 100).toFixed(0)}%</span>
      </div>
    </Card>
  );
};
