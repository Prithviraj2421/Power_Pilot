import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InsightsView } from './InsightsView';
import type { InsightReport } from '../../../types';

const base = {
  executive_summary: { dataset_name: 'x.csv', domain: 'retail', overview: 'Overview', data_quality_summary: 'Quality', major_findings: [], top_risks: [], key_opportunities: [], recommended_actions: [] },
  insights: [],
} as unknown as InsightReport;

describe('InsightsView statistical note', () => {
  it('says how much was rejected as likely noise', () => {
    const note = 'Rejected as likely noise: 12 findings (of 435 relationships tested, false discovery rate 5%).';
    render(<InsightsView report={{ ...base, noise_note: note }} />);

    const line = screen.getByTestId('noise-note');
    expect(line).toHaveTextContent('Rejected as likely noise: 12 findings');
    expect(line).toHaveTextContent('correction for the number of tests');
  });

  it('shows nothing when no tests were run', () => {
    render(<InsightsView report={{ ...base, noise_note: '' }} />);
    expect(screen.queryByTestId('noise-note')).not.toBeInTheDocument();
  });
});
