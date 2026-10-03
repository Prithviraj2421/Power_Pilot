import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LivePage } from './LivePage';
import { LiveApiError, LiveService } from '../services/liveService';
import type { ApplyResponse, LiveAnalysis, LiveKpi, LiveStatus, LiveTableAnalysis } from '../types';

vi.mock('../services/liveService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/liveService')>();
  return {
    ...actual,
    LiveService: { status: vi.fn(), analyze: vi.fn(), apply: vi.fn(), forget: vi.fn() },
  };
});

const service = vi.mocked(LiveService);

const kpi = (name: string, overrides: Partial<LiveKpi> = {}): LiveKpi => ({
  id: `ds1:${name.toLowerCase().replace(/\W+/g, '-')}`,
  name,
  formula: `SUM('Sales Data'[Amount])`,
  computed_value: 2261537,
  verified: true,
  baseline: 'Latest month 2024-03 vs 2024-02: 120.00 vs 100.00 (+20.0%)',
  note: 'computed on 61 rows',
  name_taken: false,
  added_by_powerpilot: false,
  ...overrides,
});

const table = (overrides: Partial<LiveTableAnalysis> = {}): LiveTableAnalysis => ({
  table: 'Sales Data',
  dataset_id: 'ds1',
  rows_read: 61,
  rows_total: 61,
  sampled: false,
  can_write: true,
  domain: 'retail',
  kpis: [kpi('Total Sales Revenue'), kpi('Total Units Sold', { computed_value: 11166, formula: "SUM('Sales Data'[Qty])" })],
  rejected: [],
  ...overrides,
});

const status: LiveStatus = {
  connected: true,
  error: null,
  max_rows: 500000,
  tables: [
    { name: 'Customers', columns: 4, rows: 120, will_be_sampled: false },
    { name: 'Sales Data', columns: 11, rows: 61000, will_be_sampled: false },
  ],
};

const analysis = (tables: LiveTableAnalysis[] = [table()]): LiveAnalysis => ({ max_rows: 500000, tables, skipped: [] });

function launchWith(token: string | null) {
  sessionStorage.clear();
  window.history.replaceState(null, '', token ? `/live?server=localhost%3A51234&db=abc#token=${token}` : '/live');
}

async function openAndAnalyze(user = userEvent.setup()) {
  render(<LivePage />);
  await screen.findByText('Tables in your open model');
  await user.click(screen.getByRole('button', { name: /Analyze selected/ }));
  await screen.findByTestId('analysis-Sales Data');
  return user;
}

beforeEach(() => {
  vi.clearAllMocks();
  launchWith('tok');
  service.status.mockResolvedValue(status);
  service.analyze.mockResolvedValue(analysis());
  service.forget.mockResolvedValue(undefined);
});

