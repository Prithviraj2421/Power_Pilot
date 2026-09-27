import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CopilotView } from './CopilotView';
import { CopilotService } from '../../../services/copilotService';
import { useAnalysisStore } from '../../../store/useAnalysisStore';
import type { MasterIntelligenceResult } from '../../../types';

vi.mock('../../../services/copilotService');

const intelligenceResult = {
  dataset_profile: {
    dataset_name: 'retail.csv',
    total_rows: 60,
    total_columns: 11,
    detected_domain: 'retail',
    domain_confidence: 0.8,
    columns: [],
  },
  quality_report: { grade: 'A', overall_score: 91.7, total_issues_count: 8 },
  kpi_report: { primary_kpis: [{ name: 'Total Sales Revenue' }] },
  decision_report: { primary_decisions: [{ action_title: 'Reallocate inventory' }] },
  detected_entities: [],
} as unknown as MasterIntelligenceResult;

const loadDataset = () =>
  useAnalysisStore.setState({
    status: 'success',
    datasetId: 'ds-123',
    currentDatasetName: 'retail.csv',
    intelligenceResult,
    datasetRecord: null,
    errorMessage: null,
  });

const clearDataset = () =>
  useAnalysisStore.setState({
    status: 'idle',
    datasetId: null,
    currentDatasetName: null,
    intelligenceResult: null,
    datasetRecord: null,
    errorMessage: null,
  });

const answer = {
  status: 'success' as const,
  dataset_id: 'ds-123',
  dataset_name: 'retail.csv',
  query: 'Why did profit decrease?',
  answer: 'unit_price is decreasing over order_date.',
  intent: 'WHY_DECREASE',
  evidence: ['unit_price is decreasing over order_date (-92.4% first to last)'],
  recommended_actions: ['Reallocate Inventory to High-Margin Product Categories'],
  suggested_followups: ['What should management do next?'],
  source: 'llm' as const,
  verified: true,
  verification_note: 'All 1 numeric claim(s) trace to the analysis.',
  fallback_reason: null,
};

describe('CopilotView', () => {
  beforeEach(() => {
    clearDataset();
  });

  it('prompts for a dataset when none is loaded', () => {
    render(<CopilotView />);

    expect(screen.getByText('No Active Dataset')).toBeInTheDocument();
  });

  it('builds its opening message from the real analysis, not hardcoded values', () => {
    // The previous implementation greeted every dataset with "13 columns",
    // "95.8% Grade A+" and "98% confidence" regardless of the data.
    loadDataset();
    render(<CopilotView />);

    expect(screen.getByText(/60 rows across 11 columns/)).toBeInTheDocument();
    expect(screen.getByText(/Classified as RETAIL at 80% confidence/)).toBeInTheDocument();
    expect(screen.getByText(/Data quality A \(91\.7%\), 8 issue\(s\) detected/)).toBeInTheDocument();
    expect(screen.queryByText(/95\.8/)).not.toBeInTheDocument();
  });

  it('sends the question to the backend with the dataset id', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue(answer);
    loadDataset();
    render(<CopilotView />);

    await userEvent.type(
      screen.getByPlaceholderText(/Ask about data quality/),
      'Why did profit decrease?'
    );
    await userEvent.click(screen.getByRole('button', { name: /Send/ }));

    await waitFor(() =>
      expect(CopilotService.askCopilot).toHaveBeenCalledWith('ds-123', 'Why did profit decrease?')
    );
  });

  it('renders the backend answer, intent, evidence and actions', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue(answer);
    loadDataset();
    render(<CopilotView />);

    await userEvent.type(screen.getByPlaceholderText(/Ask about data quality/), 'why');
    await userEvent.click(screen.getByRole('button', { name: /Send/ }));

    expect(await screen.findByText(answer.answer)).toBeInTheDocument();
    expect(screen.getByText('WHY_DECREASE')).toBeInTheDocument();
    expect(screen.getByText(`• ${answer.evidence[0]}`)).toBeInTheDocument();
    expect(screen.getByText(`→ ${answer.recommended_actions[0]}`)).toBeInTheDocument();
  });

  it('shows the question in the transcript', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue(answer);
    loadDataset();
    render(<CopilotView />);

    await userEvent.type(screen.getByPlaceholderText(/Ask about data quality/), 'my question');
    await userEvent.click(screen.getByRole('button', { name: /Send/ }));

    expect(await screen.findByText('my question')).toBeInTheDocument();
  });

  it('surfaces a backend failure instead of inventing an answer', async () => {
    vi.mocked(CopilotService.askCopilot).mockRejectedValue(new Error('Backend unavailable'));
    loadDataset();
    render(<CopilotView />);

    await userEvent.type(screen.getByPlaceholderText(/Ask about data quality/), 'why');
    await userEvent.click(screen.getByRole('button', { name: /Send/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable');
    expect(screen.getByText('Copilot unavailable')).toBeInTheDocument();
  });

  it('sends a quick prompt without typing', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue(answer);
    loadDataset();
    render(<CopilotView />);

    await userEvent.click(screen.getByRole('button', { name: 'Why did profit decrease?' }));

    await waitFor(() =>
      expect(CopilotService.askCopilot).toHaveBeenCalledWith('ds-123', 'Why did profit decrease?')
    );
  });

  it('sends a suggested followup when clicked', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue(answer);
    loadDataset();
    render(<CopilotView />);

    await userEvent.click(screen.getByRole('button', { name: 'What are my key KPIs?' }));

    await waitFor(() =>
      expect(CopilotService.askCopilot).toHaveBeenCalledWith('ds-123', 'What are my key KPIs?')
    );
  });

  it('does not send an empty question', async () => {
    loadDataset();
    render(<CopilotView />);

    expect(screen.getByRole('button', { name: /Send/ })).toBeDisabled();
    expect(CopilotService.askCopilot).not.toHaveBeenCalled();
  });

  it('shows the grounding panel with real values only', () => {
    loadDataset();
    render(<CopilotView />);

    expect(screen.getByText('A · 91.7%')).toBeInTheDocument();
    expect(screen.getByText('60 × 11')).toBeInTheDocument();
    // The old sidebar fell back to literal '95.8' and 'RETAIL' when data was absent.
    expect(screen.queryByText('95.8%')).not.toBeInTheDocument();
  });
  it('says which engine produced the answer', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue(answer);
    loadDataset();
    render(<CopilotView />);

    await userEvent.type(screen.getByPlaceholderText(/Ask about data quality/), 'why');
    await userEvent.click(screen.getByRole('button', { name: /Send/ }));

    expect(await screen.findByText(/every figure verified against it/)).toBeInTheDocument();
  });

  it('surfaces why the language model was skipped', async () => {
    vi.mocked(CopilotService.askCopilot).mockResolvedValue({
      ...answer,
      source: 'rules' as const,
      fallback_reason: 'LLM answering is not configured on this server.',
    });
    loadDataset();
    render(<CopilotView />);

    await userEvent.click(screen.getByRole('button', { name: 'What are my key KPIs?' }));

    expect(
      await screen.findByText(/not configured on this server/)
    ).toBeInTheDocument();
  });
});
