import React, { useRef } from 'react';
import { FileSearch } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';

export interface ReportUploadProps {
  file: File | null;
  running: boolean;
  error: string | null;
  onFile: (file: File | null) => void;
  onRun: () => void;
  /** Extra controls above the file picker, e.g. which table of the model to use. */
  children?: React.ReactNode;
  disabled?: boolean;
}

export const ReportUpload: React.FC<ReportUploadProps> = ({ file, running, error, onFile, onRun, children, disabled }) => {
  const input = useRef<HTMLInputElement>(null);
  return (
    <Card className="space-y-4 p-6">
      <div>
        <h3 className="text-base font-bold text-white">Prove-It Migration</h3>
        <p className="mt-1 text-sm text-gray-400">
          Upload an old report (Excel, CSV, or a PDF with tables). PowerPilot finds the formula behind every number, proves each one by
          recomputing it on your data, and flags the numbers it cannot reproduce. Those are often real mistakes.
        </p>
      </div>
      {children}
      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={input}
          type="file"
          accept=".xlsx,.xlsm,.csv,.pdf"
          className="sr-only"
          aria-label="Legacy report file"
          onChange={(event) => onFile(event.target.files?.[0] ?? null)}
        />
        <Button variant="outline" onClick={() => input.current?.click()} disabled={running}>
          {file ? 'Choose another file' : 'Choose the old report'}
        </Button>
        {file && <span className="text-sm text-gray-300">{file.name}</span>}
        <Button onClick={onRun} disabled={!file || running || disabled} isLoading={running} leftIcon={<FileSearch className="h-4 w-4" />}>
          Find the formulas
        </Button>
      </div>
      {running && <p className="text-xs text-gray-400">Trying formulas against your data. A big table can take a minute.</p>}
      {error && (
        <p className="text-sm text-red-300" role="alert">
          {error}
        </p>
      )}
    </Card>
  );
};
