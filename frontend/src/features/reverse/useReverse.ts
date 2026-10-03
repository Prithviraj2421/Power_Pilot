import { useCallback, useState } from 'react';
import { ReverseService } from '../../services/reverseService';
import { ApplyResponse, ReverseReport } from '../../types';
import { downloadText } from './reverseView';

function describe(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.';
}

/** The first number worth looking at: something not reproduced, else something ambiguous. */
export function firstToInspect(report: ReverseReport): string | null {
  return (
    report.cells.find((c) => c.status === 'NOT_REPRODUCIBLE')?.id ??
    report.cells.find((c) => c.status === 'AMBIGUOUS')?.id ??
    null
  );
}

/** Pick a report file, run the reverse-engineering with `runner`, and browse the result. */
export function useReverseRun(runner: (file: File) => Promise<ReverseReport>) {
  const [file, setFile] = useState<File | null>(null);
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<ReverseReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const run = useCallback(async () => {
    if (!file) return;
    setRunning(true);
    setError(null);
    try {
      const result = await runner(file);
      setReport(result);
      setSelectedId(firstToInspect(result));
    } catch (exception) {
      setError(describe(exception));
    } finally {
      setRunning(false);
    }
  }, [file, runner]);

  const chooseFile = useCallback((chosen: File | null) => {
    setFile(chosen);
    setError(null);
  }, []);

  return { file, chooseFile, running, report, error, selectedId, select: setSelectedId, run };
}

/** Check measures against Power BI's engine, add them, or download them. Measure ids only; DAX stays on the server. */
export function useMigration(report: ReverseReport | null, token: string | null) {
  const [working, setWorking] = useState<'check' | 'apply' | 'dax' | 'bim' | null>(null);
  const [outcome, setOutcome] = useState<ApplyResponse | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const submit = useCallback(
    async (dryRun: boolean) => {
      if (!report || !token) return;
      const ids = (report.plan?.measures ?? []).map((m) => m.id);
      if (ids.length === 0) return;
      setWorking(dryRun ? 'check' : 'apply');
      setActionError(null);
      setOutcome(null);
      try {
        setOutcome(await ReverseService.applyLive(token, report.report_id, ids, dryRun));
      } catch (exception) {
        setActionError(describe(exception));
      } finally {
        setWorking(null);
      }
    },
    [report, token]
  );

  const exportAs = useCallback(
    async (kind: 'dax' | 'bim') => {
      if (!report) return;
      setWorking(kind);
      setActionError(null);
      try {
        const stem = report.filename.replace(/\.[^.]+$/, '');
        if (kind === 'dax') downloadText(await ReverseService.exportDax(report.report_id), `${stem}-migrated-measures.dax`);
        else downloadText(JSON.stringify(await ReverseService.exportBim(report.report_id), null, 2), `${stem}-migrated-model.bim`, 'application/json');
      } catch (exception) {
        setActionError(describe(exception));
      } finally {
        setWorking(null);
      }
    },
    [report]
  );

  return { working, outcome, actionError, check: () => submit(true), apply: () => submit(false), exportAs };
}
