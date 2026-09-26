import { create } from 'zustand';

interface UploadState {
  file: File | null;
  isDragging: boolean;
  progress: number;
  error: string | null;
  setFile: (file: File | null) => void;
  setIsDragging: (isDragging: boolean) => void;
  setProgress: (progress: number) => void;
  setError: (error: string | null) => void;
  resetUpload: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  file: null,
  isDragging: false,
  progress: 0,
  error: null,
  setFile: (file) => set({ file, error: null }),
  setIsDragging: (isDragging) => set({ isDragging }),
  setProgress: (progress) => set({ progress }),
  setError: (error) => set({ error }),
  resetUpload: () => set({ file: null, isDragging: false, progress: 0, error: null }),
}));
