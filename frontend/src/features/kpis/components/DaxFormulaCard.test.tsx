import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DaxFormulaCard } from './DaxFormulaCard';
import { KpiStudioView } from './KpiStudioView';
import { KPIRecommendation, KPIReport } from '../../../types';

const verified: KPIRecommendation = {
  name: 'Total Sales Revenue',
  priority: 'CRITICAL' as KPIRecommendation['priority'],
  confidence: 0.95,
  reason: 'Primary revenue metric.',
  formula: "SUM('orders'[Sales])",
  target_threshold: 'Latest month 2024-04 vs 2024-03: 1,200 vs 1,000 (+20.0%)',
  computed_value: 2297200.86,
  verified: true,
  verification_note: 'computed on 9,800 rows of the cleaned dataset',
};

describe('DaxFormulaCard', () => {
  it('shows the computed value and a Verified badge for a verified KPI', () => {
    render(<DaxFormulaCard kpi={verified} />);

    expect(screen.getByTestId('kpi-value')).toHaveTextContent('2,297,201');
    expect(screen.getByText('Verified')).toBeInTheDocument();
    expect(screen.getByTitle('computed on 9,800 rows of the cleaned dataset')).toBeInTheDocument();
    expect(screen.getByText("SUM('orders'[Sales])")).toBeInTheDocument();
  });

  it('labels the target as a baseline and shows what it is', () => {
    render(<DaxFormulaCard kpi={verified} />);

    expect(screen.getByText('Baseline:')).toBeInTheDocument();
    expect(screen.getByText(/Latest month 2024-04 vs 2024-03/)).toBeInTheDocument();
  });

  it('shows neither a value nor a badge when the KPI carries no verification', () => {
    render(<DaxFormulaCard kpi={{ ...verified, computed_value: null, verified: false }} />);

    expect(screen.queryByTestId('kpi-value')).not.toBeInTheDocument();
    expect(screen.queryByText('Verified')).not.toBeInTheDocument();
  });
});

describe('KpiStudioView rejected KPIs', () => {
  const report: KPIReport = {
    primary_kpis: [verified],
    secondary_kpis: [],
    all_kpis: [verified],
    rejected_kpis: [
      { ...verified, name: 'Average Order Value (AOV)', verified: false, computed_value: null, verification_note: "column 'Order ID' is not in the dataset" },
    ],
    domain: 'retail' as KPIReport['domain'],
    total_kpis_recommended: 1,
  };

  it('lists rejected KPIs with the reason, apart from the measures', () => {
    render(<KpiStudioView report={report} />);

    const rejected = screen.getByTestId('rejected-kpis');
    expect(rejected).toHaveTextContent('Average Order Value (AOV)');
    expect(rejected).toHaveTextContent("column 'Order ID' is not in the dataset");
  });

  it('omits the section when nothing was rejected', () => {
    render(<KpiStudioView report={{ ...report, rejected_kpis: [] }} />);

    expect(screen.queryByTestId('rejected-kpis')).not.toBeInTheDocument();
  });
});
