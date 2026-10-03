/** Types for "Prove-It Migration": reverse-engineering a legacy report against the data. */

export type ReverseStatus = 'REPRODUCED' | 'AMBIGUOUS' | 'NOT_REPRODUCIBLE' | 'DERIVED';
export type ReverseEvidence = 'strong' | 'moderate' | 'weak';
export type ReverseBasis = 'raw' | 'cleaned';
export type LayoutKind = 'title' | 'header' | 'label' | 'value' | 'derived' | 'other';

export interface ReverseTarget {
  id: string;
  sheet: string;
  cell_ref: string;
  /** The number in real units: 12.5% is 0.125. */
  value: number;
  shown_text: string;
  decimals_shown: number;
  unit: 'number' | 'percent' | 'currency';
  row_labels: string[];
  col_labels: string[];
  context_labels: string[];
}

export interface ReverseAlternative {
  formula: string;
  dax: string | null;
  value: number;
}

export interface ReverseClosest {
  value: number;
  formula: string;
  /** What the report shows minus what the rule gives. */
  difference: number;
  relative: number | null;
}

export interface ReverseDerivedCheck {
  consistent: boolean;
  expected: number | null;
  explanation: string;
  data_value: number | null;
  matches_data: boolean | null;
}

export interface ReverseCell {
  id: string;
  status: ReverseStatus;
  basis: ReverseBasis | null;
  target: ReverseTarget;
  formula: string;
  dax: string | null;
  recomputed: number | null;
  exact: boolean;
  evidence: ReverseEvidence | null;
  reasons: string[];
  alternatives: ReverseAlternative[];
  closest: ReverseClosest | null;
  hint: string | null;
  notes: string[];
  derived_check: ReverseDerivedCheck | null;
  /** Proven on the raw data, so it may become a measure. */
  writable: boolean;
  proposed_by: string | null;
}

export interface ReverseLayoutCell {
  ref: string;
  row: number;
  col: number;
  text: string;
  kind: LayoutKind;
  target_id: string | null;
}

export interface ReverseSheetLayout {
  name: string;
  rows: number;
  cols: number;
  cells: ReverseLayoutCell[];
}

export interface ReverseSummary {
  cells: number;
  reproduced: number;
  ambiguous: number;
  not_reproducible: number;
  derived: number;
  percent_reproduced: number;
  suspected_errors: number;
  seconds: number;
  budget_exhausted: boolean;
}

export interface PlannedMeasure {
  id: string;
  name: string;
  kind: 'single' | 'grouped';
  dax: string;
  formula: string;
  cells: string[];
  notes: string[];
  display_folder: string;
}

export interface MigrationPlan {
  table: string;
  measures: PlannedMeasure[];
  not_writable: { cell: string; reason: string }[];
}

export interface ReverseReport {
  report_id: string;
  filename: string;
  table: string;
  rows_analysed: number;
  rows_total: number;
  sampled: boolean;
  live: boolean;
  dataset_id: string | null;
  plan: MigrationPlan | null;
  summary: ReverseSummary;
  warnings: string[];
  cells: ReverseCell[];
  layout: ReverseSheetLayout[];
}
