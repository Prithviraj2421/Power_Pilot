import { DatasetDomain } from './domain';

export interface EntityRelationship {
  source_column: string;
  target_column: string;
  relationship_type: "PRIMARY_KEY" | "FOREIGN_KEY" | "PARENT_CHILD" | "CORRELATION_LINK" | "SEMANTIC_LINK";
  cardinality: "ONE_TO_ONE" | "ONE_TO_MANY" | "MANY_TO_MANY";
  confidence: number;
  reasoning: string;
  evidence: string[];
}

export interface RelationshipReport {
  domain: DatasetDomain;
  primary_keys: EntityRelationship[];
  foreign_keys: EntityRelationship[];
  hierarchies: EntityRelationship[];
  correlations: EntityRelationship[];
  semantic_links: EntityRelationship[];
  all_relationships: EntityRelationship[];
}
