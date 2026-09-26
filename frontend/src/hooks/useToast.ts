import { useCallback } from 'react';
import { useAppStore } from '../store/useAppStore';

export function useToast() {
  const addToast = useAppStore((s) => s.addToast);

  const showSuccess = useCallback(
    (title: string, message?: string) => addToast({ type: 'success', title, message }),
    [addToast]
  );

  const showError = useCallback(
    (title: string, message?: string) => addToast({ type: 'error', title, message }),
    [addToast]
  );

  const showWarning = useCallback(
    (title: string, message?: string) => addToast({ type: 'warning', title, message }),
    [addToast]
  );

  const showInfo = useCallback(
    (title: string, message?: string) => addToast({ type: 'info', title, message }),
    [addToast]
  );

  return { showSuccess, showError, showWarning, showInfo };
}
