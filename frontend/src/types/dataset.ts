import { MasterIntelligenceResult } from './master';

export interface ColumnStatistics {
  missing_count: number;
  unique_count: number;
  min?: number;
  max?: number;
  mean?: number;
  std?: number;
  median?: number;
  sample_values?: (string | number | boolean)[];
}

export interface ColumnProfile {
  name: string;
  physical_type: string;
  nullable: boolean;
  unique: boolean;
  identifier: boolean;
  missing_count: number;
  unique_count: number;
  semantic_type?: string;
  sample_values: (string | number | boolean)[];
  confidence: number;
  metadata?: Record<string, any>;
  statistics?: ColumnStatistics;
}

export interface DatasetProfile {
  dataset_name: string;
  total_rows: number;
  total_columns: number;
  detected_domain: string;
  domain_confidence?: number;
  columns: ColumnProfile[];
}

/**
 * Durable metadata for a dataset registered in the backend registry.
 * `dataset_id` is the handle every downstream operation uses instead of
 * re-uploading the CSV.
 */
export interface DatasetRecord {
  dataset_id: string;
  filename: string;
  size_bytes: number;
  content_sha256: string;
  original_rows: number;
  total_rows: number;
  total_columns: number;
  rows_removed_by_cleaning: number;
  detected_domain: string;
  domain_confidence: number;
  quality_grade: string;
  quality_score: number;
  quality_issues_count: number;
  created_at: string;
  last_accessed_at: string;
  /** How the upload was decoded and split, e.g. "cp1252, semicolon-separated". */
  source_encoding: string;
  source_delimiter: string;
  source_format: string;
  /** True when the file was plain UTF-8 with commas, i.e. nothing worth saying. */
  read_with_defaults: boolean;
}

export interface AnalyzeCsvApiResponse {
  status: string;
  dataset_id: string;
  dataset: DatasetRecord;
  result: MasterIntelligenceResult;
  processing_time_ms?: number;
  dataset_name?: string;
  detected_domain?: string;
}

/** Response of GET /api/v1/datasets/:id/result — used to restore a workspace. */
export interface DatasetResultApiResponse {
  status: string;
  dataset: DatasetRecord;
  result: MasterIntelligenceResult;
}

/** Response of GET /api/v1/datasets — analysis history. */
export interface DatasetListApiResponse {
  status: string;
  total: number;
  limit: number;
  offset: number;
  datasets: DatasetRecord[];
}
