import { DashboardRecommendationReport } from '../types';

export class DashboardService {
  /**
   * Helper utility for extracting scorecard widget configurations from a DashboardRecommendationReport.
   */
  public static extractKpiWidgets(report: DashboardRecommendationReport) {
    if (!report || !report.tabs) return [];
    return report.tabs.flatMap((tab) =>
      tab.widgets.filter((w) => w.widget_type === 'KPI_CARD')
    );
  }

  /**
   * Helper utility for extracting chart widget configurations from a DashboardRecommendationReport.
   */
  public static extractChartWidgets(report: DashboardRecommendationReport) {
    if (!report || !report.tabs) return [];
    return report.tabs.flatMap((tab) =>
      tab.widgets.filter((w) => w.widget_type !== 'KPI_CARD' && w.widget_type !== 'FILTER_PANEL')
    );
  }
}
