import { useState, useCallback } from 'react';

export function useApi<T>() {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (apiCall: () => Promise<T>): Promise<T | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiCall();
      setData(result);
      setIsLoading(false);
      return result;
    } catch (err: any) {
      const msg = err.message || 'An error occurred while communicating with the server.';
      setError(msg);
      setIsLoading(false);
      return null;
    }
  }, []);

  return { data, isLoading, error, execute, setData };
}
