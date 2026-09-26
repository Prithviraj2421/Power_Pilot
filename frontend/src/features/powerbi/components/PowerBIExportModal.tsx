import React, { useState } from 'react';
import { Modal } from '../../../components/ui/Modal';
import { Button } from '../../../components/ui/Button';
import { Download, FileCode, Database, Copy, Check } from 'lucide-react';
import { PowerBIService } from '../../../services/powerbiService';
import { useUploadStore } from '../../../store/useUploadStore';
import { useToast } from '../../../hooks/useToast';

export interface PowerBIExportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PowerBIExportModal: React.FC<PowerBIExportModalProps> = ({ isOpen, onClose }) => {
  const { file } = useUploadStore();
  const { showSuccess, showError } = useToast();
  const [loadingType, setLoadingType] = useState<string | null>(null);
  const [copiedType, setCopiedType] = useState<string | null>(null);

  const downloadBlob = (content: string, filename: string, contentType: string) => {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = async (content: string, label: string, typeKey: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedType(typeKey);
      showSuccess('Copied to Clipboard!', `Copied ${label} script to your clipboard.`);
      setTimeout(() => setCopiedType(null), 3000);
    } catch (err) {
      showError('Copy Failed', 'Failed to copy to clipboard.');
    }
  };

  const handleDaxAction = async (action: 'download' | 'copy') => {
    if (!file) {
      showError('No File Uploaded', 'Please upload a dataset CSV file first.');
      return;
    }
    setLoadingType('dax');
    try {
      const script = await PowerBIService.exportDax(file);
      if (action === 'download') {
        downloadBlob(script, `${file.name.replace('.csv', '')}_measures.dax`, 'text/plain');
        showSuccess('DAX Script Exported', 'Downloaded .dax measures script file.');
      } else {
        await copyToClipboard(script, 'DAX Measures', 'dax');
      }
    } catch (err: any) {
      showError('Export Failed', err.message);
    } finally {
      setLoadingType(null);
    }
  };

  const handleBimAction = async (action: 'download' | 'copy') => {
    if (!file) {
      showError('No File Uploaded', 'Please upload a dataset CSV file first.');
      return;
    }
    setLoadingType('bim');
    try {
      const bimObj = await PowerBIService.exportBim(file);
      const bimJson = JSON.stringify(bimObj, null, 2);
      if (action === 'download') {
        downloadBlob(bimJson, `PowerPilot_${file.name.replace('.csv', '')}_Model.bim`, 'application/json');
        showSuccess('BIM Schema Exported', 'Downloaded Tabular Model .bim schema file.');
      } else {
        await copyToClipboard(bimJson, 'Tabular Model BIM Schema', 'bim');
      }
    } catch (err: any) {
      showError('Export Failed', err.message);
    } finally {
      setLoadingType(null);
    }
  };

  const handleMAction = async (action: 'download' | 'copy') => {
    if (!file) {
      showError('No File Uploaded', 'Please upload a dataset CSV file first.');
      return;
    }
    setLoadingType('m');
    try {
      const mScript = await PowerBIService.exportPowerQueryM(file);
      if (action === 'download') {
        downloadBlob(mScript, `${file.name.replace('.csv', '')}_PowerQuery.m`, 'text/plain');
        showSuccess('Power Query Script Exported', 'Downloaded .m transformation script file.');
      } else {
        await copyToClipboard(mScript, 'Power Query (M) Code', 'm');
      }
    } catch (err: any) {
      showError('Export Failed', err.message);
    } finally {
      setLoadingType(null);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Export Assets to Power BI" maxWidth="lg">
      <div className="space-y-4 text-sm">
        <p className="text-gray-300">
          Copy or download pre-formatted Power BI measures, Tabular Model schemas, and Power Query data transformation scripts for <strong>{file?.name || 'Uploaded Dataset'}</strong>.
        </p>

        <div className="space-y-3 pt-2">
          {/* DAX Script */}
          <div className="p-4 bg-surface rounded-xl border border-border flex items-center justify-between gap-4">
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                <FileCode className="w-4 h-4 text-primary" />
                <span>DAX Measures Script (.dax)</span>
              </h4>
              <p className="text-xs text-gray-400 mt-1">Contains all recommended KPI measures formatted for Power BI Desktop.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                isLoading={loadingType === 'dax' && copiedType === 'dax'}
                onClick={() => handleDaxAction('copy')}
                leftIcon={copiedType === 'dax' ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              >
                {copiedType === 'dax' ? 'Copied' : 'Copy M Code'}
              </Button>
              <Button
                size="sm"
                isLoading={loadingType === 'dax' && copiedType === null}
                onClick={() => handleDaxAction('download')}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                Download
              </Button>
            </div>
          </div>

          {/* Tabular Model Schema */}
          <div className="p-4 bg-surface rounded-xl border border-border flex items-center justify-between gap-4">
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                <Database className="w-4 h-4 text-success" />
                <span>Tabular Model Schema (.bim)</span>
              </h4>
              <p className="text-xs text-gray-400 mt-1">Microsoft Analysis Services Tabular Model schema for Tabular Editor.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                isLoading={loadingType === 'bim' && copiedType === 'bim'}
                onClick={() => handleBimAction('copy')}
                leftIcon={copiedType === 'bim' ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              >
                {copiedType === 'bim' ? 'Copied' : 'Copy BIM'}
              </Button>
              <Button
                size="sm"
                isLoading={loadingType === 'bim' && copiedType === null}
                onClick={() => handleBimAction('download')}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                Download
              </Button>
            </div>
          </div>

          {/* Power Query M Code */}
          <div className="p-4 bg-surface rounded-xl border border-border flex items-center justify-between gap-4">
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                <FileCode className="w-4 h-4 text-warning" />
                <span>Power Query M Code (.m)</span>
              </h4>
              <p className="text-xs text-gray-400 mt-1">M-code data type transformations for Power BI Advanced Editor.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                isLoading={loadingType === 'm' && copiedType === 'm'}
                onClick={() => handleMAction('copy')}
                leftIcon={copiedType === 'm' ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              >
                {copiedType === 'm' ? 'Copied' : 'Copy M Code'}
              </Button>
              <Button
                size="sm"
                isLoading={loadingType === 'm' && copiedType === null}
                onClick={() => handleMAction('download')}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                Download
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
};
