import React from 'react';
import { KPIRecommendation } from '../../../types';
import { MetricCard } from '../../../components/ui/MetricCard';
import { TrendingUp, Target, ShieldAlert, Award } from 'lucide-react';

export interface KpiScorecardGridProps {
  kpis: KPIRecommendation[];
}

export const KpiScorecardGrid: React.FC<KpiScorecardGridProps> = ({ kpis }) => {
  if (!kpis || kpis.length === 0) return null;

  const icons = [
    <TrendingUp className="w-5 h-5 text-primary" />,
    <Target className="w-5 h-5 text-success" />,
    <Award className="w-5 h-5 text-purple-400" />,
    <ShieldAlert className="w-5 h-5 text-warning" />,
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {kpis.map((kpi, index) => (
        <MetricCard
          key={index}
          title={kpi.name}
          value={kpi.target_threshold || 'Active Benchmark'}
          subtitle={kpi.business_impact || kpi.reason}
          badge={kpi.priority}
          icon={icons[index % icons.length]}
          trend={{
            value: `Confidence: ${(kpi.confidence * 100).toFixed(0)}%`,
            direction: kpi.priority === 'CRITICAL' ? 'up' : 'neutral',
          }}
        />
      ))}
    </div>
  );
};
