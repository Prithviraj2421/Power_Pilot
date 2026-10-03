import React, { useMemo } from 'react';
import { Card } from '../../../components/ui/Card';
import { cn } from '../../../utils/cn';
import { ReverseCell, ReverseReport } from '../../../types';
import { KIND_STYLE, STATUS_LABEL, STATUS_STYLE, describeCell, gridRows } from '../reverseView';

export interface ReportGridProps {
  report: ReverseReport;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const LEGEND: { status: keyof typeof STATUS_STYLE; text: string }[] = [
  { status: 'REPRODUCED', text: 'Reproduced' },
  { status: 'AMBIGUOUS', text: 'Several formulas fit' },
  { status: 'NOT_REPRODUCIBLE', text: 'Not reproduced' },
  { status: 'DERIVED', text: 'Calculated in the report' },
];

/** The report drawn back as it looked, each number coloured by what PowerPilot found. Click a number for details. */
export const ReportGrid: React.FC<ReportGridProps> = ({ report, selectedId, onSelect }) => {
  const byId = useMemo(() => new Map<string, ReverseCell>(report.cells.map((c) => [c.id, c])), [report.cells]);

  return (
    <Card className="space-y-4 p-5" data-testid="report-grid">
      <ul className="flex flex-wrap gap-3 text-xs text-gray-300" aria-label="Colour key">
        {LEGEND.map(({ status, text }) => (
          <li key={status} className="flex items-center gap-1.5">
            <span className={cn('inline-block h-3 w-3 rounded border', STATUS_STYLE[status])} aria-hidden />
            {text}
          </li>
        ))}
      </ul>

      {report.layout.map((sheet) => (
        <div key={sheet.name} className="overflow-x-auto">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">{sheet.name}</h4>
          <table className="border-separate border-spacing-1 text-sm" aria-label={`Report ${sheet.name}`}>
            <tbody>
              {gridRows(sheet).map((row) => (
                <tr key={row.index}>
                  {row.cells.map((cell, col) => {
                    if (!cell) return <td key={col} className="h-8 min-w-[3rem]" />;
                    const result = cell.target_id ? byId.get(cell.target_id) : undefined;
                    if (!result) {
                      return (
                        <td key={col} className={cn('whitespace-nowrap px-2 py-1 align-middle', KIND_STYLE[cell.kind])} data-kind={cell.kind}>
                          {cell.text}
                        </td>
                      );
                    }
                    const selected = selectedId === result.id;
                    return (
                      <td key={col} className="p-0">
                        <button
                          type="button"
                          data-testid={`cell-${result.id}`}
                          data-status={result.status}
                          aria-label={describeCell(result)}
                          aria-pressed={selected}
                          title={STATUS_LABEL[result.status]}
                          onClick={() => onSelect(result.id)}
                          className={cn(
                            'w-full whitespace-nowrap rounded-md border px-2 py-1 text-right font-mono transition focus:outline-none focus:ring-2 focus:ring-primary',
                            STATUS_STYLE[result.status],
                            result.basis === 'cleaned' && 'border-dashed',
                            selected && 'ring-2 ring-primary'
                          )}
                        >
                          {cell.text}
                          {result.basis === 'cleaned' && (
                            <span className="ml-1 text-[10px]" aria-hidden>
                              *
                            </span>
                          )}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {report.cells.some((c) => c.basis === 'cleaned') && (
        <p className="text-xs text-gray-400">* Matches the cleaned data, not the raw table (dashed outline).</p>
      )}
    </Card>
  );
};
