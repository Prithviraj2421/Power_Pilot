import React, { useState } from 'react';
import { Sparkles, CheckCircle2, AlertCircle, Command, Search } from 'lucide-react';
import { useAnalysisStore } from '../../store/useAnalysisStore';
import { Badge } from '../ui/Badge';
import { CommandPalette } from '../ui/CommandPalette';

export const Navbar: React.FC = () => {
  const { currentDatasetName, intelligenceResult, status } = useAnalysisStore();
  const [isCommandOpen, setIsCommandOpen] = useState(false);

  const domain = intelligenceResult?.dataset_profile?.detected_domain || 'Unclassified';
  const confidence = intelligenceResult?.dataset_profile?.domain_confidence || 0;
  const grade = intelligenceResult?.quality_report?.grade || 'A';

  return (
    <>
      <header className="h-16 bg-card/70 backdrop-blur-xl border-b border-white/10 px-6 flex items-center justify-between sticky top-0 z-20">
        {/* Left Dataset Status Indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-surface/80 border border-white/10 rounded-xl">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-xs font-semibold text-gray-300">Dataset:</span>
            <span className="text-xs font-bold text-white max-w-[200px] truncate">
              {currentDatasetName || 'No Dataset Selected'}
            </span>
          </div>

          {currentDatasetName && (
            <Badge variant="primary" size="sm">
              {domain.toUpperCase()} ({(confidence * 100).toFixed(0)}%)
            </Badge>
          )}

          {intelligenceResult?.quality_report && (
            <Badge variant="success" size="sm">
              GRADE {grade}
            </Badge>
          )}
        </div>

        {/* Center/Right Actions & Command Palette Trigger */}
        <div className="flex items-center gap-3">
          {/* Quick Command Trigger Badge (Linear Style) */}
          <button
            onClick={() => setIsCommandOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface/80 hover:bg-surface-hover border border-white/10 rounded-xl text-xs font-medium text-gray-300 hover:text-white transition-all cursor-pointer group"
          >
            <Search className="w-3.5 h-3.5 text-gray-400 group-hover:text-primary transition-colors" />
            <span>Search or jump to...</span>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-white/10 border border-white/10 rounded text-[10px] font-mono text-gray-300">
              <Command className="w-2.5 h-2.5" />K
            </kbd>
          </button>

          {/* Status Indicators */}
          {status === 'analyzing' && (
            <div className="flex items-center gap-2 text-xs text-primary font-semibold bg-primary-muted px-3 py-1.5 rounded-xl border border-primary/30 animate-pulse">
              <Sparkles className="w-3.5 h-3.5 animate-spin" />
              <span>Analyzing Intelligence...</span>
            </div>
          )}
          {status === 'success' && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/30">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Pipeline Stage Verified</span>
            </div>
          )}
          {status === 'error' && (
            <div className="flex items-center gap-1.5 text-xs text-red-400 font-semibold bg-red-500/10 px-3 py-1.5 rounded-xl border border-red-500/30">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Pipeline Error</span>
            </div>
          )}
        </div>
      </header>

      {/* Global Command Palette Modal */}
      <CommandPalette isOpen={isCommandOpen} onClose={() => setIsCommandOpen(false)} />
    </>
  );
};
