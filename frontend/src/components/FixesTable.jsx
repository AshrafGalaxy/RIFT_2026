import { motion } from 'framer-motion';
import useAgentStore from '../store/useAgentStore';
import { FixesSkeleton } from './Skeletons';

const BUG_TYPES = ['ALL', 'LINTING', 'SYNTAX', 'LOGIC', 'TYPE_ERROR', 'IMPORT', 'INDENTATION'];

const BADGE_COLORS = {
    LINTING: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    SYNTAX: 'bg-red-500/15 text-red-400 border-red-500/30',
    LOGIC: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    TYPE_ERROR: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    IMPORT: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    INDENTATION: 'bg-pink-500/15 text-pink-400 border-pink-500/30',
};

export default function FixesTable() {
    const result = useAgentStore((s) => s.result);
    const isRunning = useAgentStore((s) => s.isRunning);
    const fixFilterType = useAgentStore((s) => s.fixFilterType);
    const setFixFilter = useAgentStore((s) => s.setFixFilter);

    if (isRunning && !result?.fixes?.length) return <FixesSkeleton />;
    if (!result?.fixes?.length) return null;

    const filtered = fixFilterType === 'ALL'
        ? result.fixes
        : result.fixes.filter((f) => f.bug_type === fixFilterType);

    return (
        <motion.section
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                    <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
                        🔧 Fixes Applied
                        <span className="bg-primary/20 text-primary-light text-xs px-2.5 py-0.5 rounded-full font-medium">
                            {result.fixes.length}
                        </span>
                    </h3>
                </div>

                {/* Filter Pills */}
                <div className="flex flex-wrap gap-2 mb-6">
                    {BUG_TYPES.map((type) => (
                        <button
                            key={type}
                            onClick={() => setFixFilter(type)}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer
                ${fixFilterType === type
                                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                                    : 'border border-border text-text-secondary hover:border-primary hover:text-primary'
                                }`}
                        >
                            {type.replace('_', ' ')}
                        </button>
                    ))}
                </div>

                {/* Table */}
                <div className="overflow-x-auto rounded-xl border border-border-light">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-surface-input/60">
                                <th className="text-left py-3 px-4 text-text-muted font-medium uppercase text-xs tracking-wider">File</th>
                                <th className="text-left py-3 px-4 text-text-muted font-medium uppercase text-xs tracking-wider">Bug Type</th>
                                <th className="text-left py-3 px-4 text-text-muted font-medium uppercase text-xs tracking-wider">Line #</th>
                                <th className="text-left py-3 px-4 text-text-muted font-medium uppercase text-xs tracking-wider hidden md:table-cell">Commit Message</th>
                                <th className="text-center py-3 px-4 text-text-muted font-medium uppercase text-xs tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((fix, i) => (
                                <motion.tr
                                    key={i}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: i * 0.05 }}
                                    className={`border-t border-border-light transition-colors duration-200 hover:bg-primary/5
                    ${i % 2 === 0 ? 'bg-transparent' : 'bg-surface-input/20'}`}
                                >
                                    <td className="py-3 px-4 font-mono text-xs text-primary-light">{fix.file}</td>
                                    <td className="py-3 px-4">
                                        <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-medium border ${BADGE_COLORS[fix.bug_type] || 'bg-gray-500/15 text-gray-400 border-gray-500/30'}`}>
                                            {fix.bug_type}
                                        </span>
                                    </td>
                                    <td className="py-3 px-4 font-mono text-xs text-text-secondary">{fix.line_number}</td>
                                    <td className="py-3 px-4 text-xs text-text-secondary hidden md:table-cell max-w-xs truncate">
                                        <CommitMessage message={fix.commit_message} />
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        {fix.status === 'Fixed' ? (
                                            <span className="text-accent-green text-sm" title="Fixed">✅</span>
                                        ) : (
                                            <span className="text-accent-red text-sm" title="Failed">❌</span>
                                        )}
                                    </td>
                                </motion.tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {filtered.length === 0 && (
                    <div className="text-center py-8 text-text-muted text-sm">
                        No fixes found for filter "{fixFilterType}"
                    </div>
                )}
            </div>
        </motion.section>
    );
}

function CommitMessage({ message }) {
    const prefix = '[AI-AGENT]';
    if (!message.startsWith(prefix)) return <span>{message}</span>;

    return (
        <span>
            <span className="text-primary font-semibold">{prefix}</span>
            {message.slice(prefix.length)}
        </span>
    );
}
