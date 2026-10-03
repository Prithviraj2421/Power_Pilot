import type { ReverseCell, ReverseReport, ReverseTarget } from '../../types';

/** A small report in the shape the backend returns, for tests. */
export function target(id: string, overrides: Partial<ReverseTarget> = {}): ReverseTarget {
  const [sheet, cell_ref] = id.split('!');
  return {
    id,
    sheet,
    cell_ref,
    value: 100,
    shown_text: '100.00',
    decimals_shown: 2,
    unit: 'number',
    row_labels: ['West'],
    col_labels: ['2024'],
    context_labels: [],
    ...overrides,
  };
}

export function cell(id: string, overrides: Partial<ReverseCell> = {}): ReverseCell {
  return {
    id,
    status: 'REPRODUCED',
    basis: 'raw',
    target: target(id, overrides.target),
    formula: 'Sum of Sales where Region is West',
    dax: "CALCULATE(SUM('Orders'[Sales]), 'Orders'[Region] = \"West\")",
    recomputed: 100,
    exact: true,
    evidence: 'strong',
    reasons: ['1 formula(s) fit the 5-digit number'],
    alternatives: [],
    closest: null,
    hint: null,
    notes: [],
    derived_check: null,
    writable: true,
    proposed_by: null,
    ...overrides,
  };
}

export function report(overrides: Partial<ReverseReport> = {}): ReverseReport {
  const cells: ReverseCell[] = [
    cell('S!B3', { target: target('S!B3', { row_labels: ['Central'], shown_text: '40,194.25' }) }),
    cell('S!C3', {
      status: 'NOT_REPRODUCIBLE',
      basis: null,
      formula: '',
      dax: null,
      recomputed: null,
      exact: false,
      evidence: null,
      writable: false,
      target: target('S!C3', { row_labels: ['East'], shown_text: '16,097.19' }),
      hint: 'Two digits look swapped: the data gives 16,079.19 but the report shows 16,097.19.',
      closest: { value: 16079.19, formula: 'Sum of Sales where Region is East', difference: 18, relative: 0.001 },
      reasons: ['No formula reproduces this number.'],
    }),
    cell('S!B4', {
      status: 'AMBIGUOUS',
      writable: false,
      evidence: null,
      target: target('S!B4', { row_labels: ['Corporate'], col_labels: ['Customers'], shown_text: '6', decimals_shown: 0 }),
      formula: 'Number of different Customer ID where Segment is Corporate',
      alternatives: [{ formula: 'Number of different Customer Name where Segment is Corporate', dax: null, value: 6 }],
    }),
    cell('S!B5', {
      status: 'DERIVED',
      basis: null,
      evidence: null,
      writable: false,
      formula: 'Sum of the 4 numbers it totals',
      dax: null,
      target: target('S!B5', { row_labels: ['Total'], shown_text: '164,979.22' }),
      derived_check: { consistent: true, expected: 164979.22, explanation: 'Adding up the 4 numbers it totals gives 164,979.22, which matches.', data_value: null, matches_data: null },
    }),
  ];
  return {
    report_id: 'rep1',
    filename: 'legacy.xlsx',
    table: 'Orders',
    rows_analysed: 156,
    rows_total: 156,
    sampled: false,
    live: false,
    dataset_id: 'ds1',
    plan: {
      table: 'Orders',
      measures: [
        {
          id: 'rep1:total-sales',
          name: 'Total Sales',
          kind: 'grouped',
          dax: "SUM('Orders'[Sales])",
          formula: 'Sum of Sales',
          cells: ['S!B3', 'S!C3'],
          notes: ['Put Region and Year of Order Date on the visual and this one measure gives all 2 numbers.'],
          display_folder: 'PowerPilot\\Migrated',
        },
      ],
      not_writable: [],
    },
    summary: { cells: 4, reproduced: 1, ambiguous: 1, not_reproducible: 1, derived: 1, percent_reproduced: 33.3, suspected_errors: 1, seconds: 0.3, budget_exhausted: false },
    warnings: [],
    cells,
    layout: [
      {
        name: 'Summary',
        rows: 5,
        cols: 3,
        cells: [
          { ref: 'A1', row: 0, col: 0, text: 'Sales by Region', kind: 'title', target_id: null },
          { ref: 'A2', row: 1, col: 0, text: 'Region', kind: 'header', target_id: null },
          { ref: 'B2', row: 1, col: 1, text: '2024', kind: 'header', target_id: null },
          { ref: 'A3', row: 2, col: 0, text: 'Central', kind: 'label', target_id: null },
          { ref: 'B3', row: 2, col: 1, text: '40,194.25', kind: 'value', target_id: 'S!B3' },
          { ref: 'A4', row: 3, col: 0, text: 'East', kind: 'label', target_id: null },
          { ref: 'C3', row: 2, col: 2, text: '16,097.19', kind: 'value', target_id: 'S!C3' },
          { ref: 'B4', row: 3, col: 1, text: '6', kind: 'value', target_id: 'S!B4' },
          { ref: 'B5', row: 4, col: 1, text: '164,979.22', kind: 'derived', target_id: 'S!B5' },
        ],
      },
    ],
    ...overrides,
  };
}
