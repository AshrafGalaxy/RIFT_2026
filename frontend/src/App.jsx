import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import useAgentStore from './store/useAgentStore';
import Navbar from './components/Navbar';
import HeroInput from './components/HeroInput';
import RunSummary from './components/RunSummary';
import ScoreBreakdown from './components/ScoreBreakdown';
import FixesTable from './components/FixesTable';
import CICDTimeline from './components/CICDTimeline';
import ActivityLog from './components/ActivityLog';
import Footer from './components/Footer';

function ErrorBanner() {
  const error = useAgentStore((s) => s.error);
  const dismissError = useAgentStore((s) => s.dismissError);

  if (!error) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="max-w-5xl mx-auto px-4 sm:px-6 pt-6"
      >
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">❌</span>
            <div>
              <p className="text-accent-red font-semibold text-sm">Pipeline Error</p>
              <p className="text-text-secondary text-xs mt-0.5 break-all">{error}</p>
            </div>
          </div>
          <button
            onClick={dismissError}
            className="text-text-muted hover:text-text-primary text-xs px-3 py-1.5 rounded-lg
                          border border-border hover:border-primary transition-all cursor-pointer flex-shrink-0 ml-4"
          >
            Dismiss
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  useEffect(() => {
    useAgentStore.getState().fetchLatestResult();
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <HeroInput />
        <ErrorBanner />
        <RunSummary />
        <ScoreBreakdown />
        <FixesTable />
        <CICDTimeline />
        <ActivityLog />
      </main>
      <Footer />
    </div>
  );
}

