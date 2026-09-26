import React from 'react';
import { DatasetQualityReport, DataPreparationReport } from '../../../types';
import { DataQualityScoreCard } from './DataQualityScoreCard';
import { DataQualityAuditTrail } from './DataQualityAuditTrail';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { AlertCircle, Wrench, ShieldCheck } from 'lucide-react';

export interface QualityStudioViewProps {
  qualityReport?: DatasetQualityReport;
  preparationReport?: DataPreparationReport;
}

export const QualityStudioView: React.FC<QualityStudioViewProps> = ({
  qualityReport,
  preparationReport,
}) => {
  if (!qualityReport) return null;

  return (
    <div className="space-y-6">
      <DataQualityScoreCard report={qualityReport} />

      {preparationReport && <DataQualityAuditTrail report={preparationReport} />}

      {/* Detected Issues List */}
      <Card glass className="p-6">
        <div className="flex items-center gap-2 text-white font-bold text-lg mb-4">
          <Wrench className="w-5 h-5 text-warning" />
          <span>Stage 1: Validation Warnings & Treatments</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {qualityReport.detected_issues.map((issue, idx) => (
            <div key={idx} className="p-4 bg-surface rounded-xl border border-border flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-white">{issue.column}</span>
                  <Badge
                    variant={
                      issue.severity === 'CRITICAL'
                        ? 'danger'
                        : issue.severity === 'HIGH'
                        ? 'warning'
                        : 'primary'
                    }
                  >
                    {issue.severity}
                  </Badge>
                </div>
                <p className="text-xs text-gray-300 mb-3">{issue.description}</p>
              </div>

              <div className="p-2.5 bg-surface/50 rounded-lg border border-border/50 text-xs">
                <span className="text-gray-400 font-semibold uppercase tracking-wider block mb-0.5">
                  Recommended Treatment:
                </span>
                <span className="text-primary font-medium">{issue.recommended_treatment}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
