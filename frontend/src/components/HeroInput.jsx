import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FiGithub, FiUsers, FiUser } from 'react-icons/fi';
import { Rocket, Zap, RefreshCw, FolderOpen, Search, FlaskConical, Bot, Upload, RotateCw, CheckCircle, Loader2 } from 'lucide-react';
import useAgentStore from '../store/useAgentStore';

const STEPS = [
    { label: 'Cloning repository', Icon: FolderOpen },
    { label: 'Discovering tests', Icon: Search },
    { label: 'Running tests', Icon: FlaskConical },
    { label: 'Generating fixes', Icon: Bot },
    { label: 'Pushing to branch', Icon: Upload },
    { label: 'Monitoring CI/CD', Icon: RotateCw },
];

export default function HeroInput() {
    const repoUrl = useAgentStore((s) => s.repoUrl);
    const teamName = useAgentStore((s) => s.teamName);
    const leaderName = useAgentStore((s) => s.leaderName);
    const isRunning = useAgentStore((s) => s.isRunning);
    const currentStep = useAgentStore((s) => s.currentStep);
    const result = useAgentStore((s) => s.result);
    const error = useAgentStore((s) => s.error);

    const setRepoUrl = useAgentStore((s) => s.setRepoUrl);
    const setTeamName = useAgentStore((s) => s.setTeamName);
    const setLeaderName = useAgentStore((s) => s.setLeaderName);
    const maxIterations = useAgentStore((s) => s.maxIterations);
    const setMaxIterations = useAgentStore((s) => s.setMaxIterations);
    const startRun = useAgentStore((s) => s.startRun);
    const loadDemo = useAgentStore((s) => s.loadDemo);
    const reset = useAgentStore((s) => s.reset);

    const canSubmit = repoUrl && teamName && leaderName && !isRunning;

    // Local state for retry input so user can freely type
    const [retryInput, setRetryInput] = useState(String(maxIterations));

    const handleRetryChange = (e) => {
        setRetryInput(e.target.value);
    };

    const handleRetryBlur = () => {
        let val = parseInt(retryInput, 10);
        if (isNaN(val) || val < 1) val = 1;
        if (val > 20) val = 20;
        setRetryInput(String(val));
        setMaxIterations(val);
    };

    return (
        <section className="hero-gradient-bg hero-grid-overlay rounded-b-3xl">
            <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="text-center mb-10"
                >
                    <h2 className="text-3xl sm:text-5xl font-extrabold gradient-text mb-3 leading-tight">
                        Heal Your CI/CD Pipeline
                    </h2>
                    <p className="text-text-secondary text-sm sm:text-base max-w-xl mx-auto">
                        Enter your repository details and let our AI agent autonomously detect failures,
                        generate fixes, and heal your pipeline.
                    </p>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                    className="glass rounded-2xl p-6 sm:p-8 space-y-4"
                >
                    {/* Inputs */}
                    <div className="space-y-3">
                        <InputField
                            icon={<FiGithub />}
                            placeholder="GitHub Repository URL"
                            value={repoUrl}
                            onChange={setRepoUrl}
                            disabled={isRunning}
                        />
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <InputField
                                icon={<FiUsers />}
                                placeholder="Team Name"
                                value={teamName}
                                onChange={setTeamName}
                                disabled={isRunning}
                            />
                            <InputField
                                icon={<FiUser />}
                                placeholder="Team Leader Name"
                                value={leaderName}
                                onChange={setLeaderName}
                                disabled={isRunning}
                            />
                        </div>
                        {/* Retry limit */}
                        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-card/60 border border-border">
                            <RefreshCw className="w-4 h-4 text-text-secondary shrink-0" />
                            <span className="text-text-secondary text-sm whitespace-nowrap">Retry Limit</span>
                            <input
                                type="number"
                                min={1}
                                max={20}
                                value={retryInput}
                                onChange={handleRetryChange}
                                onBlur={handleRetryBlur}
                                onKeyDown={(e) => { if (e.key === 'Enter') e.target.blur(); }}
                                disabled={isRunning}
                                className="w-14 bg-transparent border-none outline-none text-text-primary text-sm font-semibold text-center
                                           [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                            />
                        </div>
                    </div>

                    {/* Buttons */}
                    <div className="flex flex-col sm:flex-row gap-3 pt-2">
                        <motion.button
                            whileHover={canSubmit ? { scale: 1.02 } : {}}
                            whileTap={canSubmit ? { scale: 0.98 } : {}}
                            onClick={startRun}
                            disabled={!canSubmit}
                            className={`flex-1 btn-gradient text-white font-semibold py-3.5 px-6 rounded-xl text-base
              transition-all duration-300 flex items-center justify-center gap-2
              ${!canSubmit ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                            {isRunning ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Agent Running...
                                </>
                            ) : (
                                <>
                                    <Rocket className="w-5 h-5" />
                                    Analyze Repository
                                </>
                            )}
                        </motion.button>

                        {!isRunning && !result && !error && (
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={loadDemo}
                                className="px-6 py-3.5 rounded-xl border border-border text-text-secondary
                hover:text-text-primary hover:border-primary transition-all duration-300
                text-sm font-medium cursor-pointer flex items-center gap-2"
                            >
                                <Zap className="w-4 h-4" />
                                Load Demo
                            </motion.button>
                        )}

                        {!isRunning && (result || error) && (
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={reset}
                                className="px-6 py-3.5 rounded-xl border border-accent-green/30 text-accent-green
                hover:bg-accent-green/10 transition-all duration-300
                text-sm font-medium cursor-pointer flex items-center gap-2"
                            >
                                <RefreshCw className="w-4 h-4" />
                                New Run
                            </motion.button>
                        )}
                    </div>
                </motion.div>

                {/* Progress Steps */}
                <AnimatePresence>
                    {isRunning && (
                        <motion.div
                            initial={{ opacity: 0, y: 20, height: 0 }}
                            animate={{ opacity: 1, y: 0, height: 'auto' }}
                            exit={{ opacity: 0, y: -10, height: 0 }}
                            className="mt-6"
                        >
                            <div className="glass rounded-2xl p-6 sm:p-8">
                                <div className="space-y-3">
                                    {STEPS.map((step, i) => (
                                        <StepRow key={i} index={i} label={step.label} currentStep={currentStep} Icon={step.Icon} />
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </section>
    );
}

function InputField({ icon, placeholder, value, onChange, disabled }) {
    return (
        <div className="relative group">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-primary transition-colors">
                {icon}
            </span>
            <input
                type="text"
                placeholder={placeholder}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                className="w-full bg-surface-input border border-border rounded-xl py-3 pl-11 pr-4
          text-text-primary placeholder-text-muted text-sm
          focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30
          disabled:opacity-50 transition-all duration-300"
            />
        </div>
    );
}

function StepRow({ index, label, currentStep, Icon }) {
    const isDone = currentStep > index;
    const isActive = currentStep === index;
    const isPending = currentStep < index;

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08 }}
            className={`flex items-center gap-3 py-2 px-3 rounded-lg transition-all duration-300
        ${isActive ? 'bg-primary/10 border border-primary/20' : ''}
        ${isDone ? 'opacity-80' : ''}
        ${isPending ? 'opacity-40' : ''}`}
        >
            <div className="w-7 h-7 flex items-center justify-center flex-shrink-0">
                {isDone ? (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                ) : isActive ? (
                    <Loader2 className="w-5 h-5 text-primary animate-spin" />
                ) : (
                    <Icon className="w-5 h-5 text-text-muted" />
                )}
            </div>
            <span className={`text-sm font-medium ${isActive ? 'text-text-primary' : isDone ? 'text-accent-green' : 'text-text-muted'}`}>
                Step {index + 1}: {label}
            </span>
            {isDone && <span className="ml-auto text-xs text-accent-green">Complete</span>}
            {isActive && <span className="ml-auto text-xs text-primary animate-pulse">Running...</span>}
        </motion.div>
    );
}
