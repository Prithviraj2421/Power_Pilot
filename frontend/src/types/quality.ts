export type QualityGrade = 'A+' | 'A' | 'B' | 'C' | 'D' | 'F';

export type IssueSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface QualityIssue {
  column: string;
  issue_type: string;
  description: string;
  affected_count: number;
  affected_percentage: number;
  severity: IssueSeverity;
  recommended_treatment: string;
}

export interface ColumnQualityScore {
  column_name: string;
  completeness: number;
  consistency: number;
  validity: number;
  uniqueness: number;
  overall_score: number;
}

export interface DatasetQualityReport {
  dataset_name: string;
  overall_score: number;
  grade: QualityGrade;
  grade_explanation: string;
  total_issues_count: number;
  column_scores: ColumnQualityScore[];
  detected_issues: QualityIssue[];
}

export interface AuditTrailEntry {
  column_name: string;
  action_type: string;
  before_sample: string;
  after_sample: string;
  rows_affected: number;
}

export interface DataPreparationReport {
  dataset_name: string;
  original_rows: number;
  cleaned_rows: number;
  rows_removed: number;
  total_actions_count: number;
  audit_trail: AuditTrailEntry[];
  summary_notes: string[];
}
