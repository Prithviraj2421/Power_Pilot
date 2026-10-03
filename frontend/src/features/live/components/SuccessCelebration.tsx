import React from 'react';
import { ApplyResult } from '../../../types';

export interface SuccessCelebrationProps {
  written: ApplyResult[];
  reminder: string | null;
}

/** Shown after measures were really added to the open model. Lists exactly what was written. */
export const SuccessCelebration: React.FC<SuccessCelebrationProps> = ({ written, reminder }) => (
  <div
    role="status"
    data-testid="success-celebration"
    className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-6 text-center"
  >
    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 animate-pop-in">
      <svg viewBox="0 0 24 24" className="h-9 w-9 text-emerald-400" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path className="animate-draw-check" d="M5 13l4 4L19 7" />
      </svg>
    </div>
    <h3 className="text-lg font-bold text-white">
      {written.length === 1 ? '1 measure added to your report' : `${written.length} measures added to your report`}
    </h3>
    <p className="mt-1 text-xs text-gray-400">
      Find them in the <span className="font-semibold text-gray-200">PowerPilot</span> display folder of the Data pane.
    </p>

    <ul className="mx-auto mt-4 max-w-md space-y-2 text-left">
      {written.map((r, index) => (
        <li
          key={r.kpi_id}
          className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-surface px-3 py-2 text-sm animate-rise-in"
          style={{ animationDelay: `${0.35 + index * 0.08}s` }}
        >
          <span className="font-medium text-white">{r.name}</span>
          <span className="text-xs text-gray-400">{r.table}</span>
        </li>
      ))}
    </ul>

    {reminder && <p className="mt-4 text-xs font-semibold text-amber-300">{reminder}</p>}
  </div>
);
