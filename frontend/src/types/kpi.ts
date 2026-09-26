import { DatasetDomain } from './domain';
import { Priority } from './insight';

export interface KPIRecommendation {
  name: string;
  priority: Priority;
  confidence: number;
  reason: string;
  formula?: string | null;
  target_threshold?: string | null;
  business_impact?: string | null;
}

export interface KPIReport {
  primary_kpis: KPIRecommendation[];
  secondary_kpis: KPIRecommendation[];
  all_kpis: KPIRecommendation[];
  domain: DatasetDomain;
  total_kpis_recommended: number;
}
