import React from 'react';
import { Sparkles, User, CheckCircle2, AlertCircle, ShieldCheck } from 'lucide-react';
import { Badge } from '../../../components/ui/Badge';
import { cn } from '../../../utils/cn';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  intent?: string;
  evidence?: string[];
  recommended_actions?: string[];
  suggested_followups?: string[];
  /** Which engine produced this answer. */
  source?: 'llm' | 'rules';
  /** Set when the language model was skipped or its answer was rejected. */
  fallbackReason?: string | null;
}

export const CopilotChatMessage: React.FC<{
  message: ChatMessage;
  onFollowupClick?: (prompt: string) => void;
}> = ({ message, onFollowupClick }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={cn('flex gap-4 p-4 rounded-xl mb-3', isUser ? 'bg-surface/50 border border-border' : 'bg-card border border-primary/30 shadow-glass')}>
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5',
          isUser ? 'bg-surface text-gray-400 border border-border' : 'bg-primary/20 text-primary border border-primary/30'
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      <div className="flex-1 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">
            {isUser ? 'You' : 'PowerPilot AI Copilot'}
          </span>
          {message.intent && (
            <Badge variant="purple" size="sm">
              {message.intent}
            </Badge>
          )}
        </div>

        <p className="text-sm text-gray-100 leading-relaxed">{message.content}</p>

        {/* Provenance. A reader should never have to guess whether an answer was
            generated or composed from the analysis directly. */}
        {!isUser && message.source && (
          <div className="flex items-start gap-2 text-[11px] text-gray-500">
            <ShieldCheck className="w-3.5 h-3.5 mt-px shrink-0 text-gray-500" />
            <span>
              {message.source === 'llm'
                ? 'Generated from this dataset’s analysis; every figure verified against it.'
                : 'Composed directly from the computed analysis.'}
              {message.fallbackReason ? ` ${message.fallbackReason}` : ''}
            </span>
          </div>
        )}

        {/* Supporting Evidence */}
        {message.evidence && message.evidence.length > 0 && (
          <div className="p-3 bg-surface/80 rounded-lg border border-border text-xs space-y-1">
            <span className="font-semibold text-gray-400 uppercase tracking-wider block mb-1 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5 text-primary" />
              Supporting Intelligence Proof Points:
            </span>
            {message.evidence.map((ev, idx) => (
              <p key={idx} className="text-gray-300">
                • {ev}
              </p>
            ))}
          </div>
        )}

        {/* Recommended Actions */}
        {message.recommended_actions && message.recommended_actions.length > 0 && (
          <div className="p-3 bg-success-muted/10 rounded-lg border border-success/20 text-xs space-y-1">
            <span className="font-semibold text-success uppercase tracking-wider block mb-1 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-success" />
              Recommended Action Plan:
            </span>
            {message.recommended_actions.map((act, idx) => (
              <p key={idx} className="text-gray-200 font-medium">
                → {act}
              </p>
            ))}
          </div>
        )}

        {/* Suggested Followups */}
        {message.suggested_followups && message.suggested_followups.length > 0 && (
          <div className="pt-2 flex flex-wrap gap-1.5">
            {message.suggested_followups.map((fup, idx) => (
              <button
                key={idx}
                onClick={() => onFollowupClick && onFollowupClick(fup)}
                className="text-xs text-primary hover:underline bg-primary-muted px-2.5 py-1 rounded-full border border-primary/20"
              >
                {fup}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
