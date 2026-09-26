import React from 'react';
import { DataPreparationReport } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { CheckCircle, History, ArrowRight } from 'lucide-react';

export interface DataQualityAuditTrailProps {
  report: DataPreparationReport;
}

export const DataQualityAuditTrail: React.FC<DataQualityAuditTrailProps> = ({ report }) => {
  return (
    <Card glass className="p-6">
      <div className="flex items-center gap-2 text-white font-bold text-lg mb-4">
        <History className="w-5 h-5 text-primary" />
        <span>Stage 1: Data Preparation Audit Trail</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-surface rounded-xl border border-border">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1">
            Original Rows
          </span>
          <span className="text-xl font-bold text-white">{report.original_rows}</span>
        </div>

        <div className="p-4 bg-surface rounded-xl border border-border">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1">
            Cleaned Rows Passed
          </span>
          <span className="text-xl font-bold text-success">{report.cleaned_rows}</span>
        </div>

        <div className="p-4 bg-surface rounded-xl border border-border">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1">
            Transformations Executed
          </span>
          <span className="text-xl font-bold text-primary">{report.total_actions_count} Actions</span>
        </div>
      </div>

      {report.audit_trail.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Audit Log Entries</h4>
          <div className="space-y-2 max-h-60 overflow-y-auto pr-2">
            {report.audit_trail.map((entry, idx) => (
              <div
                key={idx}
                className="p-3 bg-surface/70 rounded-lg border border-border flex items-center justify-between text-xs gap-3"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-success flex-shrink-0" />
                  <span className="font-semibold text-white">{entry.column_name}:</span>
                  <span className="text-gray-300">{entry.action_type}</span>
                </div>

                <div className="flex items-center gap-2 text-gray-400">
                  <span>{entry.before_sample}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-primary" />
                  <span className="text-gray-200 font-medium">{entry.after_sample}</span>
                  <span className="text-xs text-primary font-bold">({entry.rows_affected} rows)</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};
