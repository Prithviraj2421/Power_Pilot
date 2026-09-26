import React from 'react';
import { ExecutiveSummary } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Sparkles, CheckCircle2, Flag } from 'lucide-react';

export interface ExecutiveSummaryCardProps {
  summary: ExecutiveSummary;
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({ summary }) => {
  if (!summary) return null;

  const keyFindings = summary.key_findings || [];

  return (
    <Card glass className="p-6 border-primary/30">
      <div className="flex items-center gap-2 text-primary font-semibold text-sm mb-2">
        <Sparkles className="w-5 h-5 animate-pulse" />
        <span>Executive Briefing</span>
      </div>

      <h3 className="text-xl font-bold text-white mb-4">{summary.headline || 'Executive Intelligence Summary'}</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className="space-y-2 bg-surface/50 p-4 rounded-xl border border-border">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-success" />
            Key Analytical Findings
          </h4>
          <ul className="space-y-1.5 text-sm text-gray-200">
            {keyFindings.map((finding, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-primary font-bold">•</span>
                <span>{finding}</span>
              </li>
            ))}
          </ul>
        </div>

        {summary.strategic_takeaway && (
          <div className="bg-surface/50 p-4 rounded-xl border border-border">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Flag className="w-4 h-4 text-warning" />
              Strategic Takeaway
            </h4>
            <p className="text-sm text-gray-200 leading-relaxed">{summary.strategic_takeaway}</p>
          </div>
        )}
      </div>
    </Card>
  );
};
