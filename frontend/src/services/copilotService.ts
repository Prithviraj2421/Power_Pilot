import { apiClient } from '../api/apiClient';

export interface CopilotApiResponse {
  status: 'success' | 'error';
  query: string;
  answer: string;
  intent: string;
  evidence: string[];
  recommended_actions: string[];
  suggested_followups: string[];
}

export class CopilotService {
  /**
   * Send natural language query to backend AI Copilot endpoint.
   */
  public static async askCopilot(query: string, file: File): Promise<CopilotApiResponse> {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('file', file);

    const response = await apiClient.post<CopilotApiResponse>(
      '/api/v1/copilot/ask',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  }
}
