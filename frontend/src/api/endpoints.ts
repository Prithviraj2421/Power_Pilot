/**
 * Backend API surface.
 *
 * Everything after registration is addressed by `dataset_id`: the CSV is
 * uploaded and analyzed once, then exports, Power BI assets and copilot queries
 * reference that id instead of re-sending the file.
 */
export const API_ENDPOINTS = {
  HEALTH_CHECK: '/health',

  INTELLIGENCE: {
    ANALYZE_CSV: '/api/v1/intelligence/analyze-csv',
  },

  DATASETS: {
    REGISTER: '/api/v1/datasets',
    LIST: '/api/v1/datasets',
    CACHE_STATS: '/api/v1/datasets/stats/cache',
    DETAIL: (datasetId: string) => `/api/v1/datasets/${datasetId}`,
    RESULT: (datasetId: string) => `/api/v1/datasets/${datasetId}/result`,
    DELETE: (datasetId: string) => `/api/v1/datasets/${datasetId}`,
  },

  EXPORT_CENTER: {
    HISTORY: '/api/v1/export-center/history',
    EMAIL_STATUS: '/api/v1/export-center/email/status',
    EMAIL: (datasetId: string) => `/api/v1/export-center/${datasetId}/email`,
    CLEANED_DATA: (datasetId: string) => `/api/v1/export-center/${datasetId}/cleaned-data`,
    PDF: (datasetId: string) => `/api/v1/export-center/${datasetId}/pdf`,
    DOCX: (datasetId: string) => `/api/v1/export-center/${datasetId}/docx`,
    HTML: (datasetId: string) => `/api/v1/export-center/${datasetId}/html`,
    JSON: (datasetId: string) => `/api/v1/export-center/${datasetId}/json`,
    DATA_DICTIONARY: (datasetId: string) => `/api/v1/export-center/${datasetId}/data-dictionary`,
  },

  POWERBI: {
    STATUS: '/api/v1/export/powerbi/status',
    DAX: (datasetId: string) => `/api/v1/export/powerbi/${datasetId}/dax`,
    BIM: (datasetId: string) => `/api/v1/export/powerbi/${datasetId}/bim`,
    M: (datasetId: string) => `/api/v1/export/powerbi/${datasetId}/m`,
  },

  COPILOT: {
    ASK: '/api/v1/copilot/ask',
    STATUS: '/api/v1/copilot/status',
  },

  QUALITY: {
    ASSESS: '/api/v1/quality/assess',
    PREPARE: '/api/v1/quality/prepare',
  },
} as const;
