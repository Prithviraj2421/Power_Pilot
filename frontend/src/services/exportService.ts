import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';

export interface BrandingParams {
  [key: string]: string | undefined;
  company_name?: string;
  prepared_for?: string;
  prepared_by?: string;
}

export interface ExportHistoryEntry {
  entry_id: string;
  dataset_name: string;
  export_format: string;
  file_size_bytes: number;
  duration_ms: number;
  timestamp: string;
  status: string;
  file_path?: string | null;
}

export interface ExportHistoryResponse {
  status: string;
  total: number;
  history: ExportHistoryEntry[];
}

/**
 * Export Center client.
 *
 * Every export addresses a registered dataset by id. The CSV is never re-sent,
 * so downloading five formats costs one pipeline run rather than five.
 */
export class ExportService {
  /** Trigger a browser download from a Blob response. */
  public static downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    window.URL.revokeObjectURL(url);
  }

  private static async downloadFrom(
    url: string,
    filename: string,
    params?: Record<string, string | undefined>
  ): Promise<void> {
    const response = await apiClient.post(url, null, { params, responseType: 'blob' });
    this.downloadFile(response.data, filename);
  }

  /** Strip a trailing .csv so download names do not stack extensions. */
  private static stem(datasetName: string): string {
    return datasetName.replace(/\.csv$/i, '');
  }

  public static async exportCleanedData(
    datasetId: string,
    datasetName: string,
    format: 'csv' | 'xlsx' = 'csv'
  ): Promise<void> {
    await this.downloadFrom(
      API_ENDPOINTS.EXPORT_CENTER.CLEANED_DATA(datasetId),
      `Cleaned_${this.stem(datasetName)}.${format}`,
      { format }
    );
  }

  public static async exportPdfReport(
    datasetId: string,
    datasetName: string,
    branding: BrandingParams = {}
  ): Promise<void> {
    await this.downloadFrom(
      API_ENDPOINTS.EXPORT_CENTER.PDF(datasetId),
      `PowerPilot_Executive_Report_${this.stem(datasetName)}.pdf`,
      branding
    );
  }

  public static async exportDocxReport(
    datasetId: string,
    datasetName: string,
    branding: BrandingParams = {}
  ): Promise<void> {
    await this.downloadFrom(
      API_ENDPOINTS.EXPORT_CENTER.DOCX(datasetId),
      `PowerPilot_Executive_Report_${this.stem(datasetName)}.docx`,
      branding
    );
  }

  public static async exportHtmlReport(
    datasetId: string,
    datasetName: string,
    branding: BrandingParams = {}
  ): Promise<void> {
    await this.downloadFrom(
      API_ENDPOINTS.EXPORT_CENTER.HTML(datasetId),
      `PowerPilot_Interactive_Report_${this.stem(datasetName)}.html`,
      branding
    );
  }

  public static async exportJson(datasetId: string, datasetName: string): Promise<void> {
    await this.downloadFrom(
      API_ENDPOINTS.EXPORT_CENTER.JSON(datasetId),
      `PowerPilot_Intelligence_${this.stem(datasetName)}.json`
    );
  }

  public static async exportDataDictionary(
    datasetId: string,
    datasetName: string
  ): Promise<void> {
    await this.downloadFrom(
      API_ENDPOINTS.EXPORT_CENTER.DATA_DICTIONARY(datasetId),
      `PowerPilot_Data_Dictionary_${this.stem(datasetName)}.xlsx`
    );
  }

  /**
   * Export activity, newest first. Persisted server-side, so this survives a
   * backend restart. Pass a datasetId to scope it to one dataset.
   */
  public static async getExportHistory(
    limit = 50,
    datasetId?: string
  ): Promise<ExportHistoryResponse> {
    const response = await apiClient.get<ExportHistoryResponse>(
      API_ENDPOINTS.EXPORT_CENTER.HISTORY,
      { params: { limit, dataset_id: datasetId } }
    );
    return response.data;
  }
}
