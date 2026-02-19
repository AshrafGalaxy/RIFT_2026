import { motion } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import useAgentStore from '../store/useAgentStore';
import { ScoreSkeleton } from './Skeletons';

export default function ScoreBreakdown() {
    const result = useAgentStore((s) => s.result);
    const isRunning = useAgentStore((s) => s.isRunning);
    if (isRunning && !result?.score) return <ScoreSkeleton />;
    if (!result?.score) return null;

    const { base, speed_bonus, efficiency_penalty, total } = result.score;
    const isError = result.final_status === 'ERROR';
    const isFailed = result.final_status === 'FAILED';

    // If ERROR/FAILED with 0 scores, show a descriptive empty state instead of confusing zero-ring
    if ((isError || isFailed) && total === 0) {
        return (
            <motion.section
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
            >
                <div className="glass rounded-2xl p-6 sm:p-8">
                    <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                        🏆 Score Breakdown
                    </h3>
                    <div className="text-center py-8">
                        <p className="text-3xl mb-3">📊</p>
                        <p className="text-text-secondary text-sm">
                            {isError
                                ? 'No score available — the agent encountered an error before completing the pipeline.'
                                : 'No score available — the pipeline completed but could not fix the failures.'}
                        </p>
                        <p className="text-text-muted text-xs mt-2">Score: 0 / 120</p>
                    </div>
                </div>
            </motion.section>
        );
    }

    const chartData = [
        { name: 'Base Score', value: base, color: '#7C3AED' },
        { name: 'Speed Bonus', value: speed_bonus, color: '#10B981' },
        { name: 'Penalty', value: efficiency_penalty, color: '#EF4444' },
        { name: 'Total', value: total, color: total >= 80 ? '#10B981' : total >= 50 ? '#F59E0B' : '#EF4444' },
    ];

    return (
        <motion.section
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-5xl mx-auto px-4 sm:px-6 pb-8"
        >
            <div className="glass rounded-2xl p-6 sm:p-8">
                <h3 className="text-lg font-bold text-text-primary mb-8 flex items-center gap-2">
                    🏆 Score Breakdown
                </h3>

                {/* Ring + Cards */}
                <div className="flex flex-col items-center gap-8">
                    {/* Animated Ring */}
                    <AnimatedScoreRing score={total} />

                    {/* Score Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
                        <ScoreCard
                            icon="🎯"
                            label="Base Score"
                            value={`${base} pts`}
                            desc="Full test resolution"
                            colorClass="from-primary/20 to-primary-dark/20 border-primary/30"
                        />
                        <ScoreCard
                            icon="⚡"
                            label="Speed Bonus"
                            value={speed_bonus > 0 ? `+${speed_bonus}` : '0'}
                            desc="Completed in < 5 min"
                            colorClass="from-accent-green/20 to-accent-green/5 border-accent-green/30"
                        />
                        <ScoreCard
                            icon="📊"
                            label="Efficiency Penalty"
                            value={efficiency_penalty > 0 ? `-${efficiency_penalty}` : '0'}
                            desc="-2 per commit > 20"
                            colorClass="from-accent-red/20 to-accent-red/5 border-accent-red/30"
                        />
                    </div>
                </div>

                {/* Bar Chart */}
                <ChartSection chartData={chartData} />
            </div>
        </motion.section>
    );
}

function ChartSection({ chartData }) {
    const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'));

    useEffect(() => {
        const observer = new MutationObserver(() => {
            setIsDark(document.documentElement.classList.contains('dark'));
        });
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => observer.disconnect();
    }, []);

    const tickFill = isDark ? '#A0A0B8' : '#4A4560';
    const axisStroke = isDark ? 'rgba(124,58,237,0.2)' : 'rgba(124,58,237,0.25)';
    const gridStroke = isDark ? 'rgba(124,58,237,0.1)' : 'rgba(124,58,237,0.12)';
    const tooltipBg = isDark ? 'rgba(15,11,26,0.95)' : 'rgba(255,255,255,0.95)';
    const tooltipBorder = isDark ? 'rgba(124,58,237,0.3)' : 'rgba(124,58,237,0.2)';
    const tooltipColor = isDark ? '#F3F0FF' : '#1E1033';

    return (
        <div className="mt-8 h-56 sm:h-64 min-h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} barSize={40} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                    <XAxis dataKey="name" tick={{ fill: tickFill, fontSize: 12 }} axisLine={{ stroke: axisStroke }} />
                    <YAxis tick={{ fill: tickFill, fontSize: 12 }} axisLine={{ stroke: axisStroke }} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: tooltipBg,
                            border: `1px solid ${tooltipBorder}`,
                            borderRadius: '12px',
                            color: tooltipColor,
                            fontSize: '13px',
                            boxShadow: isDark ? '0 4px 20px rgba(0,0,0,0.3)' : '0 4px 20px rgba(0,0,0,0.1)',
                        }}
                        labelStyle={{ color: tooltipColor, fontWeight: 600 }}
                        itemStyle={{ color: tooltipColor }}
                    />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                        {chartData.map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

function AnimatedScoreRing({ score }) {
    const [displayScore, setDisplayScore] = useState(0);
    const animFrameRef = useRef(null);

    const color = score >= 80 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444';
    const maxScore = 120;
    const pct = Math.min(score / maxScore, 1);
    const r = 80;
    const circ = 2 * Math.PI * r;
    const offset = circ * (1 - pct);

    useEffect(() => {
        let start = null;
        const duration = 2000;
        const animate = (ts) => {
            if (!start) start = ts;
            const progress = Math.min((ts - start) / duration, 1);
            // Cubic ease-out: decelerates smoothly to rest
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplayScore(Math.round(eased * score));
            if (progress < 1) {
                animFrameRef.current = requestAnimationFrame(animate);
            }
        };
        animFrameRef.current = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(animFrameRef.current);
    }, [score]);

    return (
        <div className="relative w-48 h-48 sm:w-56 sm:h-56">
            <svg viewBox="0 0 200 200" className="w-full h-full -rotate-90">
                {/* Background ring */}
                <circle cx="100" cy="100" r={r} fill="none" stroke="rgba(124,58,237,0.1)" strokeWidth="12" />
                {/* Progress ring */}
                <motion.circle
                    cx="100" cy="100" r={r}
                    fill="none"
                    stroke={color}
                    strokeWidth="12"
                    strokeLinecap="round"
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: circ }}
                    animate={{ strokeDashoffset: offset }}
                    transition={{ duration: 2, ease: [0.33, 1, 0.68, 1] }}
                    style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl sm:text-5xl font-bold" style={{ color }}>{displayScore}</span>
                <span className="text-text-muted text-xs uppercase tracking-wider mt-1">points</span>
            </div>
        </div>
    );
}

function ScoreCard({ icon, label, value, desc, colorClass }) {
    return (
        <motion.div
            whileHover={{ y: -2, scale: 1.01 }}
            className={`bg-gradient-to-br ${colorClass} border rounded-xl p-4 text-center transition-all duration-300`}
        >
            <span className="text-2xl">{icon}</span>
            <p className="text-text-secondary text-xs mt-2 uppercase tracking-wider">{label}</p>
            <p className="text-text-primary text-2xl font-bold mt-1">{value}</p>
            <p className="text-text-muted text-xs mt-1">{desc}</p>
        </motion.div>
    );
}
