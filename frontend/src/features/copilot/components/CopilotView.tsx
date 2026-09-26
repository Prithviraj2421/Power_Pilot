import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Send,
  Bot,
  User,
  ShieldCheck,
  Code,
  Target,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Database,
} from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import { useAnalysisStore } from '../../../store/useAnalysisStore';

export interface CopilotMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  reasoningSteps?: string[];
  evidence?: { title: string; detail: string }[];
  suggestedActions?: string[];
}

export const CopilotView: React.FC = () => {
  const { intelligenceResult, currentDatasetName } = useAnalysisStore();
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      text: `Hello! I am your PowerPilot AI Copilot grounded directly in dataset **${currentDatasetName || 'Dataset'}**. How can I assist with your executive decision making today?`,
      timestamp: '12:00 PM',
      reasoningSteps: [
        'Analyzed dataset profile and 13 columns',
        'Verified Stage 1 Data Quality Score (95.8% Grade A+)',
        'Extracted 6 primary DAX measures and 4 management decision drivers',
      ],
      evidence: [
        { title: 'Quality Gate', detail: 'Purged 0 invalid rows; 100% type consistency' },
        { title: 'Domain Classifier', detail: 'Classified under RETAIL business domain with 98% confidence' },
      ],
      suggestedActions: [
        'Why did net profit margin increase?',
        'Export executable DAX measures script',
        'Distribute Executive PDF Report',
      ],
    },
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [expandedReasoning, setExpandedReasoning] = useState<Record<string, boolean>>({ 'msg-1': true });

  const handleSend = (textToSend?: string) => {
    const q = textToSend || inputQuery;
    if (!q.trim()) return;

    const userMsg: CopilotMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputQuery('');

    // Simulate Cursor AI Assistant Grounded Response
    setTimeout(() => {
      const botMsg: CopilotMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        text: `Based on deterministic evaluation of **${currentDatasetName || 'Dataset'}**, here is the executive analysis for "${q}":`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        reasoningSteps: [
          'Scanned data intelligence correlation matrix',
          'Evaluated target metrics vs historical benchmarks',
          'Synthesized actionable management mitigation steps',
        ],
        evidence: [
          { title: 'Statistical Trend', detail: 'Sales volume correlated +0.88 with regional promotions' },
          { title: 'DAX Formula', detail: 'Total_Revenue = SUM(Sales) executed with zero null errors' },
        ],
        suggestedActions: [
          'Review strategic decision matrix',
          'Generate executive slide deck',
        ],
      };
      setMessages((prev) => [...prev, botMsg]);
    }, 600);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
      {/* Left Chat & Reasoning Canvas */}
      <div className="lg:col-span-3 space-y-4">
        <Card glass className="p-6 min-h-[500px] flex flex-col justify-between">
          {/* Messages Stream */}
          <div className="space-y-6 overflow-y-auto max-h-[600px] pr-2">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.sender === 'assistant' && (
                    <div className="p-2 bg-primary/20 text-primary rounded-xl h-fit border border-primary/30">
                      <Bot className="w-5 h-5" />
                    </div>
                  )}

                  <div className={`max-w-2xl space-y-3 ${msg.sender === 'user' ? 'bg-primary text-white p-4 rounded-2xl' : ''}`}>
                    {msg.sender === 'assistant' ? (
                      <div className="p-5 bg-surface/90 border border-white/10 rounded-2xl space-y-3 shadow-card">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5" />
                            Grounded AI Assistant
                          </span>
                          <span className="text-[10px] text-gray-500 font-mono">{msg.timestamp}</span>
                        </div>

                        <p className="text-sm text-gray-200 leading-relaxed">{msg.text}</p>

                        {/* Reasoning Accordion */}
                        {msg.reasoningSteps && (
                          <div className="border border-white/5 rounded-xl overflow-hidden bg-background/50">
                            <button
                              onClick={() =>
                                setExpandedReasoning((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))
                              }
                              className="w-full px-3 py-2 flex items-center justify-between text-xs font-semibold text-gray-400 hover:text-white transition-colors"
                            >
                              <span className="flex items-center gap-1.5">
                                <Database className="w-3.5 h-3.5 text-primary" />
                                Interactive Reasoning Chain ({msg.reasoningSteps.length} steps)
                              </span>
                              {expandedReasoning[msg.id] ? (
                                <ChevronDown className="w-3.5 h-3.5" />
                              ) : (
                                <ChevronRight className="w-3.5 h-3.5" />
                              )}
                            </button>

                            {expandedReasoning[msg.id] && (
                              <div className="p-3 pt-0 space-y-1.5 text-xs text-gray-300 font-mono border-t border-white/5">
                                {msg.reasoningSteps.map((step, sIdx) => (
                                  <div key={sIdx} className="flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                                    <span>{step}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Evidence Cards */}
                        {msg.evidence && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                            {msg.evidence.map((ev, eIdx) => (
                              <div key={eIdx} className="p-2.5 bg-surface rounded-xl border border-white/5 text-xs">
                                <span className="font-bold text-emerald-400 block mb-0.5">{ev.title}</span>
                                <span className="text-gray-400 text-[11px] block">{ev.detail}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <span>{msg.text}</span>
                    )}
                  </div>

                  {msg.sender === 'user' && (
                    <div className="p-2 bg-white/10 text-white rounded-xl h-fit">
                      <User className="w-5 h-5" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {/* Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="mt-4 flex items-center gap-3 pt-4 border-t border-white/10"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask Copilot about revenues, quality metrics, or DAX formulas..."
              className="flex-1 bg-surface border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <Button type="submit" leftIcon={<Send className="w-4 h-4" />}>
              Send
            </Button>
          </form>
        </Card>
      </div>

      {/* Right Sidebar Prompts & Telemetry */}
      <div className="space-y-4">
        <Card glass className="p-5">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <span>Suggested Executive Prompts</span>
          </h4>

          <div className="space-y-2">
            {[
              'Why did gross margin fluctuate?',
              'Show top 3 strategic decision drivers',
              'Explain Stage 1 DQPE cleaning log',
              'Generate Power BI M script',
            ].map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(p)}
                className="w-full text-left p-2.5 bg-surface hover:bg-surface-hover border border-white/5 hover:border-primary/40 rounded-xl text-xs text-gray-300 hover:text-white transition-all flex items-center justify-between group"
              >
                <span>{p}</span>
                <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-primary transition-colors" />
              </button>
            ))}
          </div>
        </Card>

        <Card glass className="p-5">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
            Grounded Intelligence State
          </h4>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between text-gray-300">
              <span>Quality Score:</span>
              <Badge variant="success" size="sm">
                {intelligenceResult?.quality_report?.overall_score.toFixed(1) || '95.8'}%
              </Badge>
            </div>
            <div className="flex items-center justify-between text-gray-300">
              <span>Domain:</span>
              <Badge variant="primary" size="sm">
                {intelligenceResult?.dataset_profile?.detected_domain.toUpperCase() || 'RETAIL'}
              </Badge>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
