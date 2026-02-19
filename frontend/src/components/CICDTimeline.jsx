import { motion } from 'framer-motion';
import useAgentStore from '../store/useAgentStore';
import { TimelineSkeleton } from './Skeletons';

export default function CICDTimeline() {
    const result = useAgentStore((s) => s.result);
    const isRunning = useAgentStore((s) => s.isRunning);
    if (isRunning && !result) return <TimelineSkeleton />;
    if (!result) return null;

    const cicdRuns = result.cicd_runs || [];
    const totalRuns = cicdRuns.length;
    const maxRuns = 5;
    const overallStatus = result.final_status;
    const isOverallPassed = overallStatus === 'PASSED';
    const isOverallError = overallStatus === 'ERROR';

    // If there are no iterations and the pipeline errored, show a clear message
    if (totalRuns === 0) {
        return (
            <motion.section
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
            >
                <div className="glass rounded-2xl p-6 sm:p-8">
                    <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                        🔄 CI/CD Timeline
                    </h3>
                    <div className="text-center py-8">
                        <p className="text-3xl mb-3">⚠️</p>
                        <p className="text-text-secondary text-sm">
                            {isOverallError
                                ? 'Agent failed before any CI/CD iterations could run.'
                                : 'No CI/CD iterations recorded.'}
                        </p>
                    </div>
                </div>
            </motion.section>
        );
    }

    return (
        <motion.section
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8">
                <h3 className="text-lg font-bold text-text-primary mb-8 flex items-center gap-2">
                    🔄 CI/CD Timeline
                </h3>

                {/* Timeline */}
                <div className="overflow-x-auto pb-4">
                    <div className="flex items-center min-w-max px-4">
                        {cicdRuns.map((run, i) => {
                            const isPassed = run.status === 'PASSED';
                            const time = new Date(run.timestamp * 1000);
                            const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                            return (
                                <div key={i} className="flex items-center">
                                    {/* Node */}
                                    <motion.div
                                        initial={{ scale: 0, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        transition={{ delay: i * 0.15, type: 'spring', stiffness: 200 }}
                                        className={`flex flex-col items-center min-w-[120px] sm:min-w-[140px]`}
                                    >
                                        {/* Card */}
                                        <div
                                            className={`rounded-xl p-4 border text-center w-full transition-all duration-300
                        ${isPassed
                                                    ? 'bg-accent-green/5 border-accent-green/30 glow-green'
                                                    : 'bg-accent-red/5 border-accent-red/30'
                                                }`}
                                        >
                                            <p className="text-text-muted text-xs mb-2">Iteration {run.iteration}/{maxRuns}</p>
                                            <div className="text-3xl mb-2">{isPassed ? '✅' : '❌'}</div>
                                            <p className={`font-bold text-sm ${isPassed ? 'text-accent-green' : 'text-accent-red'}`}>
                                                {run.status}
                                            </p>
                                            {run.failures > 0 && (
                                                <p className="text-text-muted text-xs mt-1">{run.failures} failure{run.failures > 1 ? 's' : ''}</p>
                                            )}
                                            <p className="text-text-muted text-xs mt-1">{timeStr}</p>
                                        </div>
                                    </motion.div>

                                    {/* Connector */}
                                    {i < cicdRuns.length - 1 && (
                                        <motion.div
                                            initial={{ scaleX: 0 }}
                                            animate={{ scaleX: 1 }}
                                            transition={{ delay: i * 0.15 + 0.1, duration: 0.3 }}
                                            className="h-0.5 w-8 sm:w-12 bg-gradient-to-r from-primary/40 to-primary/20 origin-left flex-shrink-0"
                                        />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Summary text — respects overall status, not individual iteration status */}
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="text-center text-text-secondary text-sm mt-4"
                >
                    Completed in <span className="text-text-primary font-semibold">{totalRuns} iteration{totalRuns > 1 ? 's' : ''}</span> out of {maxRuns}
                    {isOverallPassed && (
                        <span className="text-accent-green"> — Pipeline Healed ✅</span>
                    )}
                    {isOverallError && (
                        <span className="text-accent-red"> — Pipeline Failed ❌</span>
                    )}
                </motion.p>
            </div>
        </motion.section>
    );
}
