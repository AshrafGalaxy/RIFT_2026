import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { FiChevronDown, FiChevronUp, FiTerminal } from 'react-icons/fi';
import useAgentStore from '../store/useAgentStore';

const TYPE_COLORS = {
    success: 'text-accent-green',
    error: 'text-accent-red',
    progress: 'text-accent-yellow',
    info: 'text-text-secondary',
};

export default function ActivityLog() {
    const liveLog = useAgentStore((s) => s.liveLog);
    const isLogExpanded = useAgentStore((s) => s.isLogExpanded);
    const toggleLog = useAgentStore((s) => s.toggleLog);
    const bottomRef = useRef(null);

    useEffect(() => {
        if (isLogExpanded && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [liveLog, isLogExpanded]);

    if (!liveLog.length) return null;

    return (
        <motion.section
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="rounded-2xl overflow-hidden border border-border-light" style={{ backgroundColor: 'rgba(8, 6, 14, 0.85)' }}>
                {/* Header */}
                <button
                    onClick={toggleLog}
                    className="w-full flex items-center justify-between px-6 py-4 cursor-pointer
            hover:bg-white/[0.02] transition-colors"
                >
                    <div className="flex items-center gap-2">
                        <FiTerminal className="text-primary" />
                        <h3 className="text-sm font-bold text-text-primary">Live Activity Log</h3>
                        <span className="bg-primary/20 text-primary-light text-xs px-2 py-0.5 rounded-full">
                            {liveLog.length}
                        </span>
                    </div>
                    {isLogExpanded ? (
                        <FiChevronUp className="text-text-muted" />
                    ) : (
                        <FiChevronDown className="text-text-muted" />
                    )}
                </button>

                {/* Log Content */}
                <AnimatePresence>
                    {isLogExpanded && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3 }}
                            className="overflow-hidden"
                        >
                            <div className="max-h-72 overflow-y-auto px-6 pb-4 font-mono text-xs leading-relaxed space-y-0.5">
                                {liveLog.map((log, i) => {
                                    const time = new Date(log.timestamp).toLocaleTimeString([], {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        second: '2-digit',
                                    });
                                    return (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: 0.02 * Math.min(i, 20) }}
                                            className={`${TYPE_COLORS[log.type] || 'text-text-secondary'} py-0.5`}
                                        >
                                            <span className="text-text-muted mr-2">[{time}]</span>
                                            {log.message}
                                        </motion.div>
                                    );
                                })}
                                <div ref={bottomRef} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.section>
    );
}
