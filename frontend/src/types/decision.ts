import { DatasetDomain } from './domain';

export interface DecisionAction {
  action_title: string;
  description: string;
  target_entity: string;
  urgency: "IMMEDIATE" | "SHORT_TERM" | "MEDIUM_TERM" | "LONG_TERM" | string;
  expected_roi: string;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  confidence: number;
  reasoning: string;
  supporting_evidence: string[];
}

export interface ScenarioOption {
  scenario_name: string;
  description: string;
  assumptions: string[];
  projected_impact: string;
  probability_of_success: number;
}

export interface DecisionReport {
  executive_decision_summary: string;
  domain: DatasetDomain;
  primary_decisions: DecisionAction[];
  scenario_options: ScenarioOption[];
  risk_matrix_summary: string;
  all_decisions: DecisionAction[];
}
