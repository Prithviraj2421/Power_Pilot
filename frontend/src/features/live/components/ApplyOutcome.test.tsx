import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ApplyOutcome } from './ApplyOutcome';
import type { ApplyResponse } from '../../../types';

const result = { table: 'Sales', kpi_id: 'ds:a', name: 'Total A', engine_value: 5, computed_value: 5, reason: 'ok' };

describe('ApplyOutcome', () => {
  it('celebrates only measures that were really written', () => {
    const outcome: ApplyResponse = {
      dry_run: false,
      saved: true,
      reminder: 'Save your report (Ctrl+S) to keep them.',
      results: [
        { ...result, status: 'written' },
        { ...result, kpi_id: 'ds:b', name: 'Total B', status: 'refused', reason: 'engine disagreed' },
      ],
    };

    render(<ApplyOutcome outcome={outcome} />);

    const celebration = screen.getByTestId('success-celebration');
    expect(celebration).toHaveTextContent('1 measure added');
    expect(celebration).not.toHaveTextContent('Total B');
  });

  it('never celebrates a dry run, even if a response were to claim something was written', () => {
    const outcome: ApplyResponse = { dry_run: true, saved: false, reminder: null, results: [{ ...result, status: 'written' }] };

    render(<ApplyOutcome outcome={outcome} />);

    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();
    expect(screen.getByText(/Nothing was added/)).toBeInTheDocument();
  });

  it('does not celebrate when nothing was written', () => {
    const outcome: ApplyResponse = { dry_run: false, saved: false, reminder: null, results: [{ ...result, status: 'refused' }] };

    render(<ApplyOutcome outcome={outcome} />);

    expect(screen.queryByTestId('success-celebration')).not.toBeInTheDocument();
  });

  it('uses the plural for several measures', () => {
    const outcome: ApplyResponse = {
      dry_run: false,
      saved: true,
      reminder: null,
      results: [{ ...result, status: 'written' }, { ...result, kpi_id: 'ds:b', name: 'Total B', status: 'written' }],
    };

    render(<ApplyOutcome outcome={outcome} />);

    expect(screen.getByTestId('success-celebration')).toHaveTextContent('2 measures added');
  });
});
