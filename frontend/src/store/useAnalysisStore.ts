import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { AnalysisService } from '../services/analysisService';
import { DatasetRecord, MasterIntelligenceResult } from '../types';

export type AnalysisStatus = 'idle' | 'analyzing' | 'restoring' | 'success' | 'error';

interface AnalysisState {
  status: AnalysisStatus;
  /** Registry handle. Every backend call after upload uses this, not the File. */
  datasetId: string | null;
  datasetRecord: DatasetRecord | null;
  currentDatasetName: string | null;
  intelligenceResult: MasterIntelligenceResult | null;
  errorMessage: string | null;

  setStatus: (status: AnalysisStatus) => void;
  setAnalysisResult: (
    datasetName: string,
    result: MasterIntelligenceResult,
    datasetId: string,
    datasetRecord?: DatasetRecord | null
  ) => void;
  setError: (message: string) => void;
  clearAnalysis: () => void;
  /** Re-fetch the analysis for the persisted datasetId, e.g. after a refresh. */
  restoreFromDatasetId: (datasetId?: string) => Promise<boolean>;
}

const initialState = {
  status: 'idle' as AnalysisStatus,
  datasetId: null,
  datasetRecord: null,
  currentDatasetName: null,
  intelligenceResult: null,
  errorMessage: null,
};

export const useAnalysisStore = create<AnalysisState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setStatus: (status) => set({ status }),

      setAnalysisResult: (datasetName, result, datasetId, datasetRecord = null) =>
        set({
          status: 'success',
          datasetId,
          datasetRecord,
          currentDatasetName: datasetName,
          intelligenceResult: result,
          errorMessage: null,
        }),

      setError: (message) => set({ status: 'error', errorMessage: message }),

      clearAnalysis: () => set({ ...initialState }),

      restoreFromDatasetId: async (datasetId) => {
        const id = datasetId ?? get().datasetId;
        if (!id) return false;

        set({ status: 'restoring', errorMessage: null });
        try {
          const { dataset, result } = await AnalysisService.getResult(id);
          set({
            status: 'success',
            datasetId: dataset.dataset_id,
            datasetRecord: dataset,
            currentDatasetName: dataset.filename,
            intelligenceResult: result,
            errorMessage: null,
          });
          return true;
        } catch (error) {
          // A persisted id can refer to a dataset that was deleted or pruned, or
          // to a backend that is simply not running. Either way the stale handle
          // is dropped so the UI falls back to the upload prompt.
          set({
            ...initialState,
            status: 'idle',
            errorMessage: error instanceof Error ? error.message : 'Could not restore dataset.',
          });
          return false;
        }
      },
    }),
    {
      name: 'powerpilot-analysis',
      storage: createJSONStorage(() => localStorage),
      // Only the id is persisted. The analysis itself is far too large for
      // localStorage and is re-fetched from the backend on restore.
      partialize: (state) => ({ datasetId: state.datasetId }),
    }
  )
);
