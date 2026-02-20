import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FiChevronUp, FiChevronDown, FiChevronsUp } from 'react-icons/fi';
import { Wrench, CheckCircle, XCircle, Settings } from 'lucide-react';
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

const COLUMNS = [
    { key: 'file', label: 'File', align: 'text-left' },
    { key: 'bug_type', label: 'Bug Type', align: 'text-left' },
    { key: 'line_number', label: 'Line #', align: 'text-left' },
    { key: 'commit_message', label: 'Commit Message', align: 'text-left' },
    { key: 'status', label: 'Status', align: 'text-center' },
];

function SortArrow({ active, direction }) {
    if (active) {
        return direction === 'asc'
            ? <FiChevronUp className="inline text-primary" size={14} />
            : <FiChevronDown className="inline text-primary" size={14} />;
    }
    return <FiChevronsUp className="inline opacity-0 group-hover:opacity-40 transition-opacity" size={14} />;
}

export default function FixesTable() {
    const result = useAgentStore((s) => s.result);
    const isRunning = useAgentStore((s) => s.isRunning);
    const fixFilterType = useAgentStore((s) => s.fixFilterType);
    const setFixFilter = useAgentStore((s) => s.setFixFilter);

    const [sortKey, setSortKey] = useState(null);
    const [sortDir, setSortDir] = useState('asc');

    const fixes = (result?.fixes || []).map(f => ({
        ...f,
        bug_type: String(f.bug_type || '').toUpperCase().replace('BUGTYPE.', ''),
        status: String(f.status || 'PENDING').toUpperCase().replace('FIXSTATUS.', '')
    }));

    const sorted = useMemo(() => {
        const filtered = fixFilterType === 'ALL'
            ? fixes
            : fixes.filter((f) => f.bug_type === fixFilterType);
        if (!sortKey) return filtered;
        return [...filtered].sort((a, b) => {
            let aVal = a[sortKey];
            let bVal = b[sortKey];
            if (sortKey === 'line_number') {
                return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
            }
            aVal = String(aVal).toLowerCase();
            bVal = String(bVal).toLowerCase();
            if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
            return 0;
        });
    }, [fixes, fixFilterType, sortKey, sortDir]);

    if (isRunning && !fixes.length) return <FixesSkeleton />;
    if (!result) return null;

    // Empty state when result exists but no fixes
    if (!fixes.length) {
        return (
            <motion.section
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
            >
                <div className="glass rounded-2xl p-6 sm:p-8">
                    <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                        <Wrench className="w-5 h-5 text-blue-400" />
                        Fixes Applied
                        <span className="bg-primary/20 text-primary-light text-xs px-2.5 py-0.5 rounded-full font-medium">0</span>
                    </h3>
                    <div className="text-center py-8">
                        <Settings className="w-10 h-10 text-text-muted mx-auto mb-3" />
                        <p className="text-text-secondary text-sm">
                            {result.final_status === 'ERROR'
                                ? 'No fixes were applied — the agent encountered an error during execution.'
                                : 'No fixes were needed — all tests passed.'}
                        </p>
                    </div>
                </div>
            </motion.section>
        );
    }

    const handleSort = (key) => {
        if (sortKey === key) {
            setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

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
                        <Wrench className="w-5 h-5 text-blue-400" />
                        Fixes Applied
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
                <div className="overflow-x-auto rounded-xl border border-border-light -mx-2 sm:mx-0">
                    <table className="w-full text-sm min-w-[640px]">
                        <thead>
                            <tr className="bg-surface-input/60">
                                {COLUMNS.map((col) => (
                                    <th
                                        key={col.key}
                                        onClick={() => handleSort(col.key)}
                                        className={`${col.align} py-3 px-4 text-text-muted font-medium uppercase text-xs tracking-wider
                                            cursor-pointer select-none hover:text-primary transition-colors group`}
                                    >
                                        <span className="inline-flex items-center gap-1">
                                            {col.label}
                                            <SortArrow active={sortKey === col.key} direction={sortKey === col.key ? sortDir : null} />
                                        </span>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sorted.map((fix, i) => (
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
                                    <td className="py-3 px-4 text-xs text-text-secondary max-w-xs truncate">
                                        <CommitMessage message={fix.commit_message} />
                                    </td>
                                    <td className="py-3 px-4 text-center">
                                        {fix.status === 'VERIFIED' ? (
                                            <CheckCircle className="w-4 h-4 text-green-400 inline-block" title="Verified" />
                                        ) : fix.status === 'APPLIED' || fix.status === 'PENDING' ? (
                                            <Wrench className="w-4 h-4 text-blue-400 inline-block" title="Applied" />
                                        ) : (
                                            <XCircle className="w-4 h-4 text-red-400 inline-block" title="Failed" />
                                        )}
                                    </td>
                                </motion.tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {sorted.length === 0 && (
                    <div className="text-center py-8 text-text-muted text-sm">
                        No fixes found for filter "{fixFilterType}"
                    </div>
                )}
            </div>
        </motion.section>
    );
}

function CommitMessage({ message }) {
    if (!message) return <span className="text-text-muted italic">No message</span>;
    const prefix = '[AI-AGENT]';
    if (!message.startsWith(prefix)) return <span>{message}</span>;

    return (
        <span>
            <span className="text-primary font-semibold">{prefix}</span>
            {message.slice(prefix.length)}
        </span>
    );
}
