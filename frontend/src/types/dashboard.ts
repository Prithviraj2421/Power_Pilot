import { DatasetDomain } from './domain';

export interface WidgetConfig {
  widget_id: string;
  title: string;
  widget_type: "KPI_CARD" | "BAR_CHART" | "LINE_CHART" | "SCATTER_PLOT" | "PIE_CHART" | "TABLE" | "FILTER_PANEL" | string;
  metric_column?: string | null;
  dimension_column?: string | null;
  chart_type?: string | null;
  grid_row: number;
  grid_col: number;
  grid_width: number;
  grid_height: number;
  options?: Record<string, string>;
}

export interface DashboardTab {
  tab_id: string;
  tab_name: string;
  description: string;
  widgets: WidgetConfig[];
}

export interface DashboardRecommendationReport {
  dashboard_title: string;
  description: string;
  domain: DatasetDomain;
  tabs: DashboardTab[];
  global_filters: string[];
  time_intelligence_dimensions: string[];
}
