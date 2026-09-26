import React from 'react';
import { motion } from 'framer-motion';
import { ColumnProfile, DashboardTab, KPIRecommendation } from '../../../types';
import { KpiScorecardGrid } from './KpiScorecardGrid';
import { DynamicChartRenderer } from './DynamicChartRenderer';
import { Badge } from '../../../components/ui/Badge';
import { Sparkles } from 'lucide-react';

export interface TabDashboardViewProps {
  tab: DashboardTab;
  primaryKpis: KPIRecommendation[];
  columns?: ColumnProfile[];
}

export const TabDashboardView: React.FC<TabDashboardViewProps> = ({ tab, primaryKpis, columns }) => {
  const chartWidgets = tab.widgets.filter((w) => w.widget_type !== 'KPI_CARD');

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            {tab.tab_name}
            <Badge variant="primary" size="sm" showDot>
              LIVE ANALYTICS
            </Badge>
          </h2>
          <p className="text-xs text-gray-400 mt-1">{tab.description}</p>
        </div>

        <div className="flex items-center gap-2 text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/30">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Stage 1 Verified Data</span>
        </div>
      </div>

      {/* Hero KPI Scorecards Row */}
      {primaryKpis.length > 0 && <KpiScorecardGrid kpis={primaryKpis} />}

      {/* Dynamic Grid Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {chartWidgets.map((widget, idx) => (
          <motion.div
            key={widget.widget_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: idx * 0.1 }}
          >
            <DynamicChartRenderer widget={widget} columns={columns} />
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};
