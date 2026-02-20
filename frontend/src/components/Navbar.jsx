import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { FiSun, FiMoon } from 'react-icons/fi';
import { Bot } from 'lucide-react';

function getInitialTheme() {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('rift-theme') || 'dark';
    }
    return 'dark';
}

export default function Navbar() {
    const [theme, setTheme] = useState(getInitialTheme);
    const [backendStatus, setBackendStatus] = useState('checking'); // 'online' | 'offline' | 'checking'

    // Theme toggle
    useEffect(() => {
        const root = document.documentElement;
        root.classList.remove('dark', 'light');
        root.classList.add(theme);
        localStorage.setItem('rift-theme', theme);
    }, [theme]);

    // Live health check
    useEffect(() => {
        const checkHealth = async () => {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            try {
                const res = await fetch(`${apiUrl}/api/health`);
                setBackendStatus(res.ok ? 'online' : 'offline');
            } catch {
                setBackendStatus('offline');
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 30000); // Re-check every 30s
        return () => clearInterval(interval);
    }, []);

    const toggleTheme = () => {
        setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
    };

    const isDark = theme === 'dark';

    const statusColor = backendStatus === 'online' ? 'bg-accent-green' : backendStatus === 'offline' ? 'bg-accent-red' : 'bg-accent-yellow';
    const statusText = backendStatus === 'online' ? 'System Online' : backendStatus === 'offline' ? 'Backend Offline' : 'Checking...';
    const statusTextColor = backendStatus === 'online' ? 'text-accent-green' : backendStatus === 'offline' ? 'text-accent-red' : 'text-accent-yellow';

    return (
        <motion.nav
            initial={{ y: -60, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="sticky top-0 z-50 glass-strong"
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Bot className="w-7 h-7 sm:w-8 sm:h-8 text-primary" />
                    <div>
                        <h1 className="text-lg sm:text-xl font-bold gradient-text leading-tight">
                            CI/CD Healing Agent
                        </h1>
                        <p className="text-[10px] sm:text-xs text-text-muted tracking-wider uppercase">
                            Autonomous DevOps • Powered by AI
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Theme Toggle */}
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={toggleTheme}
                        className="relative w-9 h-9 flex items-center justify-center rounded-xl
                          bg-surface-input border border-border hover:border-primary
                          text-text-secondary hover:text-primary transition-all duration-300 cursor-pointer"
                        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                    >
                        <motion.div
                            key={theme}
                            initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
                            animate={{ rotate: 0, opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3, ease: 'easeOut' }}
                        >
                            {isDark ? <FiSun size={16} /> : <FiMoon size={16} />}
                        </motion.div>
                    </motion.button>

                    {/* Live System Status */}
                    <div className="flex items-center gap-2">
                        <span className="relative flex h-2.5 w-2.5">
                            {backendStatus === 'online' && (
                                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${statusColor} opacity-75`}></span>
                            )}
                            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${statusColor} pulse-dot`}></span>
                        </span>
                        <span className={`text-xs sm:text-sm ${statusTextColor} font-medium`}>{statusText}</span>
                    </div>
                </div>
            </div>
        </motion.nav>
    );
}
