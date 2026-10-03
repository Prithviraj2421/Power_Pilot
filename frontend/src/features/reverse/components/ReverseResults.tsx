import React from 'react';
import { ReverseReport } from '../../../types';
import { useMigration } from '../useReverse';
import { CellDetailPanel } from './CellDetailPanel';
import { MigrationPanel } from './MigrationPanel';
import { ReportGrid } from './ReportGrid';
import { SummaryBar } from './SummaryBar';

export interface ReverseResultsProps {
  report: ReverseReport;
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** The live-model session token; present only when proven measures may be added to the open report. */
  token?: string | null;
}

/** Summary, the colour-coded report, the selected number's story, and the measures that can be added. */
export const ReverseResults: React.FC<ReverseResultsProps> = ({ report, selectedId, onSelect, token = null }) => {
  const migration = useMigration(report, token);
  const selected = report.cells.find((c) => c.id === selectedId) ?? null;

  return (
    <div className="space-y-6" data-testid="reverse-results">
      <SummaryBar summary={report.summary} warnings={report.warnings} filename={report.filename} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <ReportGrid report={report} selectedId={selectedId} onSelect={onSelect} />
        <div className="lg:sticky lg:top-4 lg:self-start">
          <CellDetailPanel cell={selected} />
        </div>
      </div>
      <MigrationPanel
        report={report}
        mode={report.live ? 'live' : 'dataset'}
        working={migration.working}
        outcome={migration.outcome}
        actionError={migration.actionError}
        onCheck={() => void migration.check()}
        onApply={() => void migration.apply()}
        onExport={(kind) => void migration.exportAs(kind)}
      />
    </div>
  );
};
