import React from 'react';
import { Download } from 'lucide-react';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';
import { ApplyResponse, ReverseReport } from '../../../types';
import { ApplyOutcome } from '../../live/components/ApplyOutcome';

export interface MigrationPanelProps {
  report: ReverseReport;
  /** "live": the data is a table of the open Power BI model, so proven measures can be added to it. */
  mode: 'dataset' | 'live';
  working: 'check' | 'apply' | 'dax' | 'bim' | null;
  outcome: ApplyResponse | null;
  actionError: string | null;
  onCheck: () => void;
  onApply: () => void;
  onExport: (kind: 'dax' | 'bim') => void;
}

export const MigrationPanel: React.FC<MigrationPanelProps> = ({ report, mode, working, outcome, actionError, onCheck, onApply, onExport }) => {
  const measures = report.plan?.measures ?? [];
  const covered = measures.reduce((total, m) => total + m.cells.length, 0);
  const blocked = mode === 'live' && report.sampled;

  return (
    <Card className="space-y-4 p-6" data-testid="migration-panel">
      <div>
        <h3 className="text-base font-bold text-white">Measures you can add</h3>
        <p className="mt-1 text-sm text-gray-400">
          {measures.length === 0
            ? 'Nothing was proven well enough to turn into a measure.'
            : `${measures.length} ${measures.length === 1 ? 'measure reproduces' : 'measures reproduce'} ${covered} of the report's numbers. Only numbers proven on the raw data are included; mistakes and guesses never are.`}
        </p>
      </div>

      <ul className="space-y-2" aria-label="Planned measures">
        {measures.map((m) => (
          <li key={m.id} className="rounded-xl border border-white/10 bg-surface p-3 text-sm" data-testid={`measure-${m.id}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-white">{m.name}</span>
              <Badge variant={m.kind === 'grouped' ? 'primary' : 'info'} showDot={false}>
                {m.kind === 'grouped' ? `one measure for ${m.cells.length} numbers` : m.cells.length === 1 ? 'one number' : `${m.cells.length} identical numbers`}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-gray-300">{m.formula}</p>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-background p-2 font-mono text-xs text-gray-200">{m.dax}</pre>
            {m.notes.map((note) => (
              <p key={note} className="mt-1 text-xs text-gray-400">
                {note}
              </p>
            ))}
          </li>
        ))}
      </ul>

      {(report.plan?.not_writable ?? []).length > 0 && (
        <p className="text-xs text-amber-300" role="note">
          {report.plan!.not_writable.length} reproduced number(s) are left out because they only match the cleaned data, not the table in the model.
        </p>
      )}

      {mode === 'dataset' && (
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={measures.length === 0 || working !== null} isLoading={working === 'dax'} onClick={() => onExport('dax')} leftIcon={<Download className="h-4 w-4" />}>
            Download .dax
          </Button>
          <Button variant="outline" size="sm" disabled={measures.length === 0 || working !== null} isLoading={working === 'bim'} onClick={() => onExport('bim')} leftIcon={<Download className="h-4 w-4" />}>
            Download .bim
          </Button>
        </div>
      )}

      {mode === 'live' && (
        <>
          {blocked && (
            <p className="text-sm text-amber-300" role="note">
              Only part of this table was read, so nothing can be added to your report. Analyze with a larger row limit, or use a smaller table.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={onCheck} disabled={measures.length === 0 || blocked || working !== null} isLoading={working === 'check'}>
              Check against Power BI
            </Button>
            <Button onClick={onApply} disabled={measures.length === 0 || blocked || working !== null} isLoading={working === 'apply'}>
              Add proven measures to Power BI
            </Button>
          </div>
          {actionError && (
            <p className="text-sm text-red-300" role="alert">
              {actionError}
            </p>
          )}
          {outcome && <ApplyOutcome outcome={outcome} />}
        </>
      )}
      {mode === 'dataset' && actionError && (
        <p className="text-sm text-red-300" role="alert">
          {actionError}
        </p>
      )}
    </Card>
  );
};
