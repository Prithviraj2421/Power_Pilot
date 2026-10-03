import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LiveReverseSection } from './LiveReverseSection';
import { ReverseStudioView } from './ReverseStudioView';
import { ReverseService } from '../../../services/reverseService';
import { useAnalysisStore } from '../../../store/useAnalysisStore';
import type { ApplyResponse, LiveStatus } from '../../../types';
import { report } from '../fixtures';

vi.mock('../../../services/reverseService', () => ({
  ReverseService: { run: vi.fn(), runLive: vi.fn(), applyLive: vi.fn(), exportDax: vi.fn(), exportBim: vi.fn() },
}));

const service = vi.mocked(ReverseService);
const file = () => new File(['x'], 'legacy.xlsx');

const status: LiveStatus = {
  connected: true,
  error: null,
  max_rows: 500000,
  tables: [
    { name: 'Customers', columns: 4, rows: 120, will_be_sampled: false },
    { name: 'Superstore', columns: 21, rows: 9994, will_be_sampled: false },
  ],
};

async function chooseAndRun(user: ReturnType<typeof userEvent.setup>) {
  await user.upload(screen.getByLabelText('Legacy report file'), file());
  await user.click(screen.getByRole('button', { name: /Find the formulas/ }));
}

beforeEach(() => {
  vi.clearAllMocks();
  useAnalysisStore.setState({ datasetId: 'ds1', currentDatasetName: 'Superstore.csv' } as never);
});

describe('workspace tab (an uploaded dataset)', () => {
  it('needs a file before it can run', () => {
    render(<ReverseStudioView />);
    expect(screen.getByRole('button', { name: /Find the formulas/ })).toBeDisabled();
  });

  it('runs against the dataset and opens on the first number that needs a look', async () => {
    service.run.mockResolvedValue(report());
    const user = userEvent.setup();
    render(<ReverseStudioView />);

    await chooseAndRun(user);

    await screen.findByTestId('reverse-results');
    expect(service.run).toHaveBeenCalledWith('ds1', expect.objectContaining({ name: 'legacy.xlsx' }));
    expect(screen.getByTestId('cell-detail')).toHaveTextContent('Two digits look swapped');
    expect(screen.getByTestId('reverse-summary')).toHaveTextContent('33.3% reproduced');
  });

  it('shows another number when it is clicked', async () => {
    service.run.mockResolvedValue(report());
    const user = userEvent.setup();
    render(<ReverseStudioView />);
    await chooseAndRun(user);
    await screen.findByTestId('reverse-results');

    await user.click(screen.getByTestId('cell-S!B3'));

    expect(within(screen.getByTestId('cell-detail')).getByText('Reproduced')).toBeInTheDocument();
    expect(screen.getByTestId('cell-detail')).not.toHaveTextContent('Two digits look swapped');
  });

  it('shows the server\'s reason when the report cannot be read, and keeps the button usable', async () => {
    service.run.mockRejectedValue(new Error('No numbers were found in the report.'));
    const user = userEvent.setup();
    render(<ReverseStudioView />);

    await chooseAndRun(user);

    expect(await screen.findByRole('alert')).toHaveTextContent('No numbers were found in the report.');
    expect(screen.queryByTestId('reverse-results')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Find the formulas/ })).toBeEnabled();
  });

  it('downloads only through the export endpoints', async () => {
    service.run.mockResolvedValue(report());
    service.exportDax.mockResolvedValue('Total Sales = SUM(1)');
    URL.createObjectURL = vi.fn(() => 'blob:x');
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {}); // jsdom cannot navigate to a download
    const user = userEvent.setup();
    render(<ReverseStudioView />);
    await chooseAndRun(user);
    await screen.findByTestId('reverse-results');

    await user.click(screen.getByRole('button', { name: /Download .dax/ }));

    await waitFor(() => expect(service.exportDax).toHaveBeenCalledWith('rep1'));
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it('asks for data first when there is no dataset', () => {
    useAnalysisStore.setState({ datasetId: null } as never);
    render(<ReverseStudioView />);
    expect(screen.getByText('No dataset yet')).toBeInTheDocument();
  });
});

describe('inside Power BI (a table of the open model)', () => {
  const liveReport = () => report({ live: true, dataset_id: null });
  const outcome = (dryRun: boolean, status: 'verified' | 'written'): ApplyResponse => ({
    dry_run: dryRun,
    saved: !dryRun,
    reminder: dryRun ? null : 'Save your report (Ctrl+S) to keep them.',
    results: [{ table: 'Superstore', kpi_id: 'rep1:total-sales', name: 'Total Sales', status, reason: 'ok', engine_value: 5, computed_value: 5 }],
  });

  it('defaults to the largest table and runs against the one chosen', async () => {
    service.runLive.mockResolvedValue(liveReport());
    const user = userEvent.setup();
    render(<LiveReverseSection token="tok" status={status} defaultTable="Superstore" />);
    const picker = screen.getByLabelText('Table to check the report against');
    expect(picker).toHaveValue('Superstore');

    await user.selectOptions(picker, 'Customers');
    await chooseAndRun(user);

    await screen.findByTestId('reverse-results');
    expect(service.runLive).toHaveBeenCalledWith('tok', 'Customers', expect.objectContaining({ name: 'legacy.xlsx' }));
  });

  it('checks with the engine first, then adds, sending measure ids and never DAX', async () => {
    service.runLive.mockResolvedValue(liveReport());
    service.applyLive.mockResolvedValueOnce(outcome(true, 'verified')).mockResolvedValueOnce(outcome(false, 'written'));
    const user = userEvent.setup();
    render(<LiveReverseSection token="tok" status={status} defaultTable="Superstore" />);
    await chooseAndRun(user);
    await screen.findByTestId('reverse-results');

    await user.click(screen.getByRole('button', { name: 'Check against Power BI' }));
    expect(await screen.findByText(/Nothing was added/)).toBeInTheDocument();
    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Add proven measures to Power BI' }));
    expect(await screen.findByTestId('success-celebration')).toHaveTextContent('1 measure added');

    expect(service.applyLive).toHaveBeenNthCalledWith(1, 'tok', 'rep1', ['rep1:total-sales'], true);
    expect(service.applyLive).toHaveBeenNthCalledWith(2, 'tok', 'rep1', ['rep1:total-sales'], false);
    for (const call of service.applyLive.mock.calls) expect(JSON.stringify(call)).not.toContain('SUM(');
  });

  it('shows a failed apply as an error and writes nothing more', async () => {
    service.runLive.mockResolvedValue(liveReport());
    service.applyLive.mockRejectedValue(new Error("PowerPilot's background program is not running any more."));
    const user = userEvent.setup();
    render(<LiveReverseSection token="tok" status={status} defaultTable="Superstore" />);
    await chooseAndRun(user);
    await screen.findByTestId('reverse-results');

    await user.click(screen.getByRole('button', { name: 'Add proven measures to Power BI' }));

    const alerts = await screen.findAllByRole('alert');
    expect(alerts.some((a) => a.textContent?.includes('not running any more'))).toBe(true);
    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();
  });

  it('renders nothing for a model with no tables', () => {
    const { container } = render(<LiveReverseSection token="tok" status={{ ...status, tables: [] }} defaultTable={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
