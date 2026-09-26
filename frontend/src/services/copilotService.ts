import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';

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
}

export class CopilotService {
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
