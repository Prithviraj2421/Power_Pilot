import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';
import {
  AnalyzeCsvApiResponse,
  DatasetListApiResponse,
  DatasetRecord,
  DatasetResultApiResponse,
} from '../types';

export class AnalysisService {
  /**
   * Upload a CSV, run the 12-stage pipeline once, and register the analysis.
   * The response carries a `dataset_id` used by every subsequent operation.
   */
  public static async analyzeCsv(file: File): Promise<AnalyzeCsvApiResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<AnalyzeCsvApiResponse>(
      API_ENDPOINTS.INTELLIGENCE.ANALYZE_CSV,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );

    return response.data;
  }

  /**
   * Re-fetch a registered analysis by id.
   *
   * Served from the backend cache when warm and recomputed from the stored CSV
   * when not, so a workspace can be restored after a page refresh without the
   * user re-uploading anything.
   */
  public static async getResult(datasetId: string): Promise<DatasetResultApiResponse> {
    const response = await apiClient.get<DatasetResultApiResponse>(
      API_ENDPOINTS.DATASETS.RESULT(datasetId)
    );
    return response.data;
  }

  /** Dataset metadata only — does not trigger a pipeline run. */
  public static async getDataset(datasetId: string): Promise<DatasetRecord> {
    const response = await apiClient.get<{ dataset: DatasetRecord }>(
      API_ENDPOINTS.DATASETS.DETAIL(datasetId)
    );
    return response.data.dataset;
  }

  /** Analysis history, newest first. */
  public static async listDatasets(limit = 50, offset = 0): Promise<DatasetListApiResponse> {
    const response = await apiClient.get<DatasetListApiResponse>(API_ENDPOINTS.DATASETS.LIST, {
      params: { limit, offset },
    });
    return response.data;
  }

  /** Permanently delete a dataset, its stored CSV and its cached analysis. */
  public static async deleteDataset(datasetId: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.DATASETS.DELETE(datasetId));
  }
}
