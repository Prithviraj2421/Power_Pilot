import React, { useCallback, useState } from 'react';
import { ReverseService } from '../../../services/reverseService';
import { LiveStatus } from '../../../types';
import { useReverseRun } from '../useReverse';
import { ReportUpload } from './ReportUpload';
import { ReverseResults } from './ReverseResults';

export interface LiveReverseSectionProps {
  token: string;
  status: LiveStatus;
  /** The table most likely to hold the data behind the old report. */
  defaultTable: string | null;
}

/** "Prove-It Migration" inside Power BI: explain an old report with a table of the open model, then add what was proven. */
export const LiveReverseSection: React.FC<LiveReverseSectionProps> = ({ token, status, defaultTable }) => {
  const [table, setTable] = useState<string>(defaultTable ?? status.tables[0]?.name ?? '');
  const runner = useCallback((file: File) => ReverseService.runLive(token, table, file), [token, table]);
  const reverse = useReverseRun(runner);

  if (status.tables.length === 0) return null;

  return (
    <section className="space-y-6" aria-label="Prove-It Migration">
      <ReportUpload
        file={reverse.file}
        running={reverse.running}
        error={reverse.error}
        onFile={reverse.chooseFile}
        onRun={() => void reverse.run()}
        disabled={!table}
      >
        <label className="flex flex-wrap items-center gap-2 text-sm text-gray-300">
          Data behind the old report
          <select
            className="rounded-lg border border-white/15 bg-surface px-2 py-1.5 text-sm text-white"
            value={table}
            onChange={(event) => setTable(event.target.value)}
            aria-label="Table to check the report against"
          >
            {status.tables.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
      </ReportUpload>
      {reverse.report && <ReverseResults report={reverse.report} selectedId={reverse.selectedId} onSelect={reverse.select} token={token} />}
    </section>
  );
};
