import React from 'react';
import { KPIReport } from '../../../types';
import { DaxFormulaCard } from './DaxFormulaCard';

export interface KpiStudioViewProps {
  report: KPIReport;
}

export const KpiStudioView: React.FC<KpiStudioViewProps> = ({ report }) => {
  if (!report) return null;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-white mb-1">Primary Power BI Measures (DAX)</h3>
        <p className="text-xs text-gray-400">
          Executable DAX measures generated for primary executive metrics. Click copy to paste directly into Power BI Desktop.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {report.primary_kpis.map((kpi, idx) => (
          <DaxFormulaCard key={idx} kpi={kpi} />
        ))}
      </div>

      {report.secondary_kpis.length > 0 && (
        <>
          <div className="pt-4">
            <h3 className="text-lg font-bold text-white mb-1">Secondary Measures</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {report.secondary_kpis.map((kpi, idx) => (
              <DaxFormulaCard key={idx} kpi={kpi} />
            ))}
          </div>
        </>
      )}

      {report.rejected_kpis && report.rejected_kpis.length > 0 && (
        <div className="pt-4" data-testid="rejected-kpis">
          <h3 className="text-lg font-bold text-white mb-1">Rejected KPIs</h3>
          <p className="text-xs text-gray-400 mb-3">
            These failed verification against your dataset, so they are not shown as measures and are not exported.
          </p>
          <ul className="space-y-2">
            {report.rejected_kpis.map((kpi, idx) => (
              <li key={idx} className="text-xs bg-surface border border-border rounded-lg p-3">
                <span className="font-semibold text-white">{kpi.name}</span>
                <span className="text-gray-400"> — {kpi.verification_note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
