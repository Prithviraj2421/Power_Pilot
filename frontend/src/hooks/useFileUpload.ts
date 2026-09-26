import { useCallback } from 'react';
import { useUploadStore } from '../store/useUploadStore';

export function useFileUpload() {
  const { file, isDragging, error, setFile, setIsDragging, setError, resetUpload } = useUploadStore();

  const validateAndSetFile = useCallback(
    (selectedFile: File) => {
      if (!selectedFile.name.endsWith('.csv')) {
        setError('Only .csv files are supported by PowerPilot.');
        return false;
      }
      setFile(selectedFile);
      return true;
    },
    [setFile, setError]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(true);
    },
    [setIsDragging]
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
    },
    [setIsDragging]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        validateAndSetFile(e.dataTransfer.files[0]);
      }
    },
    [setIsDragging, validateAndSetFile]
  );

  return {
    file,
    isDragging,
    error,
    validateAndSetFile,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    resetUpload,
  };
}
