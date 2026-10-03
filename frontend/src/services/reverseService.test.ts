import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../api/apiClient';
import { SERVER_GONE_MESSAGE } from './liveService';
import { ReverseService } from './reverseService';

vi.mock('../api/apiClient', () => ({ apiClient: { post: vi.fn(), get: vi.fn() } }));

const post = vi.mocked(apiClient.post);
const get = vi.mocked(apiClient.get);

beforeEach(() => vi.clearAllMocks());

describe('ReverseService', () => {
  it('uploads the report as multipart to the dataset it is checked against', async () => {
    post.mockResolvedValue({ data: { report_id: 'r1' } });
    const file = new File(['x'], 'legacy.xlsx');

    const result = await ReverseService.run('ds1', file);

    expect(result).toEqual({ report_id: 'r1' });
    const [url, body, config] = post.mock.calls[0];
    expect(url).toBe('/api/v1/datasets/ds1/reverse-engineer');
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get('file')).toBe(file);
    expect(config?.timeout).toBeGreaterThan(60_000); // reading a big report and searching takes longer than the default
  });

  it('sends the table, the file and the session token for a live model', async () => {
    post.mockResolvedValue({ data: { report_id: 'r2' } });

    await ReverseService.runLive('tok', 'Sales Data', new File(['x'], 'legacy.csv'));

    const [url, body, config] = post.mock.calls[0];
    expect(url).toBe('/api/v1/powerbi-live/reverse-engineer');
    expect((body as FormData).get('table')).toBe('Sales Data');
    expect(config?.headers).toEqual({ 'X-PowerPilot-Token': 'tok' });
  });

  it('applies by ids only: the body has no DAX', async () => {
    post.mockResolvedValue({ data: { dry_run: true, saved: false, results: [], reminder: null } });

    await ReverseService.applyLive('tok', 'r1', ['r1:total-sales'], true);

    const [url, body, config] = post.mock.calls[0];
    expect(url).toBe('/api/v1/powerbi-live/reverse-engineer/apply');
    expect(body).toEqual({ report_id: 'r1', measure_ids: ['r1:total-sales'], dry_run: true });
    expect(config?.headers).toEqual({ 'X-PowerPilot-Token': 'tok' });
  });

  it('tells the user the program is gone, not just "Network Error"', async () => {
    post.mockRejectedValue(Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' }));
    await expect(ReverseService.runLive('tok', 'T', new File(['x'], 'r.xlsx'))).rejects.toThrow(SERVER_GONE_MESSAGE);
  });

  it('keeps the server reason for a report it could not read', async () => {
    post.mockRejectedValue(Object.assign(new Error('Unsupported file type .txt'), { status: 422 }));
    await expect(ReverseService.runLive('tok', 'T', new File(['x'], 'r.txt'))).rejects.toMatchObject({ message: 'Unsupported file type .txt', status: 422 });
  });

  it('fetches the exports as text and JSON', async () => {
    get.mockResolvedValueOnce({ data: 'Total Sales = SUM(1)' }).mockResolvedValueOnce({ data: { model: {} } });

    expect(await ReverseService.exportDax('r1')).toBe('Total Sales = SUM(1)');
    expect(await ReverseService.exportBim('r1')).toEqual({ model: {} });
    expect(get.mock.calls[0][0]).toBe('/api/v1/reverse/r1/dax');
    expect(get.mock.calls[0][1]).toEqual({ responseType: 'text' });
    expect(get.mock.calls[1][0]).toBe('/api/v1/reverse/r1/bim');
  });
});
