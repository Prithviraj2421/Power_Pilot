import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileCheck,
  ShieldCheck,
  Lock,
  Search,
  Tag,
  Globe,
  Briefcase,
  Lightbulb,
  Network,
  Code,
  Target,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

export interface PipelineStage {
  id: number;
  label: string;
  subtext: string;
  icon: React.ReactNode;
  status: 'pending' | 'active' | 'completed';
}

export interface PipelineUploadExperienceProps {
  currentStageIndex: number;
  datasetName: string;
}

export const PipelineUploadExperience: React.FC<PipelineUploadExperienceProps> = ({
  currentStageIndex,
  datasetName,
}) => {
  const stages: Omit<PipelineStage, 'status'>[] = [
    { id: 1, label: 'File Stream Ingestion', subtext: 'Parsing CSV/XLSX bytes', icon: <FileCheck className="w-4 h-4" /> },
    { id: 2, label: 'Stage 1 DQPE Cleaner', subtext: 'Imputing missing & deduplicating', icon: <ShieldCheck className="w-4 h-4" /> },
    { id: 3, label: 'Governance Validation', subtext: 'Applying compliance rules', icon: <Lock className="w-4 h-4" /> },
    { id: 4, label: 'Schema Analyzer', subtext: 'Inferring physical data types', icon: <Search className="w-4 h-4" /> },
    { id: 5, label: 'Entity Detection', subtext: 'Mapping semantic entities', icon: <Tag className="w-4 h-4" /> },
    { id: 6, label: 'Domain Classifier', subtext: 'Classifying Retail/Finance/HR', icon: <Globe className="w-4 h-4" /> },
    { id: 7, label: 'Business Profiler', subtext: 'Building domain metadata', icon: <Briefcase className="w-4 h-4" /> },
    { id: 8, label: 'Data Intelligence Engine', subtext: 'Synthesizing statistical trends', icon: <Lightbulb className="w-4 h-4" /> },
    { id: 9, label: 'Relationship Profiler', subtext: 'Detecting entity keys & card', icon: <Network className="w-4 h-4" /> },
    { id: 10, label: 'KPI & DAX Studio', subtext: 'Generating executable formulas', icon: <Code className="w-4 h-4" /> },
    { id: 11, label: 'Strategic Decision Engine', subtext: 'Synthesizing ROI & actions', icon: <Target className="w-4 h-4" /> },
    { id: 12, label: 'Executive Output', subtext: 'Building dashboard & report assets', icon: <CheckCircle2 className="w-4 h-4" /> },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto p-8 bg-card/80 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-glass relative overflow-hidden">
      {/* Background Radial Glow */}
      <div className="absolute -top-32 -left-32 w-64 h-64 bg-primary/20 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl animate-pulse pointer-events-none" />

      {/* Header Telemetry */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary/20 text-primary rounded-2xl border border-primary/40 shadow-glow-blue">
            <Sparkles className="w-6 h-6 animate-spin" />
          </div>
          <div>
            <h3 className="text-lg font-extrabold text-white tracking-tight">
              Executing PowerPilot Intelligence Pipeline
            </h3>
            <p className="text-xs text-gray-400">
              Dataset: <span className="text-primary font-semibold">{datasetName}</span> | 12 Pipeline Stages
            </p>
          </div>
        </div>

        <div className="px-4 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-emerald-400 font-mono text-xs font-bold animate-pulse">
          STAGE {Math.min(currentStageIndex + 1, 12)} / 12
        </div>
      </div>

      {/* Grid of 12 Animated Nodes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stages.map((stage, idx) => {
          const isDone = idx < currentStageIndex;
          const isActive = idx === currentStageIndex;

          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.05 }}
              className={`p-4 rounded-2xl border transition-all duration-300 relative ${
                isActive
                  ? 'bg-primary/15 border-primary/60 shadow-glow-blue scale-[1.02]'
                  : isDone
                  ? 'bg-emerald-500/5 border-emerald-500/30'
                  : 'bg-surface/50 border-white/5 opacity-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`p-2 rounded-xl border transition-colors ${
                    isActive
                      ? 'bg-primary text-white border-primary/80 animate-pulse'
                      : isDone
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      : 'bg-white/5 text-gray-400 border-white/5'
                  }`}
                >
                  {stage.icon}
                </div>

                <div className="flex-1 min-w-0">
                  <span className="text-xs font-bold text-white block truncate">{stage.label}</span>
                  <span className="text-[11px] text-gray-400 block truncate">{stage.subtext}</span>
                </div>

                {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
