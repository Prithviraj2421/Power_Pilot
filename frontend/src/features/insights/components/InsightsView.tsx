import React from 'react';
import { InsightReport } from '../../../types';
import { ExecutiveSummaryCard } from './ExecutiveSummaryCard';
import { InsightCard } from './InsightCard';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Lightbulb } from 'lucide-react';

export interface InsightsViewProps {
  report?: InsightReport | null;
}

export const InsightsView: React.FC<InsightsViewProps> = ({ report }) => {
  const insights = report?.insights || [];

  if (!report || (!report.executive_summary && insights.length === 0)) {
    return (
      <EmptyState
        title="No Executive Insights Generated"
        description="The intelligence pipeline did not detect critical anomalies or risk thresholds requiring high-severity alert cards."
        icon={<Lightbulb className="w-12 h-12 text-primary" />}
      />
    );
  }

  return (
    <div className="space-y-6">
      {report.executive_summary && <ExecutiveSummaryCard summary={report.executive_summary} />}

      {insights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {insights.map((insight, idx) => (
            <InsightCard key={idx} insight={insight} />
          ))}
        </div>
      )}
    </div>
  );
};
