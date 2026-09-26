export const API_ENDPOINTS = {
  HEALTH_CHECK: '/',
  INTELLIGENCE: {
    ANALYZE_CSV: '/api/v1/intelligence/analyze-csv',
  },
  UPLOAD: {
    FILE: '/api/v1/upload',
  },
} as const;
