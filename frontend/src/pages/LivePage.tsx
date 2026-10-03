import React from 'react';
import { PlugZap, RefreshCw, Trash2 } from 'lucide-react';
import { PageContainer } from '../components/layout/PageContainer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { KpiPicker } from '../features/live/components/KpiPicker';
import { ApplyOutcome } from '../features/live/components/ApplyOutcome';
import { TablePicker } from '../features/live/components/TablePicker';
import { launchedModel } from '../features/live/liveSession';
import { useLiveModel } from '../features/live/useLiveModel';

export const LivePage: React.FC = () => {
  const live = useLiveModel();
  const { server } = launchedModel();

  if (live.phase === 'loading') {
    return (
      <PageContainer>
        <div className="mx-auto flex max-w-2xl flex-col items-center gap-4 py-24">
          <LoadingSpinner />
          <p className="text-sm text-gray-400">Connecting to your open Power BI model…</p>
        </div>
      </PageContainer>
    );
  }

  if (live.phase === 'not_launched' || live.phase === 'unauthorized' || live.phase === 'disconnected') {
    const title =
      live.phase === 'disconnected'
        ? "Can't reach your Power BI model"
        : live.phase === 'unauthorized'
          ? 'Open PowerPilot from Power BI Desktop'
          : 'PowerPilot is not attached to a model';
    return (
      <PageContainer>
        <div className="mx-auto max-w-2xl py-16">
          <EmptyState
            title={title}
            description={live.error ?? 'Something went wrong.'}
            icon={<PlugZap className="h-12 w-12 text-gray-500" />}
            action={
              live.phase === 'disconnected' ? (
                <Button onClick={() => void live.refresh()} leftIcon={<RefreshCw className="h-4 w-4" />}>
                  Try again
                </Button>
              ) : undefined
            }
          />
        </div>
      </PageContainer>
    );
  }

  const status = live.status!;
  const selectedCount = live.selectedKpis.size;

  return (
    <PageContainer>
      <div className="mx-auto max-w-4xl space-y-6 py-8">
        <header>
          <h1 className="text-2xl font-bold text-white">PowerPilot for Power BI</h1>
          <p className="mt-1 text-sm text-gray-400">
            Connected to your open model{server ? <> on <code className="text-gray-300">{server}</code></> : null}.
            PowerPilot reads your tables, checks each KPI against Power BI's own engine, and adds only the ones that
            match.
          </p>
        </header>

        <TablePicker
          status={status}
          selected={live.selectedTables}
          analyzing={live.analyzing}
          onToggle={live.toggleTable}
          onAnalyze={() => void live.analyze()}
        />

        {live.actionError && (
          <Card className="border-red-500/30 p-4 text-sm text-red-300" role="alert">
            {live.actionError}
          </Card>
        )}

        {live.analysis && (
          <>
            {live.analysis.skipped.length > 0 && (
              <Card className="p-4 text-xs text-gray-400">
                Skipped: {live.analysis.skipped.map((s) => `${s.table} (${s.reason})`).join('; ')}
              </Card>
            )}

            {live.analysis.tables.map((table) => (
              <KpiPicker key={table.dataset_id} table={table} selected={live.selectedKpis} onToggle={live.toggleKpi} />
            ))}

            <Card className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm text-gray-300">
                  {selectedCount} selected
                  <button type="button" className="ml-3 text-xs text-primary hover:underline" onClick={live.selectAllWritable} disabled={live.writableCount === 0}>
                    Select all verified
                  </button>
                  {selectedCount > 0 && (
                    <button type="button" className="ml-3 text-xs text-gray-400 hover:underline" onClick={live.clearSelection}>
                      Clear
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={() => void live.check()} disabled={selectedCount === 0 || live.working !== null} isLoading={live.working === 'check'}>
                    Check against Power BI
                  </Button>
                  <Button onClick={() => void live.apply()} disabled={selectedCount === 0 || live.working !== null} isLoading={live.working === 'apply'}>
                    Add {selectedCount > 0 ? selectedCount : ''} to my report
                  </Button>
                </div>
              </div>
            </Card>

            {live.outcome && <ApplyOutcome outcome={live.outcome} />}

            <div className="flex justify-end">
              <Button variant="ghost" size="sm" onClick={() => void live.forget()} leftIcon={<Trash2 className="h-4 w-4" />}>
                Forget this model's data
              </Button>
            </div>
          </>
        )}
      </div>
    </PageContainer>
  );
};
