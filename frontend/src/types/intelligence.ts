import { DatasetDomain } from './domain';

export interface QualityReport {
  overall_score: number;
  completeness_score: number;
  uniqueness_score: number;
  validity_score: number;
  total_issues: number;
  issues: string[];
}

export interface StatisticalSummary {
  total_rows: number;
  numeric_columns_count: number;
  categorical_columns_count: number;
  date_columns_count: number;
  numeric_stats: Record<string, Record<string, number>>;
}

export interface CorrelationResult {
  column_a: string;
  column_b: string;
  coefficient: number;
  correlation_type: string;
  confidence: number;
  reasoning: string;
}

export interface TrendResult {
  date_column: string;
  metric_column: string;
  direction: "increasing" | "decreasing" | "stable" | "volatile";
  slope: number;
  r_squared: number;
  period_count: number;
  confidence: number;
  reasoning: string;
}

export interface OutlierReport {
  column_name: string;
  outlier_count: number;
  outlier_ratio: number;
  lower_bound: number;
  upper_bound: number;
  method: string;
  confidence: number;
  reasoning: string;
}

export interface PatternReport {
  pattern_name: string;
  description: string;
  affected_columns: string[];
  confidence: number;
  evidence: string[];
}

export interface BusinessAnomaly {
  anomaly_title: string;
  description: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  affected_dimension?: string;
  affected_metric?: string;
  confidence: number;
  evidence: string[];
}

export interface InsightCandidate {
  title: string;
  category: string;
  importance_score: number;
  evidence: string[];
}

export interface DataIntelligenceReport {
  quality_report: QualityReport;
  statistical_summary: StatisticalSummary;
  correlations: CorrelationResult[];
  trends: TrendResult[];
  outliers: OutlierReport[];
  patterns: PatternReport[];
  business_anomalies: BusinessAnomaly[];
  insight_candidates: InsightCandidate[];
  domain: DatasetDomain;
}
