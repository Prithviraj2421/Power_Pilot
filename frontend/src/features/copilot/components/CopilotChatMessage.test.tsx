import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CopilotChatMessage, type ChatMessage } from './CopilotChatMessage';
import { formatFactValue, segmentAnswer } from './citations';
import type { CopilotCitation } from '../../../services/copilotService';

const content = 'Revenue is $2.30M and quality is 91.7%.';
const revenue: CopilotCitation = { start: 11, end: 17, text: '$2.30M', fact_id: 'F2', label: 'Total Sales Revenue (KPI value)', value: 2297200.86, unit: 'currency' };
const quality: CopilotCitation = { start: 33, end: 38, text: '91.7%', fact_id: 'F3', label: 'Overall data quality score', value: 91.66, unit: 'percent' };

const assistant = (overrides: Partial<ChatMessage> = {}): ChatMessage => ({ id: 'a1', sender: 'assistant', content, source: 'llm', ...overrides });

describe('CopilotChatMessage citations', () => {
  it('underlines each cited figure and says what it stands for on hover', async () => {
    render(<CopilotChatMessage message={assistant({ citations: [revenue, quality] })} />);

    const figures = screen.getAllByTestId('citation');
    expect(figures.map((f) => f.getAttribute('data-fact-id'))).toEqual(['F2', 'F3']);
    expect(figures[0]).toHaveClass('underline');

    await userEvent.hover(figures[0]);
    const tip = within(figures[0]).getByRole('tooltip');
    expect(tip).toHaveTextContent('Total Sales Revenue (KPI value)');
    expect(tip).toHaveTextContent('$2,297,200.86');
    expect(figures[1]).toHaveAccessibleName('91.7%: Overall data quality score = 91.66%');
  });

  it('keeps the sentence readable around the figures', () => {
    render(<CopilotChatMessage message={assistant({ citations: [revenue, quality] })} />);
    expect(screen.getByText(/Revenue is/)).toBeInTheDocument();
    expect(screen.getByText(/ and quality is/)).toBeInTheDocument();
  });

  it('shows plain text when there are no citations (a rules answer)', () => {
    render(<CopilotChatMessage message={assistant({ source: 'rules', citations: [] })} />);
    expect(screen.queryByTestId('citation')).not.toBeInTheDocument();
    expect(screen.getByText(content)).toBeInTheDocument();
  });

  it('ignores a citation that does not match the text it points at, rather than underlining the wrong words', () => {
    render(<CopilotChatMessage message={assistant({ citations: [{ ...revenue, start: 0, end: 6 }] })} />);
    expect(screen.queryByTestId('citation')).not.toBeInTheDocument();
    expect(screen.getByText(content)).toBeInTheDocument();
  });

  it('does not decorate what the user typed', () => {
    render(<CopilotChatMessage message={{ id: 'u1', sender: 'user', content, citations: [revenue] }} />);
    expect(screen.getByText(content)).toBeInTheDocument();
  });
});

describe('segmentAnswer and formatFactValue', () => {
  it('splits into text and cited parts in order', () => {
    const parts = segmentAnswer(content, [quality, revenue]);
    expect(parts.map((p) => p.text)).toEqual(['Revenue is ', '$2.30M', ' and quality is ', '91.7%', '.']);
    expect(parts.filter((p) => 'citation' in p)).toHaveLength(2);
  });

  it('skips overlapping, out-of-range and mismatched citations', () => {
    const overlap = { ...revenue, start: 13, end: 19, text: '30M an' };
    const outside = { ...quality, start: 90, end: 95 };
    expect(segmentAnswer(content, [revenue, overlap, outside]).filter((p) => 'citation' in p)).toHaveLength(1);
    expect(segmentAnswer('', [revenue])).toEqual([]);
  });

  it('formats each unit the way a reader expects', () => {
    expect(formatFactValue({ value: 91.66, unit: 'percent' })).toBe('91.66%');
    expect(formatFactValue({ value: 0.1034, unit: 'ratio' })).toBe('10.34% (0.1034)');
    expect(formatFactValue({ value: 9994, unit: 'count' })).toBe('9,994');
    expect(formatFactValue({ value: -0.81, unit: 'coefficient' })).toBe('-0.81');
    expect(formatFactValue({ value: 1234.5, unit: 'currency' })).toBe('$1,234.50');
  });
});
