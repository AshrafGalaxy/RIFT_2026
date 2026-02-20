import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, useRef } from 'react';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { Terminal } from 'lucide-react';

const AGENT_COLORS = {
    'Clone Agent': { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', border: 'rgba(59, 130, 246, 0.3)' },
    'Discover Agent': { bg: 'rgba(168, 85, 247, 0.15)', text: '#a855f7', border: 'rgba(168, 85, 247, 0.3)' },
    'Analyze Agent': { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' },
    'Heal Agent': { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', border: 'rgba(16, 185, 129, 0.3)' },
    'Verify Agent': { bg: 'rgba(236, 72, 153, 0.15)', text: '#ec4899', border: 'rgba(236, 72, 153, 0.3)' },
    'System': { bg: 'rgba(100, 116, 139, 0.15)', text: '#64748b', border: 'rgba(100, 116, 139, 0.3)' },
};

const TYPE_CLASSES = {
    info: 'text-text-secondary',
    success: 'text-accent-green',
    error: 'text-accent-red',
    progress: 'text-primary',
};

export default function ActivityLog({ logs = [] }) {
    const [collapsed, setCollapsed] = useState(false);
    const scrollRef = useRef(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        if (scrollRef.current && !collapsed) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, collapsed]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="glass rounded-2xl overflow-hidden"
        >
            {/* Header — matches other card headers */}
            <button
                className="w-full flex items-center justify-between px-6 sm:px-8 py-4 hover:bg-white/5 transition-colors cursor-pointer"
                onClick={() => setCollapsed((c) => !c)}
            >
                <div className="flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-accent-green" />
                    <span className="text-lg font-bold text-text-primary">
                        Live Activity Log
                    </span>
                    <span className="text-xs text-text-muted ml-1">
                        ({logs.length})
                    </span>
                </div>
                {collapsed ? (
                    <FiChevronDown className="text-text-muted w-5 h-5" />
                ) : (
                    <FiChevronUp className="text-text-muted w-5 h-5" />
                )}
            </button>

            <AnimatePresence>
                {!collapsed && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <div
                            ref={scrollRef}
                            className="px-6 sm:px-8 pb-6 max-h-80 overflow-y-auto font-mono text-xs space-y-1.5"
                            style={{ scrollBehavior: 'smooth' }}
                        >
                            {logs.length === 0 ? (
                                <p className="text-text-muted py-4 text-center">
                                    Waiting for pipeline to start...
                                </p>
                            ) : (
                                logs.map((entry, i) => {
                                    const agentStyle = entry.agent
                                        ? AGENT_COLORS[entry.agent] || AGENT_COLORS['System']
                                        : null;
                                    const typeClass = TYPE_CLASSES[entry.type] || TYPE_CLASSES.info;
                                    const ts = entry.timestamp
                                        ? new Date(entry.timestamp).toLocaleTimeString()
                                        : '';

                                    return (
                                        <div
                                            key={i}
                                            className="flex items-start gap-2 py-0.5 leading-snug"
                                        >
                                            {/* Timestamp */}
                                            {ts && (
                                                <span className="text-text-muted shrink-0 w-[4.5rem] text-right tabular-nums">
                                                    {ts}
                                                </span>
                                            )}

                                            {/* Agent badge */}
                                            {entry.agent && agentStyle && (
                                                <span
                                                    className="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold leading-none"
                                                    style={{
                                                        backgroundColor: agentStyle.bg,
                                                        color: agentStyle.text,
                                                        border: `1px solid ${agentStyle.border}`,
                                                    }}
                                                >
                                                    {entry.agent}
                                                </span>
                                            )}

                                            {/* Message */}
                                            <span className={`${typeClass} break-words min-w-0`}>
                                                {entry.message}
                                            </span>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
