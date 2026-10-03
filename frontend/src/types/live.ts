/** Types for PowerPilot running as a Power BI Desktop External Tool (the `/live` page). */

export interface LiveTableInfo {
  name: string;
  columns: number;
  rows: number;
  /** True when the table is larger than the row limit, so only a sample would be read. */
  will_be_sampled: boolean;
}

export interface LiveStatus {
  connected: boolean;
  error: string | null;
  max_rows: number;
  tables: LiveTableInfo[];
}

export interface LiveKpi {
  id: string;
  name: string;
  formula: string | null;
  computed_value: number | null;
  verified: boolean;
  /** A baseline computed from the model's data, an explicit example target, or a note that there is none. */
  baseline: string | null;
  note: string;
  /** A measure with this name already exists in the open model. */
  name_taken: boolean;
  added_by_powerpilot: boolean;
}

export interface LiveRejectedKpi {
  name: string;
  reason: string;
}

export interface LiveTableAnalysis {
  table: string;
  dataset_id: string;
  rows_read: number;
  rows_total: number;
  sampled: boolean;
  /** False for a sampled table: its KPIs cannot be checked against the full model. */
  can_write: boolean;
  domain: string;
  kpis: LiveKpi[];
  rejected: LiveRejectedKpi[];
}

export interface LiveAnalysis {
  max_rows: number;
  tables: LiveTableAnalysis[];
  skipped: { table: string; reason: string }[];
}

export type ApplyStatus = 'written' | 'verified' | 'refused' | 'skipped_exists' | 'failed';

export interface ApplyResult {
  table: string;
  kpi_id: string;
  name: string;
  status: ApplyStatus;
  reason: string;
  engine_value: number | null;
  computed_value: number | null;
}

export interface ApplyResponse {
  dry_run: boolean;
  saved: boolean;
  results: ApplyResult[];
  reminder: string | null;
}

export interface ApplySelection {
  table: string;
  kpi_id: string;
}
