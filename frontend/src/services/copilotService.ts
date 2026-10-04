import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';

/** A figure in the answer that the model tied to a fact in the analysis. Offsets index into `answer`. */
export interface CopilotCitation {
  start: number;
  end: number;
  /** The figure as written, e.g. "$2.30M". */
  text: string;
  fact_id: string;
  /** What the fact means, e.g. "Total Sales Revenue (KPI value)". */
  label: string;
  /** The fact's stored value. */
  value: number;
  unit: 'count' | 'number' | 'percent' | 'ratio' | 'currency' | 'coefficient';
}

export interface CopilotApiResponse {
  status: 'success' | 'error';
  dataset_id: string;
  dataset_name: string;
  query: string;
  answer: string;
  intent: string;
  evidence: string[];
  recommended_actions: string[];
  suggested_followups: string[];
  /** Which engine produced the answer: 'llm' or 'rules'. */
  source: 'llm' | 'rules';
  /** Whether every figure in the answer traces back to the computed analysis. */
  verified: boolean;
  verification_note: string;
  /** Present when the LLM was skipped or its answer was rejected. */
  fallback_reason: string | null;
  /** Where each cited figure in `answer` came from; empty for answers composed by the rules engine. */
  citations: CopilotCitation[];
}

export interface CopilotStatus {
  status: string;
  llm_enabled: boolean;
  model: string | null;
  engine: 'llm' | 'rules';
  detail: string;
}

export class CopilotService {
  /** Which engine will answer, so the UI can say so before the first question. */
  public static async getStatus(): Promise<CopilotStatus> {
    const response = await apiClient.get<CopilotStatus>(API_ENDPOINTS.COPILOT.STATUS);
    return response.data;
  }

  /**
   * Ask a natural language question against a registered dataset.
   *
   * The backend answers from that dataset's computed analysis, so figures come
   * from the data rather than being generated. A follow-up question costs a
   * cache lookup, not another pipeline run.
   */
  public static async askCopilot(datasetId: string, query: string): Promise<CopilotApiResponse> {
    const response = await apiClient.post<CopilotApiResponse>(API_ENDPOINTS.COPILOT.ASK, {
      dataset_id: datasetId,
      query,
    });
    return response.data;
  }
}
