import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReportGrid } from './ReportGrid';
import { CellDetailPanel } from './CellDetailPanel';
import { SummaryBar } from './SummaryBar';
import { MigrationPanel, MigrationPanelProps } from './MigrationPanel';
import { cell, report } from '../fixtures';

describe('ReportGrid', () => {
  it('draws the report back with every number coloured by status and named in words', () => {
    render(<ReportGrid report={report()} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByText('Sales by Region')).toBeInTheDocument();
    expect(screen.getByTestId('cell-S!B3')).toHaveAttribute('data-status', 'REPRODUCED');
    expect(screen.getByTestId('cell-S!C3')).toHaveAttribute('data-status', 'NOT_REPRODUCIBLE');
    expect(screen.getByTestId('cell-S!B4')).toHaveAttribute('data-status', 'AMBIGUOUS');
    expect(screen.getByTestId('cell-S!B5')).toHaveAttribute('data-status', 'DERIVED');
    expect(screen.getByRole('button', { name: /S C3 \(East · 2024\): not reproduced/ })).toBeInTheDocument();
    expect(screen.getByLabelText('Colour key')).toHaveTextContent('Several formulas fit');
  });

  it('shows labels and headers as plain text, not as clickable numbers', () => {
    render(<ReportGrid report={report()} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByText('Central').closest('td')).toHaveAttribute('data-kind', 'label');
    expect(screen.getByText('2024').closest('td')).toHaveAttribute('data-kind', 'header');
    expect(screen.queryByRole('button', { name: 'Central' })).not.toBeInTheDocument();
  });

  it('reports a click and marks the selected number', async () => {
    const onSelect = vi.fn();
    const { rerender } = render(<ReportGrid report={report()} selectedId={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByTestId('cell-S!C3'));
    expect(onSelect).toHaveBeenCalledWith('S!C3');

    rerender(<ReportGrid report={report()} selectedId="S!C3" onSelect={onSelect} />);
    expect(screen.getByTestId('cell-S!C3')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('cell-S!B3')).toHaveAttribute('aria-pressed', 'false');
  });

  it('marks a number that only matches the cleaned data', () => {
    const cleaned = report({ cells: report().cells.map((c) => (c.id === 'S!B3' ? { ...c, basis: 'cleaned' as const, writable: false } : c)) });
    render(<ReportGrid report={cleaned} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByTestId('cell-S!B3')).toHaveTextContent('*');
    expect(screen.getByText(/Matches the cleaned data, not the raw table/)).toBeInTheDocument();
  });

  it('says nothing about cleaned data when there is none', () => {
    render(<ReportGrid report={report()} selectedId={null} onSelect={() => {}} />);
    expect(screen.queryByText(/cleaned data/)).not.toBeInTheDocument();
  });
});

describe('CellDetailPanel', () => {
  it('invites a click when nothing is selected', () => {
    render(<CellDetailPanel cell={null} />);
    expect(screen.getByTestId('cell-detail-empty')).toHaveTextContent('Click a number');
  });

  it('shows the formula, its DAX and the recomputed value for a reproduced number', () => {
    render(<CellDetailPanel cell={cell('S!B3', { recomputed: 40194.25, target: { ...cell('S!B3').target, shown_text: '40,194.25' } })} />);
    const panel = screen.getByRole('region', { name: 'Cell details' });
    expect(within(panel).getByText('Reproduced')).toBeInTheDocument();
    expect(within(panel).getByText('Strong evidence')).toBeInTheDocument();
    expect(within(panel).getByText('Sum of Sales where Region is West')).toBeInTheDocument();
    expect(panel).toHaveTextContent("CALCULATE(SUM('Orders'[Sales])");
    expect(panel).toHaveTextContent('report shows 40,194.25, exact match');
  });

  it('explains what probably happened to a number that could not be reproduced', () => {
    render(<CellDetailPanel cell={report().cells[1]} />);
    expect(screen.getByTestId('cell-hint')).toHaveTextContent('Two digits look swapped');
    expect(screen.getByText(/Closest:/)).toHaveTextContent('16,079.19');
    expect(screen.getByText(/Closest:/)).toHaveTextContent('Sum of Sales where Region is East');
    expect(screen.queryByText('The formula')).not.toBeInTheDocument();
  });

  it('lists every formula that fits an ambiguous number', () => {
    render(<CellDetailPanel cell={report().cells[2]} />);
    expect(screen.getByText('The formulas that all give this number')).toBeInTheDocument();
    expect(screen.getByText('Number of different Customer Name where Segment is Corporate')).toBeInTheDocument();
    expect(screen.getByText('Several formulas fit')).toBeInTheDocument();
  });

  it('shows how a calculated number was checked against its own parts', () => {
    render(<CellDetailPanel cell={report().cells[3]} />);
    expect(screen.getByText('How the report calculated it')).toBeInTheDocument();
    expect(screen.getByText(/which matches/)).toBeInTheDocument();
    expect(screen.queryByText('Recomputed on the data')).not.toBeInTheDocument();
  });

  it('warns that a cleaned-data match cannot go into Power BI', () => {
    render(<CellDetailPanel cell={cell('S!B3', { basis: 'cleaned', writable: false })} />);
    expect(screen.getByRole('note')).toHaveTextContent('cannot be added to Power BI');
  });
});

describe('SummaryBar', () => {
  it('states the result and the suspected mistakes in words', () => {
    render(<SummaryBar summary={report().summary} warnings={[]} filename="legacy.xlsx" />);
    const bar = screen.getByTestId('reverse-summary');
    expect(bar).toHaveTextContent('33.3% reproduced');
    expect(bar).toHaveTextContent('1 of the 3 numbers that come from the data');
    expect(bar).toHaveTextContent('1 suspected mistake to check');
    expect(screen.getByLabelText('Results by status')).toHaveTextContent('1 not reproduced');
  });

  it('is quiet when there is nothing to suspect, and loud when the time ran out', () => {
    const summary = { ...report().summary, suspected_errors: 0, budget_exhausted: true };
    render(<SummaryBar summary={summary} warnings={['Only the first 100 rows were read.']} filename="x.csv" />);
    expect(screen.queryByText(/suspected/)).not.toBeInTheDocument();
    expect(screen.getByText(/time limit ran out/)).toBeInTheDocument();
    expect(screen.getByText('Only the first 100 rows were read.')).toBeInTheDocument();
  });
});

const baseProps = (over: Partial<MigrationPanelProps> = {}): MigrationPanelProps => ({
  report: report(),
  mode: 'dataset',
  working: null,
  outcome: null,
  actionError: null,
  onCheck: vi.fn(),
  onApply: vi.fn(),
  onExport: vi.fn(),
  ...over,
});

describe('MigrationPanel', () => {
  it('lists each planned measure with its DAX and how to use it', () => {
    render(<MigrationPanel {...baseProps()} />);
    const item = screen.getByTestId('measure-rep1:total-sales');
    expect(item).toHaveTextContent('Total Sales');
    expect(item).toHaveTextContent('one measure for 2 numbers');
    expect(item).toHaveTextContent("SUM('Orders'[Sales])");
    expect(item).toHaveTextContent('Put Region and Year of Order Date on the visual');
    expect(screen.getByText(/1 measure reproduces 2 of the report's numbers/)).toBeInTheDocument();
  });

  it('offers downloads, not Power BI buttons, for an uploaded dataset', async () => {
    const onExport = vi.fn();
    render(<MigrationPanel {...baseProps({ onExport })} />);
    await userEvent.click(screen.getByRole('button', { name: /Download .bim/ }));
    expect(onExport).toHaveBeenCalledWith('bim');
    expect(screen.queryByRole('button', { name: /Add proven measures/ })).not.toBeInTheDocument();
  });

  it('checks and then adds in live mode', async () => {
    const onCheck = vi.fn();
    const onApply = vi.fn();
    render(<MigrationPanel {...baseProps({ mode: 'live', onCheck, onApply })} />);
    await userEvent.click(screen.getByRole('button', { name: 'Check against Power BI' }));
    await userEvent.click(screen.getByRole('button', { name: 'Add proven measures to Power BI' }));
    expect(onCheck).toHaveBeenCalledOnce();
    expect(onApply).toHaveBeenCalledOnce();
    expect(screen.queryByRole('button', { name: /Download/ })).not.toBeInTheDocument();
  });

  it('refuses to offer writing when only a sample of the table was read', () => {
    render(<MigrationPanel {...baseProps({ mode: 'live', report: report({ sampled: true }) })} />);
    expect(screen.getByRole('button', { name: 'Add proven measures to Power BI' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Check against Power BI' })).toBeDisabled();
    expect(screen.getByText(/Only part of this table was read/)).toBeInTheDocument();
  });

  it('says so when nothing could be proven', () => {
    const empty = report({ plan: { table: 'Orders', measures: [], not_writable: [] } });
    render(<MigrationPanel {...baseProps({ mode: 'live', report: empty })} />);
    expect(screen.getByText('Nothing was proven well enough to turn into a measure.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add proven measures to Power BI' })).toBeDisabled();
  });

  it('mentions numbers left out because they only match the cleaned data', () => {
    const plan = { ...report().plan!, not_writable: [{ cell: 'S!B3', reason: 'cleaned' }] };
    render(<MigrationPanel {...baseProps({ report: report({ plan }) })} />);
    expect(screen.getByRole('note')).toHaveTextContent('1 reproduced number(s) are left out');
  });

  it('shows what Power BI did, with the existing apply summary', () => {
    const outcome = {
      dry_run: true,
      saved: false,
      reminder: null,
      results: [{ table: 'Orders', kpi_id: 'rep1:total-sales', name: 'Total Sales', status: 'verified' as const, reason: 'agrees', engine_value: 5, computed_value: 5 }],
    };
    render(<MigrationPanel {...baseProps({ mode: 'live', outcome })} />);
    expect(screen.getByTestId('apply-outcome')).toHaveTextContent('Matches Power BI');
    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();
  });

  it('shows an action error', () => {
    render(<MigrationPanel {...baseProps({ mode: 'live', actionError: 'The server is gone.' })} />);
    expect(screen.getByRole('alert')).toHaveTextContent('The server is gone.');
  });
});
