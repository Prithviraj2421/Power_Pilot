import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';
import { ApplyResponse, ReverseReport } from '../types';
import { authorised, call } from './liveService';

function reportForm(file: File, extra: Record<string, string> = {}): FormData {
  const form = new FormData();
  form.append('file', file);
  Object.entries(extra).forEach(([key, value]) => form.append(key, value));
  return form;
}

/**
 * "Prove-It Migration": give PowerPilot a legacy report and the data behind it, and it finds the formula
 * behind each number, proves it by recomputing, and flags the numbers it cannot reproduce.
 */
export class ReverseService {
  /** Explain a report against an uploaded dataset. */
  public static async run(datasetId: string, file: File): Promise<ReverseReport> {
    const response = await apiClient.post<ReverseReport>(API_ENDPOINTS.REVERSE.RUN(datasetId), reportForm(file), {
      timeout: 300_000,
    });
    return response.data;
  }

  /** Explain a report against a table of the open Power BI model. */
  public static runLive(token: string, table: string, file: File): Promise<ReverseReport> {
    return call(
      apiClient.post<ReverseReport>(API_ENDPOINTS.POWERBI_LIVE.REVERSE, reportForm(file, { table }), {
        ...authorised(token),
        timeout: 600_000,
      })
    );
  }

  /** With `dryRun`, Power BI's engine checks each measure but nothing is written. Ids only: DAX never leaves the server. */
  public static applyLive(token: string, reportId: string, measureIds: string[], dryRun = false): Promise<ApplyResponse> {
    return call(
      apiClient.post<ApplyResponse>(
        API_ENDPOINTS.POWERBI_LIVE.REVERSE_APPLY,
        { report_id: reportId, measure_ids: measureIds, dry_run: dryRun },
        { ...authorised(token), timeout: 120_000 }
      )
    );
  }

  /** A .dax script of only the proven measures. */
  public static async exportDax(reportId: string): Promise<string> {
    const response = await apiClient.get<string>(API_ENDPOINTS.REVERSE.DAX(reportId), { responseType: 'text' });
    return response.data;
  }

  /** A Tabular Model .bim of only the proven measures. */
  public static async exportBim(reportId: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(API_ENDPOINTS.REVERSE.BIM(reportId));
    return response.data;
  }
}
