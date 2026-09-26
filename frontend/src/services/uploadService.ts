import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';

export interface UploadFileResult {
  file_id: string;
  filename: string;
  size_bytes: number;
}

export class UploadService {
  /**
   * Upload raw dataset file for workspace storage.
   */
  public static async uploadFile(file: File): Promise<UploadFileResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadFileResult>(
      API_ENDPOINTS.UPLOAD.FILE,
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
