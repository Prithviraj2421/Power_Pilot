import React from 'react';
import { DatasetQualityReport } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { ShieldCheck, AlertTriangle, CheckCircle2, FileCheck, HelpCircle } from 'lucide-react';

export interface DataQualityScoreCardProps {
  report: DatasetQualityReport;
}

export const DataQualityScoreCard: React.FC<DataQualityScoreCardProps> = ({ report }) => {
  const gradeVariants: Record<string, 'success' | 'primary' | 'warning' | 'danger'> = {
    'A+': 'success',
    A: 'success',
    B: 'primary',
    C: 'warning',
    D: 'danger',
    F: 'danger',
  };

  const badgeVariant = gradeVariants[report.grade] || 'primary';

  return (
    <Card glass className="p-6 border-primary/30">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6 pb-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-xl text-primary border border-primary/20">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold text-white">Stage 1: Data Quality Assessment</h3>
              <Badge variant={badgeVariant} className="text-sm px-3 py-1 font-bold">
                Grade {report.grade}
              </Badge>
            </div>
            <p className="text-sm text-gray-400 mt-1">{report.grade_explanation}</p>
          </div>
        </div>

        <div className="text-right flex items-center gap-3 bg-surface/50 p-4 rounded-xl border border-border">
          <div>
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
              Overall Quality Score
            </span>
            <span className="text-3xl font-extrabold text-white">{report.overall_score}%</span>
          </div>
        </div>
      </div>

      {/* Issues Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-surface/50 rounded-xl border border-border flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-success flex-shrink-0" />
          <div>
            <span className="text-xs text-gray-400 uppercase font-semibold">Total Issues Detected</span>
            <p className="text-lg font-bold text-white">{report.total_issues_count} Issue(s)</p>
          </div>
        </div>

        <div className="p-4 bg-surface/50 rounded-xl border border-border flex items-center gap-3">
          <FileCheck className="w-6 h-6 text-primary flex-shrink-0" />
          <div>
            <span className="text-xs text-gray-400 uppercase font-semibold">Columns Assessed</span>
            <p className="text-lg font-bold text-white">{report.column_scores.length} Columns</p>
          </div>
        </div>

        <div className="p-4 bg-surface/50 rounded-xl border border-border flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-warning flex-shrink-0" />
          <div>
            <span className="text-xs text-gray-400 uppercase font-semibold">Quality Status</span>
            <p className="text-lg font-bold text-white">
              {report.overall_score >= 85 ? 'Validated & Ready' : 'Preparation Advised'}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
};
