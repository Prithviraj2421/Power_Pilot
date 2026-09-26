import { DatasetProfile } from './dataset';
import { DetectedEntity } from './entity';
import { BusinessProfile } from './business';
import { DataIntelligenceReport } from './intelligence';
import { InsightReport } from './insight';
import { RelationshipReport } from './relationship';
import { KPIReport } from './kpi';
import { DashboardRecommendationReport } from './dashboard';
import { DecisionReport } from './decision';
import { DatasetQualityReport, DataPreparationReport } from './quality';

export interface MasterIntelligenceResult {
  dataset_profile: DatasetProfile;
  detected_entities: DetectedEntity[];
  quality_report?: DatasetQualityReport;
  preparation_report?: DataPreparationReport;
  business_profile?: BusinessProfile;
  data_intelligence_report?: DataIntelligenceReport;
  insight_report?: InsightReport;
  relationship_report?: RelationshipReport;
  kpi_report?: KPIReport;
  dashboard_report?: DashboardRecommendationReport;
  decision_report?: DecisionReport;
}
