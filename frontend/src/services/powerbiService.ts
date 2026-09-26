import { apiClient } from '../api/apiClient';

export class PowerBIService {
  /**
   * Post CSV file and receive formatted DAX script.
   */
  public static async exportDax(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<string>(
      '/api/v1/export/powerbi/dax',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'text',
      }
    );
    return response.data;
  }

  /**
   * Post CSV file and receive Tabular Model .bim JSON schema.
   */
  public static async exportBim(file: File): Promise<Record<string, unknown>> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/export/powerbi/bim',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  }

  /**
   * Post CSV file and receive Power Query (M) code.
   */
  public static async exportPowerQueryM(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<string>(
      '/api/v1/export/powerbi/m',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'text',
      }
    );
    return response.data;
  }
}
