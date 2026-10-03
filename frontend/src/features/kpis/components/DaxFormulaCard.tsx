import React, { useState } from 'react';
import { KPIRecommendation } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Copy, Check, Code, ShieldCheck } from 'lucide-react';
import { formatKpiValue } from '../formatKpiValue';

export interface DaxFormulaCardProps {
  kpi: KPIRecommendation;
}

export const DaxFormulaCard: React.FC<DaxFormulaCardProps> = ({ kpi }) => {
  const [copied, setCopied] = useState(false);
  const value = formatKpiValue(kpi);

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
        <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Code className="w-5 h-5 text-primary" />
            <h4 className="text-base font-semibold text-white">{kpi.name}</h4>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {kpi.verified && (
              <span title={kpi.verification_note || 'Verified against the dataset'}>
                <Badge variant="success">
                  <ShieldCheck className="w-3 h-3 mr-1 inline" />
                  Verified
                </Badge>
              </span>
            )}
            <Badge variant="purple">{kpi.priority}</Badge>
          </div>
        </div>

        {value !== null && (
          <div className="mb-3" data-testid="kpi-value">
            <div className="text-2xl font-bold text-white">{value}</div>
            <div className="text-[11px] text-gray-500">Computed on your cleaned dataset</div>
          </div>
        )}

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

      <div className="pt-2 flex items-start justify-between gap-3 text-xs border-t border-border">
        <span className="text-gray-400 shrink-0">Baseline:</span>
        <span className="font-semibold text-success text-right">{kpi.target_threshold || 'N/A'}</span>
      </div>
    </Card>
  );
};
