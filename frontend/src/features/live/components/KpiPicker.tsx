import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { Badge } from '../../../components/ui/Badge';
import { Card } from '../../../components/ui/Card';
import { LiveKpi, LiveTableAnalysis } from '../../../types';
import { formatKpiValue } from '../../kpis/formatKpiValue';
import { isWritable } from '../useLiveModel';

export interface KpiPickerProps {
  table: LiveTableAnalysis;
  selected: Set<string>;
  onToggle: (id: string) => void;
}

function reasonDisabled(table: LiveTableAnalysis, kpi: LiveKpi): string | null {
  if (!table.can_write) return 'Only a sample of this table was read, so this cannot be checked against Power BI.';
  if (kpi.added_by_powerpilot) return 'PowerPilot already added this measure.';
  if (kpi.name_taken) return 'A measure with this name already exists in your model. It will not be touched.';
  if (!kpi.verified) return 'This KPI did not pass verification.';
  return null;
}

export const KpiPicker: React.FC<KpiPickerProps> = ({ table, selected, onToggle }) => (
  <Card className="p-6" data-testid={`analysis-${table.table}`}>
    <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-base font-bold text-white">{table.table}</h3>
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <Badge variant="info" showDot={false}>
          {table.domain}
        </Badge>
        {table.rows_read.toLocaleString('en-US')} of {table.rows_total.toLocaleString('en-US')} rows read
      </div>
    </div>

    {table.sampled && (
      <p className="mb-3 mt-2 text-xs text-amber-300" role="alert">
        Only the first {table.rows_read.toLocaleString('en-US')} of {table.rows_total.toLocaleString('en-US')} rows were
        read, so measures from this table cannot be added to your report.
      </p>
    )}

    {table.kpis.length === 0 ? (
      <p className="mt-3 text-sm text-gray-400">No KPI could be verified for this table.</p>
    ) : (
      <ul className="mt-3 space-y-3">
        {table.kpis.map((kpi) => {
          const disabled = reasonDisabled(table, kpi);
          const value = formatKpiValue(kpi);
          return (
            <li key={kpi.id} className="rounded-xl border border-white/10 bg-surface p-3">
              <label className={`flex items-start gap-3 ${disabled ? 'opacity-70' : 'cursor-pointer'}`}>
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={selected.has(kpi.id)}
                  disabled={!isWritable(table, kpi)}
                  onChange={() => onToggle(kpi.id)}
                  aria-label={`Add ${kpi.name} to my report`}
                />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-white">{kpi.name}</span>
                    <span className="flex items-center gap-2">
                      {kpi.verified && (
                        <Badge variant="success" showDot={false}>
                          <ShieldCheck className="mr-1 inline h-3 w-3" />
                          Verified
                        </Badge>
                      )}
                      {value !== null && <span className="text-lg font-bold text-white">{value}</span>}
                    </span>
                  </span>
                  {kpi.formula && (
                    <code className="mt-1 block overflow-x-auto rounded-lg bg-background px-2 py-1 font-mono text-xs text-blue-300">
                      {kpi.formula}
                    </code>
                  )}
                  {kpi.baseline && <span className="mt-1 block text-xs text-gray-400">{kpi.baseline}</span>}
                  {disabled && (
                    <span className="mt-1 block text-xs text-amber-300" data-testid="disabled-reason">
                      {disabled}
                    </span>
                  )}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    )}

    {table.rejected.length > 0 && (
      <details className="mt-4 text-xs text-gray-400">
        <summary className="cursor-pointer">{table.rejected.length} KPI(s) did not pass verification</summary>
        <ul className="mt-2 space-y-1">
          {table.rejected.map((r) => (
            <li key={r.name}>
              <span className="font-semibold text-gray-200">{r.name}</span> — {r.reason}
            </li>
          ))}
        </ul>
      </details>
    )}
  </Card>
);
