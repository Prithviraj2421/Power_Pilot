export enum Priority {
  CRITICAL = "CRITICAL",
  HIGH = "HIGH",
  MEDIUM = "MEDIUM",
  LOW = "LOW",
}

export enum Severity {
  CRITICAL = "CRITICAL",
  HIGH = "HIGH",
  MEDIUM = "MEDIUM",
  LOW = "LOW",
}

export interface Recommendation {
  action_title: string;
  description: string;
  expected_impact: string;
  priority: Priority;
  confidence: number;
}

export interface Insight {
  title: string;
  description: string;
  category: string;
  severity: Severity;
  priority: Priority;
  confidence: number;
  business_impact: string;
  recommendation?: Recommendation;
  supporting_evidence: string[];
}

export interface ExecutiveSummary {
  headline: string;
  key_findings: string[];
  strategic_takeaway: string;
}

export interface InsightReport {
  executive_summary: ExecutiveSummary;
  insights: Insight[];
  critical_count: number;
  high_count: number;
}
