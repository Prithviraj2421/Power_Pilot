import { apiClient } from '../api/apiClient';
import { API_ENDPOINTS } from '../api/endpoints';
import { AnalysisService } from './analysisService';
import { ApplyResponse, ApplySelection, LiveAnalysis, LiveStatus } from '../types';

const TOKEN_HEADER = 'X-PowerPilot-Token';

/** An error that keeps the HTTP status, so the page can tell "not launched" from "wrong token". */
export class LiveApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = 'LiveApiError';
  }
}

function authorised(token: string) {
  return { headers: { [TOKEN_HEADER]: token } };
}

async function call<T>(request: Promise<{ data: T }>): Promise<T> {
  try {
    return (await request).data;
  } catch (error) {
    // The shared client already turns responses into Errors; recover the status it recorded.
    const status = (error as { status?: number }).status;
    throw new LiveApiError((error as Error).message, status);
  }
}

/** The open Power BI model: read its tables, analyse them, and add verified measures back. */
export class LiveService {
  public static status(token: string): Promise<LiveStatus> {
    return call(apiClient.get<LiveStatus>(API_ENDPOINTS.POWERBI_LIVE.STATUS, authorised(token)));
  }

  /** Reads each table and runs the analysis pipeline on it. Large tables take a while. */
  public static analyze(token: string, tables?: string[]): Promise<LiveAnalysis> {
    return call(
      apiClient.post<LiveAnalysis>(API_ENDPOINTS.POWERBI_LIVE.ANALYZE, { tables }, { ...authorised(token), timeout: 600_000 })
    );
  }

  /** With `dryRun`, runs Power BI's own engine on each KPI and reports, but writes nothing. */
  public static apply(token: string, items: ApplySelection[], dryRun = false): Promise<ApplyResponse> {
    return call(
      apiClient.post<ApplyResponse>(
        API_ENDPOINTS.POWERBI_LIVE.APPLY,
        { items, dry_run: dryRun },
        { ...authorised(token), timeout: 120_000 }
      )
    );
  }

  /** Removes the local copy of a table's rows that analysis kept. */
  public static forget(datasetId: string): Promise<void> {
    return AnalysisService.deleteDataset(datasetId);
  }
}
