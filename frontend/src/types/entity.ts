export type SemanticType =
  | 'CUSTOMER'
  | 'PRODUCT'
  | 'REVENUE'
  | 'PROFIT'
  | 'COST'
  | 'QUANTITY'
  | 'DATE'
  | 'REGION'
  | 'EMPLOYEE'
  | 'IDENTIFIER'
  | 'UNKNOWN';

export interface DetectedEntity {
  column_name: string;
  entity_type: string | SemanticType;
  confidence: number;
  reason: string;
}

export interface EntityDetectionResult {
  column_name: string;
  entity_type: SemanticType;
  confidence: number;
  reasoning: string;
  evidence: string[];
}
