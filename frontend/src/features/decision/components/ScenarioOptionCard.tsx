import React from 'react';
import { ScenarioOption } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { GitBranch, CheckCircle2 } from 'lucide-react';

export interface ScenarioOptionCardProps {
  scenario: ScenarioOption;
}

export const ScenarioOptionCard: React.FC<ScenarioOptionCardProps> = ({ scenario }) => {
  const probPercent = (scenario.probability_of_success * 100).toFixed(0);

  return (
    <Card className="p-5 border-border">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-purple-400" />
          <h4 className="text-base font-bold text-white">{scenario.scenario_name}</h4>
        </div>
        <span className="text-xs font-bold text-purple-400 bg-purple-900/30 px-2.5 py-1 rounded-full border border-purple-800/30">
          {probPercent}% Probability
        </span>
      </div>

      <p className="text-xs text-gray-300 mb-4">{scenario.description}</p>

      {/* Probability Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Probability of Success</span>
          <span className="font-semibold text-white">{probPercent}%</span>
        </div>
        <div className="w-full bg-surface rounded-full h-2 overflow-hidden">
          <div
            className="bg-purple-500 h-full rounded-full transition-all duration-500"
            style={{ width: `${probPercent}%` }}
          />
        </div>
      </div>

      <div className="p-3 bg-surface rounded-lg border border-border text-xs mb-3">
        <span className="font-semibold text-gray-400 uppercase tracking-wider block mb-1">
          Assumptions:
        </span>
        <ul className="space-y-1 text-gray-300">
          {scenario.assumptions.map((asm, idx) => (
            <li key={idx} className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-success flex-shrink-0" />
              <span>{asm}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="p-3 bg-success-muted/10 border border-success/20 rounded-lg text-xs flex justify-between items-center">
        <span className="text-gray-300 font-medium">Projected Impact:</span>
        <span className="font-bold text-success">{scenario.projected_impact}</span>
      </div>
    </Card>
  );
};
