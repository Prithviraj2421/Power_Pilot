import React from 'react';
import { Badge } from '../../../components/ui/Badge';
import { Card } from '../../../components/ui/Card';
import { ReverseCell } from '../../../types';
import { EVIDENCE_TEXT, STATUS_BADGE, STATUS_LABEL, formatValue } from '../reverseView';

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <section className="space-y-1">
    <h5 className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{title}</h5>
    {children}
  </section>
);

const Code: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-surface p-2 font-mono text-xs text-gray-200">{children}</pre>
);

export const CellDetailPanel: React.FC<{ cell: ReverseCell | null }> = ({ cell }) => {
  if (!cell) {
    return (
      <Card className="p-5 text-sm text-gray-400" data-testid="cell-detail-empty">
        Click a number in the report to see the formula behind it, how it was proven, or why it could not be.
      </Card>
    );
  }
  const t = cell.target;
  const place = [...t.row_labels, ...t.col_labels].join(' · ');
  const gap = cell.closest ? formatValue(Math.abs(cell.closest.difference), t, 0) : null;
  const direction = cell.closest && cell.closest.difference < 0 ? 'lower' : 'higher';

  return (
    <Card className="space-y-4 p-5" role="region" aria-label="Cell details" data-testid="cell-detail">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs text-gray-400">
            {t.sheet} · {t.cell_ref}
            {place ? ` · ${place}` : ''}
          </p>
          <p className="font-mono text-2xl font-bold text-white">{t.shown_text}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={STATUS_BADGE[cell.status]} showDot={false}>
            {STATUS_LABEL[cell.status]}
          </Badge>
          {cell.evidence && (
            <Badge variant="primary" showDot={false}>
              {EVIDENCE_TEXT[cell.evidence]}
            </Badge>
          )}
        </div>
      </header>

      {cell.formula && (
        <Section title={cell.status === 'DERIVED' ? 'How the report calculated it' : 'The formula'}>
          <p className="text-sm text-gray-100">{cell.formula}</p>
          {cell.dax && <Code>{cell.dax}</Code>}
        </Section>
      )}

      {cell.recomputed !== null && cell.status !== 'DERIVED' && (
        <Section title="Recomputed on the data">
          <p className="font-mono text-sm text-gray-100">
            {formatValue(cell.recomputed, t, 2)}{' '}
            <span className="text-xs text-gray-400">
              (report shows {t.shown_text}
              {cell.exact ? ', exact match' : ''})
            </span>
          </p>
        </Section>
      )}

      {cell.basis === 'cleaned' && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-200" role="note">
          This only matches the cleaned data, not the raw table, so it cannot be added to Power BI as it is.
        </p>
      )}

      {cell.status === 'NOT_REPRODUCIBLE' && cell.hint && (
        <Section title="What probably happened">
          <p className="rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-sm text-red-100" data-testid="cell-hint">
            {cell.hint}
          </p>
          {cell.closest && (
            <p className="text-xs text-gray-300">
              Closest: <span className="font-mono">{formatValue(cell.closest.value, t, 2)}</span> from &ldquo;{cell.closest.formula}&rdquo;
              {gap ? ` (the report is ${gap} ${direction})` : ''}.
            </p>
          )}
        </Section>
      )}

      {cell.derived_check && (
        <Section title="Checked against its own parts">
          <p className={cell.derived_check.consistent ? 'text-sm text-gray-200' : 'text-sm text-red-200'}>{cell.derived_check.explanation}</p>
          {cell.derived_check.matches_data === false && cell.hint && <p className="text-sm text-amber-200">{cell.hint}</p>}
          {cell.derived_check.matches_data === true && <p className="text-xs text-gray-400">It also matches what the data gives.</p>}
        </Section>
      )}

      {cell.alternatives.length > 0 && (
        <Section title={cell.status === 'AMBIGUOUS' ? 'The formulas that all give this number' : 'Other formulas that also give this number'}>
          <ul className="space-y-1 text-sm text-gray-200">
            {cell.alternatives.map((a) => (
              <li key={a.formula} className="rounded-lg border border-white/10 bg-surface px-2 py-1">
                {a.formula}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {cell.reasons.length > 0 && (
        <Section title="Why PowerPilot says so">
          <ul className="list-disc space-y-1 pl-4 text-xs text-gray-300">
            {cell.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </Section>
      )}

      {cell.notes.length > 0 && (
        <ul className="space-y-1 text-xs text-gray-400">
          {cell.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </Card>
  );
};
