import { DatasetDomain } from './domain';
import { Priority } from './insight';

export interface KPIRecommendation {
  name: string;
  priority: Priority;
  confidence: number;
  reason: string;
  formula?: string | null;
  /** A baseline computed from the data, or an explicitly labelled example, or a note that there is none. */
  target_threshold?: string | null;
  business_impact?: string | null;
  /** The value of the KPI computed on the cleaned dataset. Present only when `verified`. */
  computed_value?: number | null;
  /** True when the KPI's columns exist, the DAX matches them, and the computed value is finite. */
  verified?: boolean;
  verification_note?: string;
}

export interface KPIReport {
  primary_kpis: KPIRecommendation[];
  secondary_kpis: KPIRecommendation[];
  all_kpis: KPIRecommendation[];
  /** KPIs that failed verification. They are never exported as measures. */
  rejected_kpis?: KPIRecommendation[];
  domain: DatasetDomain;
  total_kpis_recommended: number;
}
