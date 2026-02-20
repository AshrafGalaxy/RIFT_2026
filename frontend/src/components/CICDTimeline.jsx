import { motion } from 'framer-motion';
import { GitCommit, CheckCircle, XCircle, AlertTriangle, Clock, ArrowRight } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

export default function CICDTimeline({ iterations = [] }) {
    const result = useAgentStore((s) => s.result);
    const isRunning = useAgentStore((s) => s.isRunning);

    // Only healing iterations (number >= 1)
    const healingRuns = iterations.filter((iter) => iter.number >= 1);

    const lastRun = healingRuns.length > 0 ? healingRuns[healingRuns.length - 1] : null;
    const overallPassed = lastRun?.status === 'PASSED' || (lastRun?.failed === 0 && lastRun?.total > 0);

    if (!result && !isRunning) return null;

    return (
        <motion.section
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl overflow-hidden">
                <div className="p-6 sm:p-8">
                    {/* Header */}
                    <h3 className="text-lg font-bold text-text-primary mb-6 flex items-center gap-2">
                        <GitCommit className="w-5 h-5 text-primary" />
                        CI/CD Pipeline Timeline
                        <span className="text-xs text-text-muted font-normal ml-auto">
                            {healingRuns.length} {healingRuns.length === 1 ? 'iteration' : 'iterations'}
                        </span>
                    </h3>

                    {/* Empty state */}
                    {healingRuns.length === 0 ? (
                        <div className="text-center py-8">
                            <Clock className="w-8 h-8 text-text-muted mx-auto mb-2" />
                            <p className="text-text-muted text-sm">
                                {isRunning
                                    ? 'Pipeline is running — iterations will appear here...'
                                    : 'No healing iterations recorded.'}
                            </p>
                        </div>
                    ) : (
                        <>
                            {/* Horizontal scrolling cards */}
                            <div className="flex gap-3 overflow-x-auto pb-3 -mx-1 px-1 scrollbar-thin">
                                {healingRuns.map((iter, idx) => {
                                    const isPassed = iter.status === 'PASSED' || (iter.failed === 0 && iter.total > 0);

                                    return (
                                        <div key={iter.number} className="flex items-center gap-2 shrink-0">
                                            {/* Card */}
                                            <motion.div
                                                initial={{ opacity: 0, scale: 0.9 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: idx * 0.1 }}
                                                className={`
                          relative rounded-xl border px-4 py-3 min-w-[140px]
                          ${isPassed
                                                        ? 'bg-accent-green/10 border-accent-green/30'
                                                        : 'bg-accent-red/10 border-accent-red/30'
                                                    }
                        `}
                                            >
                                                {/* Top row: iteration + icon */}
                                                <div className="flex items-center justify-between gap-2 mb-1.5">
                                                    <span className="text-sm font-bold text-text-primary">
                                                        #{iter.number}
                                                    </span>
                                                    {isPassed ? (
                                                        <CheckCircle className="w-4 h-4 text-accent-green" />
                                                    ) : (
                                                        <XCircle className="w-4 h-4 text-accent-red" />
                                                    )}
                                                </div>

                                                {/* Test counts */}
                                                <div className="text-xs space-y-0.5">
                                                    <div className="flex justify-between">
                                                        <span className="text-text-muted">Passed</span>
                                                        <span className="text-accent-green font-semibold">{iter.passed}</span>
                                                    </div>
                                                    <div className="flex justify-between">
                                                        <span className="text-text-muted">Failed</span>
                                                        <span className="text-accent-red font-semibold">{iter.failed}</span>
                                                    </div>
                                                    <div className="flex justify-between">
                                                        <span className="text-text-muted">Total</span>
                                                        <span className="text-text-primary font-semibold">{iter.total}</span>
                                                    </div>
                                                </div>

                                                {/* Fixes info */}
                                                {iter.fixes_applied > 0 && (
                                                    <div className="mt-1.5 pt-1.5 border-t border-border text-[10px] text-text-muted">
                                                        {iter.fixes_applied} fix(es) applied
                                                    </div>
                                                )}

                                                {/* Timestamp */}
                                                {iter.timestamp && (
                                                    <div className="mt-1 text-[10px] text-text-muted tabular-nums">
                                                        {new Date(iter.timestamp).toLocaleTimeString()}
                                                    </div>
                                                )}
                                            </motion.div>

                                            {/* Arrow between cards */}
                                            {idx < healingRuns.length - 1 && (
                                                <ArrowRight className="w-4 h-4 text-text-muted shrink-0" />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Summary footer */}
                            <div
                                className={`mt-4 flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium ${overallPassed
                                    ? 'bg-accent-green/10 border border-accent-green/20 text-accent-green'
                                    : 'bg-accent-red/10 border border-accent-red/20 text-accent-red'
                                    }`}
                            >
                                {overallPassed ? (
                                    <CheckCircle className="w-4 h-4 shrink-0" />
                                ) : (
                                    <AlertTriangle className="w-4 h-4 shrink-0" />
                                )}
                                {overallPassed
                                    ? `All tests passed on iteration ${lastRun.number}`
                                    : `${lastRun.failed} test(s) still failing after ${healingRuns.length} iteration(s)`}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </motion.section>
    );
}
