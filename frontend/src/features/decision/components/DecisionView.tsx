import React from 'react';
import { DecisionReport } from '../../../types';
import { DecisionActionCard } from './DecisionActionCard';
import { ScenarioOptionCard } from './ScenarioOptionCard';
import { Card } from '../../../components/ui/Card';
import { Lightbulb, ShieldAlert } from 'lucide-react';

export interface DecisionViewProps {
  report: DecisionReport;
}

export const DecisionView: React.FC<DecisionViewProps> = ({ report }) => {
  if (!report) return null;

  return (
    <div className="space-y-6">
      {/* Executive Summary Card */}
      <Card glass className="p-6 border-purple-800/30">
        <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm mb-2">
          <Lightbulb className="w-5 h-5" />
          <span>Strategic Executive Decision Summary</span>
        </div>
        <p className="text-base text-gray-200 leading-relaxed mb-4">
          {report.executive_decision_summary}
        </p>

        {report.risk_matrix_summary && (
          <div className="p-3 bg-surface rounded-lg border border-border flex items-center gap-2 text-xs text-warning">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>{report.risk_matrix_summary}</span>
          </div>
        )}
      </Card>

      {/* Decision Actions */}
      <div>
        <h3 className="text-lg font-bold text-white mb-3">Recommended Decision Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {report.primary_decisions.map((dec, idx) => (
            <DecisionActionCard key={idx} decision={dec} />
          ))}
        </div>
      </div>

      {/* Scenario Options */}
      {report.scenario_options.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-white mb-3">Strategic Scenario Analysis</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {report.scenario_options.map((sc, idx) => (
              <ScenarioOptionCard key={idx} scenario={sc} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
