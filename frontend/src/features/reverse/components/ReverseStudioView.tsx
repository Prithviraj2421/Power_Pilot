import React, { useCallback } from 'react';
import { EmptyState } from '../../../components/ui/EmptyState';
import { ReverseService } from '../../../services/reverseService';
import { useAnalysisStore } from '../../../store/useAnalysisStore';
import { useReverseRun } from '../useReverse';
import { ReportUpload } from './ReportUpload';
import { ReverseResults } from './ReverseResults';

/** The "Prove-It Migration" tab of the workspace: the old report against the dataset that was uploaded. */
export const ReverseStudioView: React.FC = () => {
  const { datasetId, currentDatasetName } = useAnalysisStore();
  const runner = useCallback((file: File) => ReverseService.run(datasetId as string, file), [datasetId]);
  const reverse = useReverseRun(runner);

  if (!datasetId) {
    return <EmptyState title="No dataset yet" description="Upload and analyze your data first; the old report is checked against it." />;
  }

  return (
    <div className="space-y-6">
      <ReportUpload file={reverse.file} running={reverse.running} error={reverse.error} onFile={reverse.chooseFile} onRun={() => void reverse.run()}>
        <p className="text-xs text-gray-400">
          The numbers are checked against <strong className="text-gray-200">{currentDatasetName ?? 'your dataset'}</strong>, as you uploaded it (before any cleaning).
        </p>
      </ReportUpload>
      {reverse.report && <ReverseResults report={reverse.report} selectedId={reverse.selectedId} onSelect={reverse.select} />}
    </div>
  );
};
