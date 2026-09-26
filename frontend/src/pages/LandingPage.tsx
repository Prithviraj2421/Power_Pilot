import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Upload,
  Zap,
  ShieldCheck,
  Code,
  LayoutDashboard,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  FileSpreadsheet,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useUploadStore } from '../store/useUploadStore';
import { useAnalysisStore } from '../store/useAnalysisStore';
import { PipelineUploadExperience } from '../features/upload/components/PipelineUploadExperience';
import { apiClient } from '../api/apiClient';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { file, setFile } = useUploadStore();
  const { setAnalysisResult, setStatus } = useAnalysisStore();

  const [isProcessing, setIsProcessing] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setIsProcessing(true);
    setStageIndex(0);
    setStatus('analyzing');

    // Simulate 12-stage animated pipeline step transitions
    const stageTimer = setInterval(() => {
      setStageIndex((prev) => {
        if (prev >= 11) {
          clearInterval(stageTimer);
          return 11;
        }
        return prev + 1;
      });
    }, 450);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await apiClient.post('/api/v1/intelligence/analyze-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // The API returns { status, result, dataset_name, ... }
      // The actual MasterIntelligenceResult is inside response.data.result
      const intelligenceResult = response.data.result;
      setAnalysisResult(selectedFile.name, intelligenceResult);

      clearInterval(stageTimer);
      setStageIndex(11);
      setTimeout(() => {
        setIsProcessing(false);
        navigate('/workspace');
      }, 1200);
    } catch (err) {
      setStatus('error');
      setIsProcessing(false);
      clearInterval(stageTimer);
    }
  };

  return (
    <div className="min-h-screen bg-[#080B11] text-white overflow-hidden relative selection:bg-primary selection:text-white">
      {/* Background Ambient Radial Lights (Apple/Awwwards style) */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-primary/20 via-purple-500/10 to-transparent blur-3xl pointer-events-none" />
      <div className="absolute top-1/3 -right-48 w-[500px] h-[500px] bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />

      {/* Header Bar */}
      <header className="h-20 border-b border-white/10 px-8 flex items-center justify-between sticky top-0 z-30 bg-[#080B11]/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/20 text-primary rounded-2xl border border-primary/30 shadow-glow-blue">
            <Zap className="w-5 h-5" />
          </div>
          <span className="font-extrabold text-xl text-white tracking-tight">
            Power<span className="text-primary">Pilot</span>
          </span>
          <Badge variant="primary" size="sm">ENTERPRISE BI</Badge>
        </div>

        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/workspace')}>
            View Demo Workspace
          </Button>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 pt-16 pb-24 relative z-10 space-y-24">
        {/* Processing State: Iron Man Animated Pipeline */}
        {isProcessing ? (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
            <PipelineUploadExperience currentStageIndex={stageIndex} datasetName={file?.name || 'Dataset'} />
          </motion.div>
        ) : (
          <>
            {/* Personality 1: Awwwards 3D/Motion Hero Section */}
            <div className="text-center space-y-8 max-w-4xl mx-auto">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
                <span className="px-4 py-1.5 bg-white/5 border border-white/10 rounded-full text-xs font-bold text-primary tracking-widest uppercase inline-flex items-center gap-2 mb-4">
                  <Sparkles className="w-3.5 h-3.5" />
                  Autonomous Enterprise BI Engine
                </span>
                <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-white leading-tight">
                  Turn Raw Data into <br />
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary via-purple-400 to-emerald-400">
                    Executive Intelligence.
                  </span>
                </h1>
              </motion.div>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed"
              >
                Upload any CSV or Excel file. PowerPilot validates data quality, infers domain semantics, builds executable DAX measures, and synthesizes strategic decision matrices automatically.
              </motion.p>

              {/* Upload Dropzone Component */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="max-w-xl mx-auto"
              >
                <label className="block p-10 bg-card/60 backdrop-blur-2xl border-2 border-dashed border-white/15 hover:border-primary/60 rounded-3xl cursor-pointer transition-all duration-300 shadow-glass group relative overflow-hidden">
                  <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />

                  <div className="flex flex-col items-center gap-4 text-center">
                    <div className="p-4 bg-primary/20 text-primary rounded-2xl border border-primary/30 group-hover:scale-110 group-hover:shadow-glow-blue transition-all">
                      <Upload className="w-8 h-8" />
                    </div>
                    <div>
                      <span className="text-base font-bold text-white block mb-1">
                        Drop your CSV dataset here
                      </span>
                      <span className="text-xs text-gray-400 block">
                        Supports enterprise datasets up to 100,000+ rows
                      </span>
                    </div>
                    <Button variant="primary" leftIcon={<FileSpreadsheet className="w-4 h-4" />}>
                      Browse Files
                    </Button>
                  </div>
                </label>
              </motion.div>
            </div>

            {/* Floating Morphing Hero KPI Panel (Apple/Framer style) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card glass className="p-6 border-emerald-500/30">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Stage 1 DQPE</span>
                  <Badge variant="success">GRADE A+</Badge>
                </div>
                <div className="text-3xl font-extrabold text-white mb-2">98.5% Quality</div>
                <p className="text-xs text-gray-400">Zero missing cell errors; automated category & datetime normalization.</p>
              </Card>

              <Card glass className="p-6 border-primary/30">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">DAX KPI Studio</span>
                  <Badge variant="primary">POWER BI</Badge>
                </div>
                <div className="text-3xl font-extrabold text-white mb-2">12 DAX Measures</div>
                <p className="text-xs text-gray-400">Executable Tabular Model formulas with 1-click clipboard copying.</p>
              </Card>

              <Card glass className="p-6 border-purple-500/30">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Decision Engine</span>
                  <Badge variant="purple">98% CONFIDENCE</Badge>
                </div>
                <div className="text-3xl font-extrabold text-white mb-2">Strategic Matrix</div>
                <p className="text-xs text-gray-400">Synthesizes ROI, risk levels, and management mitigation plans.</p>
              </Card>
            </div>
          </>
        )}
      </main>
    </div>
  );
};
