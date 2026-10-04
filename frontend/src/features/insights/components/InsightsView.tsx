import React from 'react';
import { InsightReport } from '../../../types';
import { ExecutiveSummaryCard } from './ExecutiveSummaryCard';
import { InsightCard } from './InsightCard';
import { EmptyState } from '../../../components/ui/EmptyState';
import { FlaskConical, Lightbulb } from 'lucide-react';

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

      {report.noise_note && (
        <p className="flex items-start gap-2 text-xs text-gray-400" data-testid="noise-note">
          <FlaskConical className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>{report.noise_note} Only findings that survive a correction for the number of tests run are shown.</span>
        </p>
      )}
    </div>
  );
};
