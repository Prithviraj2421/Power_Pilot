import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from '@testing-library/react';
import { useAnalysisStore } from './useAnalysisStore';
import { AnalysisService } from '../services/analysisService';
import type { DatasetRecord, MasterIntelligenceResult } from '../types';

vi.mock('../services/analysisService');

const record: DatasetRecord = {
  dataset_id: 'ds-123',
  filename: 'retail.csv',
  size_bytes: 4457,
  content_sha256: 'abc',
  original_rows: 61,
  total_rows: 60,
  total_columns: 11,
  rows_removed_by_cleaning: 1,
  detected_domain: 'retail',
  domain_confidence: 0.8,
  quality_grade: 'A',
  quality_score: 91.7,
  quality_issues_count: 8,
  created_at: '2026-01-01T00:00:00Z',
  last_accessed_at: '2026-01-01T00:00:00Z',
  source_encoding: 'utf-8',
  source_delimiter: ',',
  source_format: 'utf-8, comma-separated',
  read_with_defaults: true,
};

const result = {
  dataset_profile: { dataset_name: 'retail.csv', total_rows: 60, total_columns: 11 },
  detected_entities: [],
} as unknown as MasterIntelligenceResult;

const reset = () =>
  act(() => {
    useAnalysisStore.setState({
      status: 'idle',
      datasetId: null,
      datasetRecord: null,
      currentDatasetName: null,
      intelligenceResult: null,
      errorMessage: null,
    });
  });

describe('useAnalysisStore', () => {
  beforeEach(reset);

  it('starts idle with nothing loaded', () => {
    const state = useAnalysisStore.getState();
    expect(state.status).toBe('idle');
    expect(state.datasetId).toBeNull();
    expect(state.intelligenceResult).toBeNull();
  });

  it('stores the dataset id alongside the analysis', () => {
    act(() => {
      useAnalysisStore.getState().setAnalysisResult('retail.csv', result, 'ds-123', record);
    });

    const state = useAnalysisStore.getState();
    expect(state.status).toBe('success');
    expect(state.datasetId).toBe('ds-123');
    expect(state.currentDatasetName).toBe('retail.csv');
    expect(state.datasetRecord?.rows_removed_by_cleaning).toBe(1);
  });

  it('clears a previous error when a new analysis succeeds', () => {
    act(() => {
      useAnalysisStore.getState().setError('boom');
      useAnalysisStore.getState().setAnalysisResult('retail.csv', result, 'ds-123', record);
    });

    expect(useAnalysisStore.getState().errorMessage).toBeNull();
  });

  it('records an error without discarding the dataset id', () => {
    act(() => {
      useAnalysisStore.getState().setAnalysisResult('retail.csv', result, 'ds-123', record);
      useAnalysisStore.getState().setError('network down');
    });

    const state = useAnalysisStore.getState();
    expect(state.status).toBe('error');
    expect(state.errorMessage).toBe('network down');
    expect(state.datasetId).toBe('ds-123');
  });

  it('clearAnalysis resets everything', () => {
    act(() => {
      useAnalysisStore.getState().setAnalysisResult('retail.csv', result, 'ds-123', record);
      useAnalysisStore.getState().clearAnalysis();
    });

    const state = useAnalysisStore.getState();
    expect(state.status).toBe('idle');
    expect(state.datasetId).toBeNull();
    expect(state.intelligenceResult).toBeNull();
  });

  describe('restoreFromDatasetId', () => {
    it('re-fetches the analysis for the persisted id', async () => {
      vi.mocked(AnalysisService.getResult).mockResolvedValue({
        status: 'success',
        dataset: record,
        result,
      });
      act(() => {
        useAnalysisStore.setState({ datasetId: 'ds-123' });
      });

      let restored = false;
      await act(async () => {
        restored = await useAnalysisStore.getState().restoreFromDatasetId();
      });

      expect(restored).toBe(true);
      expect(AnalysisService.getResult).toHaveBeenCalledWith('ds-123');
      const state = useAnalysisStore.getState();
      expect(state.status).toBe('success');
      expect(state.currentDatasetName).toBe('retail.csv');
      expect(state.intelligenceResult).toEqual(result);
    });

    it('accepts an explicit id over the stored one', async () => {
      vi.mocked(AnalysisService.getResult).mockResolvedValue({
        status: 'success',
        dataset: record,
        result,
      });

      await act(async () => {
        await useAnalysisStore.getState().restoreFromDatasetId('ds-explicit');
      });

      expect(AnalysisService.getResult).toHaveBeenCalledWith('ds-explicit');
    });

    it('does nothing when there is no id to restore from', async () => {
      let restored = true;
      await act(async () => {
        restored = await useAnalysisStore.getState().restoreFromDatasetId();
      });

      expect(restored).toBe(false);
      expect(AnalysisService.getResult).not.toHaveBeenCalled();
    });

    it('drops a stale id when the dataset no longer exists', async () => {
      // A persisted id can point at a dataset that was deleted or pruned; the UI
      // must fall back to the upload prompt rather than hanging on a dead handle.
      vi.mocked(AnalysisService.getResult).mockRejectedValue(
        new Error("No dataset registered with id 'ds-gone'.")
      );
      act(() => {
        useAnalysisStore.setState({ datasetId: 'ds-gone' });
      });

      let restored = true;
      await act(async () => {
        restored = await useAnalysisStore.getState().restoreFromDatasetId();
      });

      expect(restored).toBe(false);
      const state = useAnalysisStore.getState();
      expect(state.datasetId).toBeNull();
      expect(state.status).toBe('idle');
      expect(state.errorMessage).toContain('No dataset registered');
    });
  });

  describe('persistence', () => {
    it('persists only the dataset id, never the analysis', () => {
      act(() => {
        useAnalysisStore.getState().setAnalysisResult('retail.csv', result, 'ds-123', record);
      });

      const stored = JSON.parse(localStorage.getItem('powerpilot-analysis') ?? '{}');
      expect(stored.state.datasetId).toBe('ds-123');
      // The analysis is far too large for localStorage and is re-fetched instead.
      expect(stored.state.intelligenceResult).toBeUndefined();
      expect(stored.state.datasetRecord).toBeUndefined();
    });
  });
});
