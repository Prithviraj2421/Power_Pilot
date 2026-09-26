import React, { useState } from 'react';
import { KPIRecommendation } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Copy, Check, Code } from 'lucide-react';

export interface DaxFormulaCardProps {
  kpi: KPIRecommendation;
}

export const DaxFormulaCard: React.FC<DaxFormulaCardProps> = ({ kpi }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (kpi.formula) {
      navigator.clipboard.writeText(kpi.formula);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Card className="p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Code className="w-5 h-5 text-primary" />
            <h4 className="text-base font-semibold text-white">{kpi.name}</h4>
          </div>
          <Badge variant="purple">{kpi.priority}</Badge>
        </div>

        <p className="text-xs text-gray-400 mb-3">{kpi.reason}</p>

        {kpi.formula && (
          <div className="relative group bg-background border border-border rounded-lg p-3 font-mono text-xs text-blue-300 overflow-x-auto mb-3">
            <code>{kpi.formula}</code>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 bg-card hover:bg-surface text-gray-400 hover:text-white rounded border border-border transition-colors"
              title="Copy DAX Formula"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
      </div>

      <div className="pt-2 flex items-center justify-between text-xs border-t border-border">
        <span className="text-gray-400">Target Benchmark:</span>
        <span className="font-semibold text-success">{kpi.target_threshold || 'N/A'}</span>
      </div>
    </Card>
  );
};