describe('connecting', () => {
  it('tells the user to open it from Power BI when there is no token', async () => {
    launchWith(null);

    render(<LivePage />);

    expect(await screen.findByText('Open PowerPilot from Power BI Desktop')).toBeInTheDocument();
    expect(service.status).not.toHaveBeenCalled();
  });

  it('explains a missing launch context (409)', async () => {
    service.status.mockRejectedValue(new LiveApiError('PowerPilot was not started from Power BI Desktop', 409));

    render(<LivePage />);

    expect(await screen.findByText('PowerPilot is not attached to a model')).toBeInTheDocument();
  });

  it('explains an expired session (401)', async () => {
    service.status.mockRejectedValue(new LiveApiError('Missing or wrong PowerPilot session token.', 401));

    render(<LivePage />);

    expect(await screen.findByText('Open PowerPilot from Power BI Desktop')).toBeInTheDocument();
    expect(screen.getByText(/session has expired/)).toBeInTheDocument();
  });

  it('shows the engine message and a retry when the model is unreachable', async () => {
    service.status.mockResolvedValueOnce({ ...status, connected: false, error: 'Power BI Desktop’s model is not reachable. Is the report still open?', tables: [] });
    const user = userEvent.setup();

    render(<LivePage />);

    expect(await screen.findByText(/Is the report still open/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Try again/ }));
    expect(await screen.findByText('Tables in your open model')).toBeInTheDocument();
  });

  it('lists the model’s tables and preselects the largest, which is likely the fact table', async () => {
    render(<LivePage />);

    expect(await screen.findByRole('checkbox', { name: 'Analyze Sales Data' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Analyze Customers' })).not.toBeChecked();
    expect(screen.getByText(/61,000 rows/)).toBeInTheDocument();
  });

  it('warns up front that a table over the row limit will only be sampled', async () => {
    service.status.mockResolvedValue({
      ...status,
      tables: [{ name: 'Sales Data', columns: 11, rows: 2_000_000, will_be_sampled: true }],
    });

    render(<LivePage />);

    expect(await screen.findByText('sample only')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent('cannot be added to your report');
  });
});

describe('analysis', () => {
  it('analyzes only the selected tables', async () => {
    const user = userEvent.setup();
    render(<LivePage />);
    await screen.findByText('Tables in your open model');

    await user.click(screen.getByRole('checkbox', { name: 'Analyze Customers' }));
    await user.click(screen.getByRole('button', { name: /Analyze selected/ }));

    await waitFor(() => expect(service.analyze).toHaveBeenCalledWith('tok', ['Sales Data', 'Customers']));
  });

  it('shows each verified KPI with its value, formula and baseline, unchecked by default', async () => {
    await openAndAnalyze();

    const card = screen.getByTestId('analysis-Sales Data');
    expect(within(card).getByText('Total Sales Revenue')).toBeInTheDocument();
    expect(within(card).getByText('2,261,537')).toBeInTheDocument();
    expect(within(card).getAllByText(/SUM\('Sales Data'\[/).length).toBe(2);
    expect(within(card).getAllByText(/Latest month 2024-03/).length).toBeGreaterThan(0);
    expect(within(card).getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' })).not.toBeChecked();
  });

  it('will not offer to add measures from a sampled table, and says why', async () => {
    service.analyze.mockResolvedValue(analysis([table({ sampled: true, can_write: false, rows_read: 500000, rows_total: 2000000 })]));

    await openAndAnalyze();

    expect(screen.getByRole('alert')).toHaveTextContent('cannot be added to your report');
    for (const box of screen.getAllByRole('checkbox', { name: /to my report/ })) expect(box).toBeDisabled();
    expect(screen.getAllByTestId('disabled-reason')[0]).toHaveTextContent('Only a sample');
  });

  it('leaves a name the user already has alone: disabled, with the reason', async () => {
    service.analyze.mockResolvedValue(
      analysis([table({ kpis: [kpi('Total Sales Revenue', { name_taken: true }), kpi('Total Units Sold')] })])
    );

    await openAndAnalyze();

    expect(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' })).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: 'Add Total Units Sold to my report' })).toBeEnabled();
    expect(screen.getByText(/already exists in your model/)).toBeInTheDocument();
  });

  it('lists KPIs that failed verification instead of hiding them', async () => {
    service.analyze.mockResolvedValue(analysis([table({ rejected: [{ name: 'Average Order Value', reason: "column 'Order ID' is not in the dataset" }] })]));

    await openAndAnalyze();

    expect(screen.getByText(/1 KPI\(s\) did not pass verification/)).toBeInTheDocument();
    expect(screen.getByText(/Order ID/)).toBeInTheDocument();
  });

  it('shows an analysis failure without leaving the page', async () => {
    service.analyze.mockRejectedValue(new LiveApiError('Could not read table: model is not reachable', 502));
    const user = userEvent.setup();
    render(<LivePage />);
    await screen.findByText('Tables in your open model');

    await user.click(screen.getByRole('button', { name: /Analyze selected/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('model is not reachable');
  });
});

describe('adding measures', () => {
  const written: ApplyResponse = {
    dry_run: false,
    saved: true,
    reminder: 'Measures were added to the open model. Save your report (Ctrl+S) to keep them.',
    results: [
      { table: 'Sales Data', kpi_id: 'ds1:total-sales-revenue', name: 'Total Sales Revenue', status: 'written', reason: 'added to your model', engine_value: 2261537, computed_value: 2261537 },
    ],
  };

  it('sends only the selected KPIs, as ids, never as formulas', async () => {
    service.apply.mockResolvedValue(written);
    const user = await openAndAnalyze();

    await user.click(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' }));
    await user.click(screen.getByRole('button', { name: /to my report$/ }));

    await waitFor(() =>
      expect(service.apply).toHaveBeenCalledWith('tok', [{ table: 'Sales Data', kpi_id: 'ds1:total-sales-revenue' }], false)
    );
  });

  it('cannot be submitted with nothing selected', async () => {
    await openAndAnalyze();

    expect(screen.getByRole('button', { name: /to my report$/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Check against Power BI/ })).toBeDisabled();
  });

  it('shows a celebration listing exactly what was written, and the save reminder', async () => {
    service.apply.mockResolvedValue(written);
    const user = await openAndAnalyze();
    await user.click(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' }));

    await user.click(screen.getByRole('button', { name: /to my report$/ }));

    const celebration = await screen.findByTestId('success-celebration');
    expect(celebration).toHaveTextContent('1 measure added to your report');
    expect(celebration).toHaveTextContent('Total Sales Revenue');
    expect(celebration).toHaveTextContent('PowerPilot display folder');
    expect(celebration).toHaveTextContent('Ctrl+S');
  });

  it('marks the written measure as taken without re-reading any table', async () => {
    service.apply.mockResolvedValue(written);
    const user = await openAndAnalyze();
    await user.click(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' }));

    await user.click(screen.getByRole('button', { name: /to my report$/ }));
    await screen.findByTestId('success-celebration');

    expect(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' })).toBeDisabled();
    expect(screen.getByText(/PowerPilot already added this measure/)).toBeInTheDocument();
    expect(service.analyze).toHaveBeenCalledTimes(1);
  });

  it('a check against Power BI reports values and writes nothing, so there is no celebration', async () => {
    service.apply.mockResolvedValue({
      dry_run: true,
      saved: false,
      reminder: null,
      results: [{ ...written.results[0], status: 'verified', reason: "Power BI's engine agrees with the computed value" }],
    });
    const user = await openAndAnalyze();
    await user.click(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' }));

    await user.click(screen.getByRole('button', { name: /Check against Power BI/ }));

    const outcome = await screen.findByTestId('apply-outcome');
    expect(outcome).toHaveTextContent('Matches Power BI');
    expect(outcome).toHaveTextContent('Power BI: 2,261,537 · PowerPilot: 2,261,537');
    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();
    expect(service.apply).toHaveBeenCalledWith('tok', expect.any(Array), true);
  });

  it('shows why a measure was refused, with both values', async () => {
    service.apply.mockResolvedValue({
      dry_run: false,
      saved: false,
      reminder: null,
      results: [
        { ...written.results[0], status: 'refused', reason: 'the DAX engine returned 2,263,799 but pandas computed 2,261,537', engine_value: 2263799, computed_value: 2261537 },
      ],
    });
    const user = await openAndAnalyze();
    await user.click(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' }));

    await user.click(screen.getByRole('button', { name: /to my report$/ }));

    const outcome = await screen.findByTestId('apply-outcome');
    expect(outcome).toHaveTextContent('Not added');
    expect(outcome).toHaveTextContent('the DAX engine returned 2,263,799');
    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();
  });

  it('can select every verified KPI at once, skipping any that cannot be added', async () => {
    service.analyze.mockResolvedValue(
      analysis([table({ kpis: [kpi('Total Sales Revenue', { name_taken: true }), kpi('Total Units Sold'), kpi('Active Customer Count')] })])
    );
    const user = await openAndAnalyze();

    await user.click(screen.getByRole('button', { name: 'Select all verified' }));

    expect(screen.getByText('2 selected')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Add Total Sales Revenue to my report' })).not.toBeChecked();
  });
});

describe('forgetting the data', () => {
  it('removes the local copy of every analyzed table and clears the results', async () => {
    const user = await openAndAnalyze();

    await user.click(screen.getByRole('button', { name: /Forget this model's data/ }));

    await waitFor(() => expect(service.forget).toHaveBeenCalledWith('ds1'));
    expect(screen.queryByTestId('analysis-Sales Data')).not.toBeInTheDocument();
  });
});

describe('Prove-It Migration section', () => {
  it('is offered once connected, defaulting to the largest table', async () => {
    render(<LivePage />);

    expect(await screen.findByRole('heading', { name: 'Prove-It Migration' })).toBeInTheDocument();
    expect(screen.getByLabelText('Table to check the report against')).toHaveValue('Sales Data');
    expect(screen.getByRole('button', { name: /Find the formulas/ })).toBeDisabled(); // until an old report is chosen
  });

  it('is not offered when PowerPilot is not attached to a model', async () => {
    launchWith(null);

    render(<LivePage />);

    await screen.findByText('Open PowerPilot from Power BI Desktop');
    expect(screen.queryByRole('heading', { name: 'Prove-It Migration' })).not.toBeInTheDocument();
  });
});
