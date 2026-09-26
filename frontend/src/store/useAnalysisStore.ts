import { create } from 'zustand';
import { MasterIntelligenceResult } from '../types';

export type AnalysisStatus = 'idle' | 'analyzing' | 'success' | 'error';

interface AnalysisState {
  status: AnalysisStatus;
  currentDatasetName: string | null;
  intelligenceResult: MasterIntelligenceResult | null;
  errorMessage: string | null;
  
  setStatus: (status: AnalysisStatus) => void;
  setAnalysisResult: (datasetName: string, result: MasterIntelligenceResult) => void;
  setError: (message: string) => void;
  clearAnalysis: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  status: 'idle',
  currentDatasetName: null,
  intelligenceResult: null,
  errorMessage: null,

  setStatus: (status) => set({ status }),
  setAnalysisResult: (datasetName, result) =>
    set({
      status: 'success',
      currentDatasetName: datasetName,
      intelligenceResult: result,
      errorMessage: null,
    }),
  setError: (message) =>
    set({
      status: 'error',
      errorMessage: message,
    }),
  clearAnalysis: () =>
    set({
      status: 'idle',
      currentDatasetName: null,
      intelligenceResult: null,
      errorMessage: null,
    }),
}));
