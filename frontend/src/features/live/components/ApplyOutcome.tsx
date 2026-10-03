import React from 'react';
import { Badge } from '../../../components/ui/Badge';
import { Card } from '../../../components/ui/Card';
import { ApplyResponse, ApplyStatus } from '../../../types';
import { SuccessCelebration } from './SuccessCelebration';

const LABEL: Record<ApplyStatus, { text: string; variant: 'success' | 'warning' | 'danger' | 'info' }> = {
  written: { text: 'Added', variant: 'success' },
  verified: { text: 'Matches Power BI', variant: 'success' },
  refused: { text: 'Not added', variant: 'danger' },
  skipped_exists: { text: 'Skipped', variant: 'warning' },
  failed: { text: 'Failed', variant: 'danger' },
};

const number = (value: number | null) =>
  value === null ? '—' : value.toLocaleString('en-US', { maximumFractionDigits: 6 });

export const ApplyOutcome: React.FC<{ outcome: ApplyResponse }> = ({ outcome }) => {
  const written = outcome.results.filter((r) => r.status === 'written');

  return (
    <div className="space-y-4" data-testid="apply-outcome">
      {!outcome.dry_run && written.length > 0 && <SuccessCelebration written={written} reminder={outcome.reminder} />}

      <Card className="p-6">
        <h3 className="mb-1 text-base font-bold text-white">
          {outcome.dry_run ? 'Check against Power BI' : 'What happened'}
        </h3>
        {outcome.dry_run && (
          <p className="mb-3 text-xs text-gray-400">Nothing was added. Power BI's own engine ran each measure.</p>
        )}
        <ul className="space-y-2">
          {outcome.results.map((r) => (
            <li key={`${r.kpi_id}`} className="rounded-xl border border-white/10 bg-surface p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-white">{r.name || r.kpi_id}</span>
                <Badge variant={LABEL[r.status].variant} showDot={false}>
                  {LABEL[r.status].text}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-gray-300">{r.reason}</p>
              {(r.engine_value !== null || r.computed_value !== null) && (
                <p className="mt-1 font-mono text-[11px] text-gray-500">
                  Power BI: {number(r.engine_value)} · PowerPilot: {number(r.computed_value)}
                </p>
              )}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
};
