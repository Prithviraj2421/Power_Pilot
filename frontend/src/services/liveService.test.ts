import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../api/apiClient';
import { LiveApiError, LiveService, SERVER_GONE_MESSAGE, TIMED_OUT_MESSAGE } from './liveService';

vi.mock('../api/apiClient', () => ({ apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));
const api = vi.mocked(apiClient);

const failure = (message: string, extra: { status?: number; code?: string }) =>
  Object.assign(new Error(message), extra);

beforeEach(() => vi.clearAllMocks());

describe('LiveService errors', () => {
  it('says the background program is gone when the server cannot be reached at all', async () => {
    api.post.mockRejectedValue(failure('Network Error', { code: 'ERR_NETWORK' }));

    const error = await LiveService.analyze('tok').catch((e) => e);

    expect(error).toBeInstanceOf(LiveApiError);
    expect(error.message).toBe(SERVER_GONE_MESSAGE);
    expect(error.message).toContain('External Tools ribbon');
    expect(error.message).not.toBe('Network Error');
  });

  it('does not blame a vanished server for a request that merely timed out', async () => {
    api.post.mockRejectedValue(failure('timeout of 600000ms exceeded', { code: 'ECONNABORTED' }));

    const error = await LiveService.analyze('tok').catch((e) => e);

    expect(error.message).toBe(TIMED_OUT_MESSAGE);
  });

  it('keeps the server’s own message and status for real HTTP errors', async () => {
    api.get.mockRejectedValue(failure('Missing or wrong PowerPilot session token.', { status: 401 }));

    const error = await LiveService.status('tok').catch((e) => e);

    expect(error.status).toBe(401);
    expect(error.message).toBe('Missing or wrong PowerPilot session token.');
  });

  it('sends the session token as a header, and only KPI ids when applying', async () => {
    api.post.mockResolvedValue({ data: { dry_run: false, saved: true, results: [], reminder: null } });

    await LiveService.apply('secret', [{ table: 'Sales', kpi_id: 'ds:total' }], false);

    expect(api.post).toHaveBeenCalledWith(
      '/api/v1/powerbi-live/apply-measures',
      { items: [{ table: 'Sales', kpi_id: 'ds:total' }], dry_run: false },
      expect.objectContaining({ headers: { 'X-PowerPilot-Token': 'secret' } })
    );
  });
});
