import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DashboardTabsView } from './DashboardTabsView';
import type { DashboardTab, KPIRecommendation } from '../../../types';

const makeTab = (id: string, name: string, widgetCount = 2): DashboardTab => ({
  tab_id: id,
  tab_name: name,
  description: `${name} description`,
  widgets: Array.from({ length: widgetCount }, (_, index) => ({
    widget_id: `${id}-w${index}`,
    title: `${name} widget ${index}`,
    widget_type: 'BAR_CHART',
    metric_column: 'sales_amount',
    dimension_column: 'category',
    grid_row: index,
    grid_col: 0,
    grid_width: 6,
    grid_height: 4,
  })),
});

const kpis: KPIRecommendation[] = [
  {
    name: 'Total Sales Revenue',
    priority: 'CRITICAL',
    confidence: 0.95,
    reason: 'Top-line growth',
    formula: "SUM('Sales'[Revenue])",
    target_threshold: '> +5% MoM',
    business_impact: 'Direct measure of commercial growth',
  } as KPIRecommendation,
];

describe('DashboardTabsView', () => {
  it('renders every recommended tab in the switcher', () => {
    const tabs = [makeTab('t1', 'Executive Summary'), makeTab('t2', 'Product Performance')];

    render(<DashboardTabsView tabs={tabs} primaryKpis={kpis} />);

    expect(screen.getByRole('tab', { name: /Executive Summary/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Product Performance/ })).toBeInTheDocument();
    expect(screen.getByText('2 Dashboards')).toBeInTheDocument();
  });

  it('shows the first tab by default', () => {
    const tabs = [makeTab('t1', 'Executive Summary'), makeTab('t2', 'Product Performance')];

    render(<DashboardTabsView tabs={tabs} primaryKpis={kpis} />);

    expect(screen.getByRole('tab', { name: /Executive Summary/ })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  it('switches to a second tab on click', async () => {
    // The regression this component exists for: tabs beyond the first used to be
    // computed by the Dashboard Engine and then silently discarded by the UI.
    const tabs = [makeTab('t1', 'Executive Summary'), makeTab('t2', 'Product Performance')];
    render(<DashboardTabsView tabs={tabs} primaryKpis={kpis} />);

    await userEvent.click(screen.getByRole('tab', { name: /Product Performance/ }));

    expect(screen.getByRole('tab', { name: /Product Performance/ })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByText('Product Performance description')).toBeInTheDocument();
  });

  it('hides the switcher when only one tab is recommended', () => {
    render(<DashboardTabsView tabs={[makeTab('t1', 'Only Tab')]} primaryKpis={kpis} />);

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
    expect(screen.getByText('Only Tab')).toBeInTheDocument();
  });

  it('shows each tab widget count', () => {
    const tabs = [makeTab('t1', 'First', 3), makeTab('t2', 'Second', 5)];

    render(<DashboardTabsView tabs={tabs} primaryKpis={kpis} />);

    expect(screen.getByRole('tab', { name: /First/ })).toHaveTextContent('3');
    expect(screen.getByRole('tab', { name: /Second/ })).toHaveTextContent('5');
  });

  it('renders an empty state when the engine recommended no layout', () => {
    render(<DashboardTabsView tabs={[]} primaryKpis={kpis} />);

    expect(screen.getByText('No Dashboard Layout Recommended')).toBeInTheDocument();
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });

  it('falls back to the first tab when a new dataset has fewer tabs', () => {
    const { rerender } = render(
      <DashboardTabsView
        tabs={[makeTab('t1', 'One'), makeTab('t2', 'Two'), makeTab('t3', 'Three')]}
        primaryKpis={kpis}
      />
    );

    rerender(<DashboardTabsView tabs={[makeTab('t1', 'One')]} primaryKpis={kpis} />);

    // Without the index guard this would point past the end and render nothing.
    expect(screen.getByText('One')).toBeInTheDocument();
  });
});
