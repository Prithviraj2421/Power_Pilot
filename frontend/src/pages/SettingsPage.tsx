import React from 'react';
import { Settings, Sliders, Monitor } from 'lucide-react';
import { PageContainer } from '../components/layout/PageContainer';
import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';
import { usePreferencesStore } from '../store/usePreferencesStore';

export const SettingsPage: React.FC = () => {
  const { denseView, autoAnalyzeOnUpload, setDenseView, setAutoAnalyzeOnUpload } = usePreferencesStore();

  return (
    <PageContainer>
      <PageHeader
        title="Application Settings"
        description="Configure PowerPilot executive UI preferences, API defaults, and pipeline behavior."
      />

      <div className="max-w-3xl space-y-6">
        <Card className="p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-primary" />
            <span>Workspace & Display</span>
          </h3>

          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between py-3 border-b border-border">
              <div>
                <p className="font-semibold text-white">Dense Compact Layout</p>
                <p className="text-xs text-gray-400">Reduce card padding for high-density monitors.</p>
              </div>
              <input
                type="checkbox"
                checked={denseView}
                onChange={(e) => setDenseView(e.target.checked)}
                className="w-5 h-5 accent-primary rounded bg-surface border-border cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between py-3">
              <div>
                <p className="font-semibold text-white">Auto-Analyze on Upload</p>
                <p className="text-xs text-gray-400">Automatically trigger the 10-stage pipeline upon file select.</p>
              </div>
              <input
                type="checkbox"
                checked={autoAnalyzeOnUpload}
                onChange={(e) => setAutoAnalyzeOnUpload(e.target.checked)}
                className="w-5 h-5 accent-primary rounded bg-surface border-border cursor-pointer"
              />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Monitor className="w-5 h-5 text-primary" />
            <span>API & Connection Defaults</span>
          </h3>

          <div className="space-y-3 text-xs text-gray-300">
            <div className="flex justify-between py-1">
              <span className="text-gray-400">Backend API URL:</span>
              <span className="font-mono text-primary">http://localhost:8000</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-gray-400">Pipeline Endpoint:</span>
              <span className="font-mono text-white">/api/v1/intelligence/analyze-csv</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-gray-400">Axios Request Timeout:</span>
              <span className="font-mono text-white">60,000 ms</span>
            </div>
          </div>
        </Card>
      </div>
    </PageContainer>
  );
};
