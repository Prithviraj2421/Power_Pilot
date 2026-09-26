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
    </div>
  );
};
