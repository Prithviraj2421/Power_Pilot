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

export interface AnalyzeCsvApiResponse {
  status: string;
  result: MasterIntelligenceResult;
  processing_time_ms?: number;
  dataset_name?: string;
  detected_domain?: string;
}
