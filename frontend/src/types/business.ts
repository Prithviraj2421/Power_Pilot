import { DatasetDomain } from './domain';

export interface BusinessProfile {
  domain: DatasetDomain;
  domain_confidence: number;
  business_context: string;
  executive_summary: string;
  primary_kpis: string[];
  secondary_kpis: string[];
  dimensions: string[];
  measures: string[];
  business_questions: string[];
  suggested_charts: string[];
  suggested_dashboard_layout: string[];
  suggested_filters: string[];
  time_intelligence: string[];
  recommended_insights: string[];
  relationships: string[];
  data_quality_notes: string[];
}
