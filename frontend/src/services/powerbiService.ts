import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';

/**
 * Power BI asset generation, addressed by registered dataset id.
 * Generating all three artifacts costs one pipeline run, not three.
 */
export class PowerBIService {
  /** Formatted .dax measure script for Power BI Desktop. */
  public static async exportDax(datasetId: string): Promise<string> {
    const response = await apiClient.post<string>(API_ENDPOINTS.POWERBI.DAX(datasetId), null, {
      responseType: 'text',
    });
    return response.data;
  }

  /** Analysis Services Tabular Model .bim JSON schema. */
  public static async exportBim(datasetId: string): Promise<Record<string, unknown>> {
    const response = await apiClient.post<Record<string, unknown>>(
      API_ENDPOINTS.POWERBI.BIM(datasetId)
    );
    return response.data;
  }

  /** Power Query (M) transformation code. */
  public static async exportPowerQueryM(datasetId: string): Promise<string> {
    const response = await apiClient.post<string>(API_ENDPOINTS.POWERBI.M(datasetId), null, {
      responseType: 'text',
    });
    return response.data;
  }
}
