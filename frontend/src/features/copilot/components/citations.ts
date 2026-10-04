import type { CopilotCitation } from '../../../services/copilotService';

/** A stored value the way a reader expects to see it next to its label. */
export function formatFactValue(citation: Pick<CopilotCitation, 'value' | 'unit'>): string {
  const { value, unit } = citation;
  if (unit === 'percent') return `${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}%`;
  if (unit === 'ratio') return `${(value * 100).toLocaleString('en-US', { maximumFractionDigits: 2 })}% (${value})`;
  if (unit === 'currency') return value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
  return value.toLocaleString('en-US', { maximumFractionDigits: 4 });
}

/** The answer split into plain text and cited figures. Overlapping or out-of-range citations are ignored, never guessed at. */
export function segmentAnswer(content: string, citations: CopilotCitation[] = []): ({ text: string } | { text: string; citation: CopilotCitation })[] {
  const usable = [...citations]
    .filter((c) => c.start >= 0 && c.end <= content.length && c.start < c.end && content.slice(c.start, c.end) === c.text)
    .sort((a, b) => a.start - b.start);
  const out: ({ text: string } | { text: string; citation: CopilotCitation })[] = [];
  let at = 0;
  for (const citation of usable) {
    if (citation.start < at) continue;
    if (citation.start > at) out.push({ text: content.slice(at, citation.start) });
    out.push({ text: citation.text, citation });
    at = citation.end;
  }
  if (at < content.length) out.push({ text: content.slice(at) });
  return out;
}
