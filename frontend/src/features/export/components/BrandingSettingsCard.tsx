import React from 'react';
import { Card } from '../../../components/ui/Card';
import { Building2, UserCheck, Shield } from 'lucide-react';

export interface BrandingSettingsCardProps {
  companyName: string;
  setCompanyName: (v: string) => void;
  preparedFor: string;
  setPreparedFor: (v: string) => void;
  preparedBy: string;
  setPreparedBy: (v: string) => void;
}

export const BrandingSettingsCard: React.FC<BrandingSettingsCardProps> = ({
  companyName,
  setCompanyName,
  preparedFor,
  setPreparedFor,
  preparedBy,
  setPreparedBy,
}) => {
  return (
    <Card glass className="p-6 border-primary/30">
      <div className="flex items-center gap-2 text-white font-bold text-base mb-4">
        <Building2 className="w-5 h-5 text-primary" />
        <span>Enterprise Branding & Report Headers</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1.5 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-primary" />
            Company Name
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="e.g. Acme Corporation"
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1.5 flex items-center gap-1.5">
            <UserCheck className="w-3.5 h-3.5 text-success" />
            Prepared For
          </label>
          <input
            type="text"
            value={preparedFor}
            onChange={(e) => setPreparedFor(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="e.g. Executive Board"
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-1.5 flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-warning" />
            Prepared By
          </label>
          <input
            type="text"
            value={preparedBy}
            onChange={(e) => setPreparedBy(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder="e.g. PowerPilot Intelligence"
          />
        </div>
      </div>
    </Card>
  );
};
