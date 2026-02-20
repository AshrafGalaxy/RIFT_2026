import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle } from 'lucide-react';
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
  if (!error) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="max-w-5xl mx-auto px-4 sm:px-6 pt-6"
      >
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div>
            <p className="text-accent-red font-semibold text-sm">Pipeline Error</p>
            <p className="text-text-secondary text-xs mt-0.5 break-all">{error}</p>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  const result = useAgentStore((s) => s.result);
  const liveLog = useAgentStore((s) => s.liveLog);
  const isRunning = useAgentStore((s) => s.isRunning);

  useEffect(() => {
    useAgentStore.getState().checkBackend();
  }, []);

  const iterations = result?.iterations || result?.cicd_runs || [];

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <HeroInput />
        <ErrorBanner />
        <RunSummary />
        <ScoreBreakdown />
        <FixesTable />
        <CICDTimeline iterations={iterations} />

        {/* Activity Log — uniform wrapper */}
        {(isRunning || liveLog.length > 0) && (
          <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-8">
            <ActivityLog logs={liveLog} />
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
}
