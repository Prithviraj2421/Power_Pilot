import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, ArrowLeft, Lightbulb, Code, Network, Target, Monitor, Sparkles, ShieldCheck, Download, Upload } from 'lucide-react';
import { PageContainer } from '../components/layout/PageContainer';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Tabs, TabItem } from '../components/ui/Tabs';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useAnalysisStore } from '../store/useAnalysisStore';
import { WorkspaceLayout } from '../components/layout/WorkspaceLayout';
import { DashboardTabsView } from '../features/dashboard/components/DashboardTabsView';
import { FilterControlPanel } from '../features/dashboard/components/FilterControlPanel';
import { InsightsView } from '../features/insights/components/InsightsView';
import { KpiStudioView } from '../features/kpis/components/KpiStudioView';
import { RelationshipsView } from '../features/relationships/components/RelationshipsView';
import { DecisionView } from '../features/decision/components/DecisionView';
import { PowerBIStudioView } from '../features/powerbi/components/PowerBIStudioView';
import { CopilotView } from '../features/copilot/components/CopilotView';
import { QualityStudioView } from '../features/quality/components/QualityStudioView';
import { ExportCenterView } from '../features/export/components/ExportCenterView';

export const WorkspacePage: React.FC = () => {
  const navigate = useNavigate();
  const { currentDatasetName, intelligenceResult, datasetId, status, restoreFromDatasetId } =
    useAnalysisStore();
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  // A page refresh clears the in-memory analysis but the dataset id is persisted,
  // so the workspace restores itself from the backend instead of demanding a
  // re-upload. The backend serves it from cache, or recomputes it from the
  // stored CSV if the cache has gone cold.
  const needsRestore = !intelligenceResult && !!datasetId && status !== 'restoring';
  useEffect(() => {
    if (needsRestore) {
      void restoreFromDatasetId();
    }
  }, [needsRestore, restoreFromDatasetId]);

  if (status === 'restoring') {
    return (
      <PageContainer>
        <div className="max-w-2xl mx-auto py-24 flex flex-col items-center gap-4">
          <LoadingSpinner />
          <p className="text-sm text-gray-400">Restoring your workspace…</p>
        </div>
      </PageContainer>
    );
  }

  if (!intelligenceResult || !intelligenceResult.dataset_profile) {
    return (
      <PageContainer>
        <div className="max-w-2xl mx-auto py-16">
          <EmptyState
            title="No Active Dataset in Workspace"
            description="Please upload and analyze a CSV dataset on the landing page to unlock real-time executive dashboard views, Stage 1 Data Quality, and DAX KPI Studio."
            action={
              <Button onClick={() => navigate('/')} leftIcon={<Upload className="w-4 h-4" />}>
                Go to Landing & Dataset Upload
              </Button>
            }
          />
        </div>
      </PageContainer>
    );
  }

  const {
    dataset_profile,
    quality_report,
    preparation_report,
    kpi_report,
    dashboard_report,
    insight_report,
    relationship_report,
    decision_report,
  } = intelligenceResult;

  const tabs: TabItem[] = [
    { id: 'quality', label: 'Data Quality (Stage 1)', icon: <ShieldCheck />, badge: quality_report?.total_issues_count || 0 },
    { id: 'dashboard', label: 'Executive Dashboard', icon: <LayoutDashboard /> },
    { id: 'insights', label: 'Executive Insights', icon: <Lightbulb />, badge: insight_report?.insights?.length || 0 },
    { id: 'kpis', label: 'KPI & DAX Studio', icon: <Code />, badge: kpi_report?.primary_kpis?.length || 0 },
    { id: 'relationships', label: 'Entity & Relationships', icon: <Network />, badge: relationship_report?.all_relationships?.length || 0 },
    { id: 'decision', label: 'Strategic Decisions', icon: <Target />, badge: decision_report?.primary_decisions?.length || 0 },
    { id: 'copilot', label: 'AI Copilot', icon: <Sparkles /> },
    { id: 'powerbi', label: 'Power BI Studio', icon: <Monitor /> },
    { id: 'export', label: 'Export Center', icon: <Download /> },
  ];

  // The Dashboard Engine recommends a multi-tab layout. This used to render
  // dashboard_report.tabs[0] and silently discard the rest, so every tab the
  // engine designed beyond the first was computed and never shown.
  const dashboardTabs = dashboard_report?.tabs ?? [];

  return (
    <PageContainer>
      <PageHeader
        title={`${dataset_profile.detected_domain.toUpperCase()} Workspace`}
        description={`Executive intelligence for ${currentDatasetName} (${dataset_profile.total_rows} rows, ${dataset_profile.total_columns} columns). Quality Grade: ${quality_report?.grade || 'A'}.`}
        action={
          <Button variant="secondary" onClick={() => navigate('/')} leftIcon={<FileText className="w-4 h-4" />}>
            Upload Another Dataset
          </Button>
        }
      />

      <WorkspaceLayout>
        {/* Navigation Tabs */}
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

        {/* Global Filter Bar */}
        {dashboard_report && activeTab !== 'copilot' && activeTab !== 'powerbi' && activeTab !== 'quality' && activeTab !== 'export' && (
          <FilterControlPanel
            globalFilters={dashboard_report.global_filters || []}
            timeDimensions={dashboard_report.time_intelligence_dimensions || []}
          />
        )}

        {/* Dynamic Tab Content Renderer */}
        <div className="pt-2">
          {activeTab === 'quality' && (
            <QualityStudioView qualityReport={quality_report} preparationReport={preparation_report} />
          )}

          {activeTab === 'dashboard' && kpi_report && (
            <DashboardTabsView
              tabs={dashboardTabs}
              primaryKpis={kpi_report.primary_kpis}
              columns={dataset_profile.columns}
            />
          )}

          {activeTab === 'insights' && <InsightsView report={insight_report} />}

          {activeTab === 'kpis' && kpi_report && <KpiStudioView report={kpi_report} />}

          {activeTab === 'relationships' && relationship_report && (
            <RelationshipsView report={relationship_report} />
          )}

          {activeTab === 'decision' && decision_report && <DecisionView report={decision_report} />}

          {activeTab === 'copilot' && <CopilotView />}

          {activeTab === 'powerbi' && <PowerBIStudioView />}

          {activeTab === 'export' && <ExportCenterView />}
        </div>
      </WorkspaceLayout>
    </PageContainer>
  );
};
