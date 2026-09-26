import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  ShieldCheck,
  Code,
  Target,
  Download,
  FileText,
  Command,
  Sparkles,
  ArrowRight,
  X,
} from 'lucide-react';
import { useUploadStore } from '../../store/useUploadStore';
import { useAnalysisStore } from '../../store/useAnalysisStore';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { file } = useUploadStore();
  const { intelligenceResult } = useAnalysisStore();
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery('');
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    {
      id: 'workspace-quality',
      label: 'Stage 1: Data Quality & Governance Audit',
      category: 'Navigation',
      icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
      action: () => {
        navigate('/workspace');
        onClose();
      },
    },
    {
      id: 'workspace-dashboard',
      label: 'Executive BI Dashboard',
      category: 'Navigation',
      icon: <LayoutDashboard className="w-4 h-4 text-blue-400" />,
      action: () => {
        navigate('/workspace');
        onClose();
      },
    },
    {
      id: 'workspace-kpi',
      label: 'KPI & Executable DAX Studio',
      category: 'Navigation',
      icon: <Code className="w-4 h-4 text-indigo-400" />,
      action: () => {
        navigate('/workspace');
        onClose();
      },
    },
    {
      id: 'workspace-decision',
      label: 'Strategic Decision Engine',
      category: 'Navigation',
      icon: <Target className="w-4 h-4 text-amber-400" />,
      action: () => {
        navigate('/workspace');
        onClose();
      },
    },
    {
      id: 'workspace-export',
      label: 'Enterprise Export & Distribution Center',
      category: 'Navigation',
      icon: <Download className="w-4 h-4 text-purple-400" />,
      action: () => {
        navigate('/workspace');
        onClose();
      },
    },
    {
      id: 'upload-new',
      label: 'Upload New Dataset (.csv / .xlsx)',
      category: 'Dataset',
      icon: <FileText className="w-4 h-4 text-primary" />,
      action: () => {
        navigate('/');
        onClose();
      },
    },
  ];

  const filteredActions = actions.filter((a) => a.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/70 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-xl bg-card border border-white/10 rounded-2xl shadow-glass overflow-hidden">
        {/* Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-white/10 gap-3">
          <Search className="w-5 h-5 text-gray-400" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search workspace..."
            className="w-full bg-transparent text-white text-sm focus:outline-none placeholder-gray-500 font-medium"
          />
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white rounded-lg transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filteredActions.length === 0 ? (
            <p className="text-xs text-gray-400 p-4 text-center">No matching commands found.</p>
          ) : (
            filteredActions.map((item) => (
              <button
                key={item.id}
                onClick={item.action}
                className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl hover:bg-white/5 text-left text-sm text-gray-200 transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-surface border border-white/5 group-hover:border-primary/40 transition-colors">
                    {item.icon}
                  </div>
                  <div>
                    <span className="font-semibold text-white group-hover:text-primary transition-colors">
                      {item.label}
                    </span>
                    <span className="text-xs text-gray-500 block font-normal">{item.category}</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-600 opacity-0 group-hover:opacity-100 group-hover:text-primary transition-all" />
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-white/5 bg-surface/50 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <Command className="w-3.5 h-3.5 text-primary" />
            <span>PowerPilot Command Menu</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="bg-white/10 px-1.5 py-0.5 rounded text-[10px] font-mono text-gray-300">ESC</span>
            <span>to close</span>
          </div>
        </div>
      </div>
    </div>
  );
};
