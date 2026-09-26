import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Bot, Database, Send, Sparkles } from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import { useAnalysisStore } from '../../../store/useAnalysisStore';
import { CopilotService } from '../../../services/copilotService';
import { CopilotChatMessage, ChatMessage } from './CopilotChatMessage';
import { CopilotQuickPrompts } from './CopilotQuickPrompts';

/**
 * AI Copilot.
 *
 * Every answer comes from the backend CopilotEngine, which reasons only over the
 * registered dataset's computed analysis. It has no generative freedom, so it
 * cannot invent a figure that is not in the data.
 *
 * This view previously faked its answers with a setTimeout and hardcoded strings
 * ("Sales volume correlated +0.88 with regional promotions", "95.8% Grade A+")
 * that were returned regardless of the dataset. Nothing is fabricated here now:
 * if the backend cannot answer, the failure is shown rather than papered over.
 */
export const CopilotView: React.FC = () => {
  const { datasetId, currentDatasetName, intelligenceResult } = useAnalysisStore();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const streamEndRef = useRef<HTMLDivElement>(null);

  /** Opening message, built from this dataset's real analysis values. */
  const welcomeMessage = useMemo<ChatMessage | null>(() => {
    if (!intelligenceResult?.dataset_profile) return null;

    const profile = intelligenceResult.dataset_profile;
    const quality = intelligenceResult.quality_report;
    const kpiCount = intelligenceResult.kpi_report?.primary_kpis?.length ?? 0;
    const decisionCount = intelligenceResult.decision_report?.primary_decisions?.length ?? 0;

    const grounding: string[] = [
      `${profile.total_rows} rows across ${profile.total_columns} columns`,
      `Classified as ${profile.detected_domain.toUpperCase()}` +
        (profile.domain_confidence
          ? ` at ${(profile.domain_confidence * 100).toFixed(0)}% confidence`
          : ''),
    ];
    if (quality) {
      grounding.push(
        `Data quality ${quality.grade} (${quality.overall_score.toFixed(1)}%), ` +
          `${quality.total_issues_count} issue(s) detected`
      );
    }
    if (kpiCount) grounding.push(`${kpiCount} primary KPI measure(s) available`);
    if (decisionCount) grounding.push(`${decisionCount} strategic decision(s) available`);

    return {
      id: 'welcome',
      sender: 'assistant',
      content:
        `I'm grounded in ${currentDatasetName ?? 'this dataset'}. ` +
        'Ask about data quality, KPIs and DAX measures, relationships, or what to do next. ' +
        'Every answer is derived from this dataset’s analysis.',
      evidence: grounding,
      suggested_followups: [
        'What are my key KPIs?',
        'How is the data quality?',
        'What should management do next?',
      ],
    };
  }, [intelligenceResult, currentDatasetName]);

  const visibleMessages = useMemo(
    () => (welcomeMessage ? [welcomeMessage, ...messages] : messages),
    [welcomeMessage, messages]
  );

  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [visibleMessages.length, isAsking]);

  const handleSend = async (promptOverride?: string) => {
    const question = (promptOverride ?? inputQuery).trim();
    if (!question || isAsking) return;

    if (!datasetId) {
      setErrorMessage('No active dataset. Upload and analyze a CSV first.');
      return;
    }

    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, sender: 'user', content: question },
    ]);
    if (!promptOverride) setInputQuery('');
    setErrorMessage(null);
    setIsAsking(true);

    try {
      const response = await CopilotService.askCopilot(datasetId, question);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          sender: 'assistant',
          content: response.answer,
          intent: response.intent,
          evidence: response.evidence,
          recommended_actions: response.recommended_actions,
          suggested_followups: response.suggested_followups,
        },
      ]);
    } catch (err) {
      // Surface the failure instead of inventing an answer.
      setErrorMessage(
        err instanceof Error ? err.message : 'The Copilot could not answer that question.'
      );
    } finally {
      setIsAsking(false);
    }
  };

  if (!datasetId || !intelligenceResult) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <EmptyState
          title="No Active Dataset"
          description="The Copilot answers only from an analyzed dataset's intelligence. Upload and analyze a CSV to start asking questions."
        />
      </div>
    );
  }

  const quality = intelligenceResult.quality_report;
  const profile = intelligenceResult.dataset_profile;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
      {/* Conversation */}
      <div className="lg:col-span-3 space-y-4">
        <Card glass className="p-6 min-h-[500px] flex flex-col justify-between">
          <div className="overflow-y-auto max-h-[560px] pr-2">
            {visibleMessages.map((message) => (
              <CopilotChatMessage
                key={message.id}
                message={message}
                onFollowupClick={(prompt) => void handleSend(prompt)}
              />
            ))}

            {isAsking && (
              <div className="flex items-center gap-3 p-4 text-xs text-gray-400">
                <div className="p-2 bg-primary/20 text-primary rounded-xl border border-primary/30">
                  <Bot className="w-4 h-4 animate-pulse" />
                </div>
                <span>Querying the dataset&apos;s intelligence…</span>
              </div>
            )}

            {errorMessage && (
              <div
                role="alert"
                className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl"
              >
                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                <div>
                  <span className="block text-sm font-semibold text-red-300">
                    Copilot unavailable
                  </span>
                  <span className="block text-xs text-red-200/80 mt-0.5">{errorMessage}</span>
                </div>
              </div>
            )}

            <div ref={streamEndRef} />
          </div>

          <div className="mt-4 space-y-3 pt-4 border-t border-white/10">
            <CopilotQuickPrompts
              onSelectPrompt={(prompt) => void handleSend(prompt)}
              disabled={isAsking}
            />

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void handleSend();
              }}
              className="flex items-center gap-3"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(event) => setInputQuery(event.target.value)}
                disabled={isAsking}
                placeholder="Ask about data quality, KPIs, relationships, or recommended actions…"
                className="flex-1 bg-surface border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-60"
              />
              <Button
                type="submit"
                isLoading={isAsking}
                disabled={!inputQuery.trim()}
                leftIcon={<Send className="w-4 h-4" />}
              >
                Send
              </Button>
            </form>
          </div>
        </Card>
      </div>

      {/* Grounding panel — real values only, no placeholder fallbacks */}
      <div className="space-y-4">
        <Card glass className="p-5">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Database className="w-4 h-4 text-primary" />
            <span>Grounded In</span>
          </h4>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between gap-2 text-gray-300">
              <span className="shrink-0">Dataset:</span>
              <span className="font-mono text-gray-200 truncate" title={currentDatasetName ?? ''}>
                {currentDatasetName ?? '—'}
              </span>
            </div>

            <div className="flex items-center justify-between text-gray-300">
              <span>Domain:</span>
              <Badge variant="primary" size="sm">
                {profile.detected_domain.toUpperCase()}
              </Badge>
            </div>

            {quality && (
              <div className="flex items-center justify-between text-gray-300">
                <span>Quality:</span>
                <Badge variant="success" size="sm">
                  {quality.grade} · {quality.overall_score.toFixed(1)}%
                </Badge>
              </div>
            )}

            <div className="flex items-center justify-between text-gray-300">
              <span>Shape:</span>
              <span className="font-mono text-gray-200">
                {profile.total_rows} × {profile.total_columns}
              </span>
            </div>
          </div>
        </Card>

        <Card glass className="p-5">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <span>How this works</span>
          </h4>
          <p className="text-[11px] text-gray-400 leading-relaxed">
            Answers are computed from this dataset&apos;s analysis on the server — quality
            scores, KPI definitions, correlations, anomalies and decisions. The Copilot
            cannot generate figures that are not present in the data, so it will say when
            something is unknown rather than guess.
          </p>
        </Card>
      </div>
    </div>
  );
};
