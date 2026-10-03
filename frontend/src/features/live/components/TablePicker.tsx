import React from 'react';
import { Database } from 'lucide-react';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';
import { LiveStatus } from '../../../types';

export interface TablePickerProps {
  status: LiveStatus;
  selected: Set<string>;
  analyzing: boolean;
  onToggle: (name: string) => void;
  onAnalyze: () => void;
}

export const TablePicker: React.FC<TablePickerProps> = ({ status, selected, analyzing, onToggle, onAnalyze }) => {
  if (status.tables.length === 0) {
    return (
      <Card className="p-6 text-sm text-gray-300">
        This model has no tables with data to analyze yet. Load some data in Power BI, then reload this page.
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center gap-2">
        <Database className="h-5 w-5 text-primary" />
        <h3 className="text-base font-bold text-white">Tables in your open model</h3>
      </div>

      <ul className="space-y-2" aria-label="Tables">
        {status.tables.map((table) => (
          <li key={table.name}>
            <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-white/10 bg-surface px-3 py-2.5 hover:border-primary/40">
              <span className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={selected.has(table.name)}
                  onChange={() => onToggle(table.name)}
                  aria-label={`Analyze ${table.name}`}
                />
                <span className="font-medium text-white">{table.name}</span>
              </span>
              <span className="flex items-center gap-2 text-xs text-gray-400">
                {table.will_be_sampled && (
                  <Badge variant="warning" showDot={false}>
                    sample only
                  </Badge>
                )}
                {table.rows.toLocaleString('en-US')} rows · {table.columns} columns
              </span>
            </label>
          </li>
        ))}
      </ul>

      {status.tables.some((t) => selected.has(t.name) && t.will_be_sampled) && (
        <p className="mt-3 text-xs text-amber-300" role="note">
          A table over {status.max_rows.toLocaleString('en-US')} rows is analyzed from its first{' '}
          {status.max_rows.toLocaleString('en-US')} rows. Its KPIs cannot be checked against Power BI's engine like for
          like, so they cannot be added to your report.
        </p>
      )}

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-[11px] text-gray-500">
          PowerPilot keeps a local copy of the rows it reads, on this computer only, so it can re-check KPIs. You can
          remove it afterwards.
        </p>
        <Button onClick={onAnalyze} disabled={selected.size === 0 || analyzing} isLoading={analyzing}>
          {analyzing ? 'Reading your model…' : 'Analyze selected'}
        </Button>
      </div>
    </Card>
  );
};
