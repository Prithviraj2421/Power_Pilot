import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { ReverseSummary } from '../../../types';

const PILL = 'rounded-full border px-3 py-1 text-xs font-semibold';

export interface SummaryBarProps {
  summary: ReverseSummary;
  warnings: string[];
  filename: string;
}

export const SummaryBar: React.FC<SummaryBarProps> = ({ summary, warnings, filename }) => {
  const fromData = summary.reproduced + summary.ambiguous + summary.not_reproducible;
  return (
    <Card className="space-y-3 p-5" data-testid="reverse-summary">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-bold text-white">
          {summary.percent_reproduced.toLocaleString('en-US', { maximumFractionDigits: 1 })}% reproduced
        </h3>
        <span className="text-xs text-gray-400">
          {filename} · {summary.cells} numbers · {summary.seconds.toLocaleString('en-US', { maximumFractionDigits: 1 })} s
        </span>
      </div>
      <p className="text-sm text-gray-300">
        {summary.reproduced} of the {fromData} numbers that come from the data were proven by recomputing them.
        {summary.suspected_errors > 0 && (
          <strong className="text-red-300">
            {' '}
            {summary.suspected_errors} suspected {summary.suspected_errors === 1 ? 'mistake' : 'mistakes'} to check.
          </strong>
        )}
      </p>
      <ul className="flex flex-wrap gap-2" aria-label="Results by status">
        <li className={`${PILL} border-emerald-500/50 bg-emerald-500/15 text-emerald-100`}>{summary.reproduced} reproduced</li>
        <li className={`${PILL} border-amber-500/50 bg-amber-500/15 text-amber-100`}>{summary.ambiguous} several formulas fit</li>
        <li className={`${PILL} border-red-500/60 bg-red-500/20 text-red-100`}>{summary.not_reproducible} not reproduced</li>
        <li className={`${PILL} border-gray-500/40 bg-gray-500/15 text-gray-200`}>{summary.derived} calculated in the report</li>
      </ul>
      {summary.budget_exhausted && (
        <p className="flex items-center gap-2 text-xs text-amber-300" role="note">
          <AlertTriangle className="h-4 w-4" /> The time limit ran out before every formula could be tried, so some numbers may have been missed.
        </p>
      )}
      {warnings.map((warning) => (
        <p key={warning} className="text-xs text-amber-300" role="note">
          {warning}
        </p>
      ))}
    </Card>
  );
};
