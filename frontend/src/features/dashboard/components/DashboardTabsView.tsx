import React, { useEffect, useState } from 'react';
import { LayoutGrid } from 'lucide-react';
import { ColumnProfile, DashboardTab, KPIRecommendation } from '../../../types';
import { EmptyState } from '../../../components/ui/EmptyState';
import { TabDashboardView } from './TabDashboardView';

export interface DashboardTabsViewProps {
  tabs: DashboardTab[];
  primaryKpis: KPIRecommendation[];
  columns?: ColumnProfile[];
}

/**
 * Renders the full multi-tab dashboard the Dashboard Engine recommended.
 *
 * The workspace previously rendered `tabs[0]` only, so for a retail dataset the
 * engine's second tab (and any beyond it) was computed on every analysis and
 * never displayed. A single-tab recommendation renders without the switcher, so
 * nothing extra appears when there is nothing extra to show.
 */
export const DashboardTabsView: React.FC<DashboardTabsViewProps> = ({
  tabs,
  primaryKpis,
  columns,
}) => {
  const [activeIndex, setActiveIndex] = useState(0);

  // A new dataset can recommend fewer tabs than the last one; without this the
  // index could point past the end and render nothing.
  useEffect(() => {
    if (activeIndex > tabs.length - 1) setActiveIndex(0);
  }, [tabs.length, activeIndex]);

  if (tabs.length === 0) {
    return (
      <EmptyState
        title="No Dashboard Layout Recommended"
        description="The Dashboard Engine did not produce any tabs for this dataset. It needs recognizable measures and dimensions to design a layout."
      />
    );
  }

  const activeTab = tabs[Math.min(activeIndex, tabs.length - 1)];

  return (
    <div className="space-y-5">
      {tabs.length > 1 && (
        <div
          role="tablist"
          aria-label="Dashboard tabs"
          className="flex items-center gap-2 flex-wrap"
        >
          <span className="flex items-center gap-1.5 text-[11px] font-bold text-gray-500 uppercase tracking-wider mr-1">
            <LayoutGrid className="w-3.5 h-3.5 text-primary" />
            <span>
              {tabs.length} Dashboards
            </span>
          </span>

          {tabs.map((tab, index) => {
            const isActive = index === activeIndex;
            return (
              <button
                key={tab.tab_id}
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveIndex(index)}
                title={tab.description}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  isActive
                    ? 'bg-primary text-white border-primary/50 shadow-glow-blue'
                    : 'bg-surface text-gray-300 border-white/5 hover:text-white hover:border-primary/40'
                }`}
              >
                {tab.tab_name}
                <span
                  className={`ml-2 text-[10px] font-mono ${
                    isActive ? 'text-white/70' : 'text-gray-500'
                  }`}
                >
                  {tab.widgets.length}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <TabDashboardView
        key={activeTab.tab_id}
        tab={activeTab}
        primaryKpis={primaryKpis}
        columns={columns}
      />
    </div>
  );
};
