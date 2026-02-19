import { motion, AnimatePresence } from 'framer-motion';
import { FiGithub, FiUsers, FiUser, FiLoader } from 'react-icons/fi';
import useAgentStore from '../store/useAgentStore';

const stepIcons = ['📂', '🔍', '🧪', '🤖', '📤', '🔄'];

export default function HeroInput() {
    const {
        repoUrl, teamName, leaderName, isRunning, currentStep, steps,
        setField, startAgent, loadDemo, reset, result,
    } = useAgentStore();

    const canSubmit = repoUrl && teamName && leaderName && !isRunning;

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
                            onChange={(v) => setField('repoUrl', v)}
                            disabled={isRunning}
                        />
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <InputField
                                icon={<FiUsers />}
                                placeholder="Team Name"
                                value={teamName}
                                onChange={(v) => setField('teamName', v)}
                                disabled={isRunning}
                            />
                            <InputField
                                icon={<FiUser />}
                                placeholder="Team Leader Name"
                                value={leaderName}
                                onChange={(v) => setField('leaderName', v)}
                                disabled={isRunning}
                            />
                        </div>
                    </div>

                    {/* Buttons */}
                    <div className="flex flex-col sm:flex-row gap-3 pt-2">
                        <motion.button
                            whileHover={canSubmit ? { scale: 1.02 } : {}}
                            whileTap={canSubmit ? { scale: 0.98 } : {}}
                            onClick={startAgent}
                            disabled={!canSubmit}
                            className={`flex-1 btn-gradient text-white font-semibold py-3.5 px-6 rounded-xl text-base
              transition-all duration-300 flex items-center justify-center gap-2
              ${!canSubmit ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                            {isRunning ? (
                                <>
                                    <FiLoader className="animate-spin" />
                                    Agent Running...
                                </>
                            ) : (
                                <>🚀 Analyze Repository</>
                            )}
                        </motion.button>

                        {!isRunning && !result && (
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={loadDemo}
                                className="px-6 py-3.5 rounded-xl border border-border text-text-secondary
                hover:text-text-primary hover:border-primary transition-all duration-300
                text-sm font-medium cursor-pointer"
                            >
                                ⚡ Load Demo
                            </motion.button>
                        )}

                        {!isRunning && result && (
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={reset}
                                className="px-6 py-3.5 rounded-xl border border-accent-green/30 text-accent-green
                hover:bg-accent-green/10 transition-all duration-300
                text-sm font-medium cursor-pointer flex items-center gap-2"
                            >
                                🔄 New Run
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
                                    {steps.map((step, i) => (
                                        <StepRow key={i} index={i} label={step} currentStep={currentStep} icon={stepIcons[i]} />
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

function StepRow({ index, label, currentStep, icon }) {
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
            <div className="w-7 h-7 flex items-center justify-center text-lg flex-shrink-0">
                {isDone ? '✅' : isActive ? (
                    <FiLoader className="animate-spin text-primary" />
                ) : (
                    <span className="text-text-muted">{icon}</span>
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
