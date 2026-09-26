export enum DatasetDomain {
  RETAIL = "retail",
  FINANCE = "finance",
  HR = "hr",
  HEALTHCARE = "healthcare",
  MARKETING = "marketing",
  LOGISTICS = "logistics",
  UNKNOWN = "unknown",
}

export interface DomainDetectionResult {
  domain: DatasetDomain;
  confidence: number;
  matched_entities: string[];
  missing_entities: string[];
  evidence: string[];
  reasoning: string;
}
