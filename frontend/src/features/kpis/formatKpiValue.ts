import { KPIRecommendation } from '../../types';

/** A KPI's computed value for display, or null when it has none (it was never verified). */
export function formatKpiValue(kpi: Pick<KPIRecommendation, 'computed_value'>): string | null {
  const value = kpi.computed_value;
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  const digits = Math.abs(value) >= 1000 ? 0 : Math.abs(value) >= 1 ? 2 : 4;
  return value.toLocaleString('en-US', { maximumFractionDigits: digits });
}
