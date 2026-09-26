import { create } from 'zustand';

interface PreferencesState {
  theme: 'dark';
  denseView: boolean;
  autoAnalyzeOnUpload: boolean;
  setDenseView: (dense: boolean) => void;
  setAutoAnalyzeOnUpload: (auto: boolean) => void;
}

export const usePreferencesStore = create<PreferencesState>((set) => ({
  theme: 'dark',
  denseView: false,
  autoAnalyzeOnUpload: true,
  setDenseView: (dense) => set({ denseView: dense }),
  setAutoAnalyzeOnUpload: (auto) => set({ autoAnalyzeOnUpload: auto }),
}));
