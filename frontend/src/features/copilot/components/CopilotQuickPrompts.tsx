import React from 'react';
import { Sparkles } from 'lucide-react';
import { Chip } from '../../../components/ui/Chip';

export interface CopilotQuickPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const QUICK_PROMPTS = [
  "Why did profit decrease?",
  "Show sales by region.",
  "What should management do?",
  "Which KPIs are failing benchmarks?",
  "Give me an executive briefing summary.",
];

export const CopilotQuickPrompts: React.FC<CopilotQuickPromptsProps> = ({
  onSelectPrompt,
  disabled,
}) => {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider mr-1">
        <Sparkles className="w-3.5 h-3.5 text-primary" />
        <span>Suggested Prompts:</span>
      </div>
      {QUICK_PROMPTS.map((prompt, idx) => (
        <button
          key={idx}
          disabled={disabled}
          onClick={() => onSelectPrompt(prompt)}
          className="text-xs bg-surface border border-border hover:border-primary/50 text-gray-300 hover:text-white px-3 py-1.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
};
