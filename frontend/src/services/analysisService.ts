import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';
import { AnalyzeCsvApiResponse } from '../types';

export class AnalysisService {
  /**
   * Post CSV file to the backend PowerPilot Master Intelligence Pipeline endpoint.
   */
  public static async analyzeCsv(file: File): Promise<AnalyzeCsvApiResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<AnalyzeCsvApiResponse>(
      API_ENDPOINTS.INTELLIGENCE.ANALYZE_CSV,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }
}
