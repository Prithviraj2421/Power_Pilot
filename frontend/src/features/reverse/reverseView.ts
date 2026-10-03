import type {
  LayoutKind,
  ReverseCell,
  ReverseEvidence,
  ReverseSheetLayout,
  ReverseStatus,
  ReverseTarget,
} from '../../types';

export const STATUS_LABEL: Record<ReverseStatus, string> = {
  REPRODUCED: 'Reproduced',
  AMBIGUOUS: 'Several formulas fit',
  NOT_REPRODUCIBLE: 'Not reproduced',
  DERIVED: 'Calculated in the report',
};

/** Colour classes per status. The status is also always written out (label, aria-label), never colour alone. */
export const STATUS_STYLE: Record<ReverseStatus, string> = {
  REPRODUCED: 'border-emerald-500/50 bg-emerald-500/15 text-emerald-100',
  AMBIGUOUS: 'border-amber-500/50 bg-amber-500/15 text-amber-100',
  NOT_REPRODUCIBLE: 'border-red-500/60 bg-red-500/20 text-red-100',
  DERIVED: 'border-gray-500/40 bg-gray-500/15 text-gray-200',
};

export const STATUS_BADGE: Record<ReverseStatus, 'success' | 'warning' | 'danger' | 'info'> = {
  REPRODUCED: 'success',
  AMBIGUOUS: 'warning',
  NOT_REPRODUCIBLE: 'danger',
  DERIVED: 'info',
};

export const EVIDENCE_TEXT: Record<ReverseEvidence, string> = {
  strong: 'Strong evidence',
  moderate: 'Moderate evidence',
  weak: 'Weak evidence',
};

/** A number the way the report would print it: same decimals, with % or the unit. */
export function formatValue(value: number | null, target: Pick<ReverseTarget, 'unit' | 'decimals_shown'>, extraDecimals = 0): string {
  if (value === null || !Number.isFinite(value)) return '—';
  const decimals = Math.max(0, target.decimals_shown + extraDecimals);
  if (target.unit === 'percent') return `${(value * 100).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}%`;
  return value.toLocaleString('en-US', { minimumFractionDigits: Math.min(decimals, 2), maximumFractionDigits: Math.max(decimals, 2) });
}

export function describeCell(cell: ReverseCell): string {
  const place = [...cell.target.row_labels, ...cell.target.col_labels].join(' · ');
  return `${cell.target.sheet} ${cell.target.cell_ref}${place ? ` (${place})` : ''}: ${STATUS_LABEL[cell.status].toLowerCase()}`;
}

export type GridRow = { index: number; cells: (ReverseSheetLayout['cells'][number] | null)[] };

/** The sheet as rows of cells, ready to draw. Rows with nothing in them are kept as spacing between tables. */
export function gridRows(sheet: ReverseSheetLayout): GridRow[] {
  const rows: GridRow[] = Array.from({ length: sheet.rows }, (_, index) => ({ index, cells: Array(sheet.cols).fill(null) }));
  for (const cell of sheet.cells) {
    if (rows[cell.row]) rows[cell.row].cells[cell.col] = cell;
  }
  return rows;
}

export const KIND_STYLE: Record<LayoutKind, string> = {
  title: 'font-bold text-white',
  header: 'font-semibold text-gray-200 bg-white/5',
  label: 'font-medium text-gray-200',
  value: '',
  derived: '',
  other: 'text-gray-400',
};

export function downloadText(content: string, filename: string, type = 'text/plain'): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
