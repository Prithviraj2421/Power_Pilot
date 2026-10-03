import { useCallback, useEffect, useMemo, useState } from 'react';
import { LiveApiError, LiveService } from '../../services/liveService';
import { ApplyResponse, LiveAnalysis, LiveKpi, LiveStatus, LiveTableAnalysis } from '../../types';
import { captureToken } from './liveSession';

export type LivePhase = 'loading' | 'not_launched' | 'unauthorized' | 'disconnected' | 'ready';

export interface LiveModelState {
  phase: LivePhase;
  error: string | null;
  status: LiveStatus | null;
  selectedTables: Set<string>;
  analysis: LiveAnalysis | null;
  analyzing: boolean;
  selectedKpis: Set<string>;
  working: 'check' | 'apply' | null;
  outcome: ApplyResponse | null;
  actionError: string | null;
}

/** A KPI can be added when it was verified, its table was read in full, and its name is free. */
export function isWritable(table: LiveTableAnalysis, kpi: LiveKpi): boolean {
  return table.can_write && kpi.verified && !kpi.name_taken;
}

/** The table most likely to be the fact table: the one with the most rows. */
export function largestTable(status: LiveStatus): string | null {
  const sorted = [...status.tables].sort((a, b) => b.rows - a.rows);
  return sorted[0]?.name ?? null;
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong.';
}

export function useLiveModel() {
  const [token] = useState<string | null>(() => captureToken());
  const [state, setState] = useState<LiveModelState>({
    phase: 'loading',
    error: null,
    status: null,
    selectedTables: new Set(),
    analysis: null,
    analyzing: false,
    selectedKpis: new Set(),
    working: null,
    outcome: null,
    actionError: null,
  });

  const patch = useCallback((changes: Partial<LiveModelState>) => setState((s) => ({ ...s, ...changes })), []);

  const refresh = useCallback(async () => {
    if (!token) {
      patch({
        phase: 'unauthorized',
        error: "This page was not opened from Power BI Desktop. Open a report, then choose PowerPilot on the External Tools ribbon.",
      });
      return;
    }
    patch({ phase: 'loading', error: null });
    try {
      const status = await LiveService.status(token);
      if (!status.connected) {
        patch({ phase: 'disconnected', status, error: status.error });
        return;
      }
      const first = largestTable(status);
      patch({ phase: 'ready', status, error: null, selectedTables: first ? new Set([first]) : new Set() });
    } catch (error) {
      const status = error instanceof LiveApiError ? error.status : undefined;
      if (status === 409) patch({ phase: 'not_launched', error: describe(error) });
      else if (status === 401) {
        patch({ phase: 'unauthorized', error: 'This PowerPilot session has expired. Choose PowerPilot on the External Tools ribbon again.' });
      } else patch({ phase: 'disconnected', error: describe(error) });
    }
  }, [token, patch]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const toggleTable = useCallback((name: string) => {
    setState((s) => {
      const next = new Set(s.selectedTables);
      if (!next.delete(name)) next.add(name);
      return { ...s, selectedTables: next };
    });
  }, []);

  const analyze = useCallback(async () => {
    if (!token) return;
    patch({ analyzing: true, actionError: null, outcome: null });
    try {
      const analysis = await LiveService.analyze(token, [...state.selectedTables]);
      patch({ analysis, selectedKpis: new Set(), analyzing: false });
    } catch (error) {
      patch({ analyzing: false, actionError: describe(error) });
    }
  }, [token, state.selectedTables, patch]);

  const toggleKpi = useCallback((id: string) => {
    setState((s) => {
      const next = new Set(s.selectedKpis);
      if (!next.delete(id)) next.add(id);
      return { ...s, selectedKpis: next };
    });
  }, []);

  const writableIds = useMemo(
    () => (state.analysis?.tables ?? []).flatMap((t) => t.kpis.filter((k) => isWritable(t, k)).map((k) => k.id)),
    [state.analysis]
  );

  const selectAllWritable = useCallback(() => patch({ selectedKpis: new Set(writableIds) }), [patch, writableIds]);
  const clearSelection = useCallback(() => patch({ selectedKpis: new Set() }), [patch]);

  const submit = useCallback(
    async (dryRun: boolean) => {
      if (!token || !state.analysis) return;
      const items = state.analysis.tables.flatMap((t) =>
        t.kpis.filter((k) => state.selectedKpis.has(k.id)).map((k) => ({ table: t.table, kpi_id: k.id }))
      );
      if (items.length === 0) return;
      patch({ working: dryRun ? 'check' : 'apply', actionError: null, outcome: null });
      try {
        const outcome = await LiveService.apply(token, items, dryRun);
        if (dryRun || !outcome.saved) {
          patch({ outcome, working: null });
          return;
        }
        // The response says which measures now exist, so mark them taken without re-reading any table.
        const written = new Set(outcome.results.filter((r) => r.status === 'written').map((r) => r.kpi_id));
        const analysis = {
          ...state.analysis,
          tables: state.analysis.tables.map((t) => ({
            ...t,
            kpis: t.kpis.map((k) => (written.has(k.id) ? { ...k, name_taken: true, added_by_powerpilot: true } : k)),
          })),
        };
        patch({ outcome, working: null, analysis, selectedKpis: new Set() });
      } catch (error) {
        patch({ working: null, actionError: describe(error) });
      }
    },
    [token, state.analysis, state.selectedKpis, patch]
  );

  const forget = useCallback(async () => {
    const tables = state.analysis?.tables ?? [];
    try {
      await Promise.all(tables.map((t) => LiveService.forget(t.dataset_id)));
      patch({ analysis: null, selectedKpis: new Set(), outcome: null, actionError: null });
    } catch (error) {
      patch({ actionError: describe(error) });
    }
  }, [state.analysis, patch]);

  return {
    ...state,
    token,
    writableCount: writableIds.length,
    refresh,
    toggleTable,
    analyze,
    toggleKpi,
    selectAllWritable,
    clearSelection,
    check: () => submit(true),
    apply: () => submit(false),
    forget,
  };
}
