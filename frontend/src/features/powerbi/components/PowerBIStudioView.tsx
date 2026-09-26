import React, { useState } from 'react';
import { PowerBIInstructionGuide } from './PowerBIInstructionGuide';
import { PowerBIExportModal } from './PowerBIExportModal';
import { Button } from '../../../components/ui/Button';
import { Download, Monitor, Share2 } from 'lucide-react';

export const PowerBIStudioView: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white mb-1">Power BI Integration Studio</h3>
          <p className="text-xs text-gray-400">
            Export generated DAX measures, Tabular Model BIM schemas, and Power Query M transformations for Power BI Desktop.
          </p>
        </div>
        <Button
          onClick={() => setIsModalOpen(true)}
          leftIcon={<Download className="w-4 h-4" />}
        >
          Export Assets to Power BI
        </Button>
      </div>

      <PowerBIInstructionGuide />

      <PowerBIExportModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
};
