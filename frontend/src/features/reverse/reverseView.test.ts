import { describe, expect, it } from 'vitest';
import { describeCell, formatValue, gridRows } from './reverseView';
import { firstToInspect } from './useReverse';
import { cell, report } from './fixtures';

describe('formatValue', () => {
  it('prints a percent the way the report does', () => {
    expect(formatValue(0.125, { unit: 'percent', decimals_shown: 1 })).toBe('12.5%');
    expect(formatValue(0.103362, { unit: 'percent', decimals_shown: 1 }, 2)).toBe('10.336%');
  });

  it('keeps at least the report decimals for money and groups thousands', () => {
    expect(formatValue(1234.5, { unit: 'number', decimals_shown: 2 })).toBe('1,234.50');
    expect(formatValue(1234.5678, { unit: 'currency', decimals_shown: 2 }, 2)).toBe('1,234.5678');
    expect(formatValue(12, { unit: 'number', decimals_shown: 0 })).toBe('12');
  });

  it('shows a dash for nothing', () => {
    expect(formatValue(null, { unit: 'number', decimals_shown: 0 })).toBe('—');
    expect(formatValue(Number.NaN, { unit: 'number', decimals_shown: 0 })).toBe('—');
  });
});

describe('gridRows', () => {
  it('places each cell at its row and column, leaving gaps empty', () => {
    const rows = gridRows(report().layout[0]);
    expect(rows).toHaveLength(5);
    expect(rows[2].cells[1]?.text).toBe('40,194.25');
    expect(rows[3].cells[2]).toBeNull();
    expect(rows[0].cells.filter(Boolean)).toHaveLength(1);
  });

  it('ignores cells outside the sheet rather than crashing', () => {
    const sheet = { name: 'S', rows: 1, cols: 1, cells: [{ ref: 'Z9', row: 8, col: 0, text: 'x', kind: 'other' as const, target_id: null }] };
    expect(gridRows(sheet)[0].cells).toEqual([null]);
  });
});

describe('describeCell and firstToInspect', () => {
  it('writes the status out in words for screen readers', () => {
    expect(describeCell(cell('S!C3', { status: 'NOT_REPRODUCIBLE' }))).toBe('S C3 (West · 2024): not reproduced');
  });

  it('opens on the first number that needs a look: not reproduced, then ambiguous', () => {
    expect(firstToInspect(report())).toBe('S!C3');
    const noRed = report({ cells: report().cells.filter((c) => c.status !== 'NOT_REPRODUCIBLE') });
    expect(firstToInspect(noRed)).toBe('S!B4');
    expect(firstToInspect(report({ cells: [cell('S!B3')] }))).toBeNull();
  });
});
