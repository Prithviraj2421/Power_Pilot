import { apiClient } from '../api/apiClient';

export interface EmailDistributionRequest {
  recipients: string;
  subject: string;
  body_message: string;
}

export class ExportService {
  /**
   * Helper to trigger browser file download from Blob response.
   */
  public static downloadFile(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  public static async exportCleanedData(file: File, format: 'csv' | 'xlsx' = 'csv'): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post(`/api/v1/export-center/cleaned-data?format=${format}`, formData, {
      responseType: 'blob',
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    const ext = format === 'csv' ? 'csv' : 'xlsx';
    this.downloadFile(response.data, `Cleaned_${file.name.replace('.csv', '')}.${ext}`);
  }

  public static async exportPdfReport(file: File, companyName = 'Enterprise Organization', preparedFor = 'Executive Leadership Team'): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post(
      `/api/v1/export-center/pdf?company_name=${encodeURIComponent(companyName)}&prepared_for=${encodeURIComponent(preparedFor)}`,
      formData,
      {
        responseType: 'blob',
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    this.downloadFile(response.data, `PowerPilot_Executive_Report_${file.name.replace('.csv', '')}.pdf`);
  }

  public static async exportDocxReport(file: File, companyName = 'Enterprise Organization', preparedFor = 'Executive Leadership Team'): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post(
      `/api/v1/export-center/docx?company_name=${encodeURIComponent(companyName)}&prepared_for=${encodeURIComponent(preparedFor)}`,
      formData,
      {
        responseType: 'blob',
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    this.downloadFile(response.data, `PowerPilot_Executive_Report_${file.name.replace('.csv', '')}.docx`);
  }

  public static async exportHtmlReport(file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/v1/export-center/html', formData, {
      responseType: 'blob',
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    this.downloadFile(response.data, `PowerPilot_Interactive_Report_${file.name.replace('.csv', '')}.html`);
  }

  public static async exportJson(file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/v1/export-center/json', formData, {
      responseType: 'blob',
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    this.downloadFile(response.data, `PowerPilot_Intelligence_${file.name.replace('.csv', '')}.json`);
  }

  public static async exportDataDictionary(file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/v1/export-center/data-dictionary', formData, {
      responseType: 'blob',
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    this.downloadFile(response.data, `PowerPilot_Data_Dictionary_${file.name.replace('.csv', '')}.xlsx`);
  }

  public static async sendEmailDistribution(file: File, req: EmailDistributionRequest): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams({
      recipients: req.recipients,
      subject: req.subject,
      body_message: req.body_message,
    });

    const response = await apiClient.post(`/api/v1/export-center/email?${params.toString()}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  }

  public static async getExportHistory(): Promise<any> {
    const response = await apiClient.get('/api/v1/export-center/history');
    return response.data;
  }
}
