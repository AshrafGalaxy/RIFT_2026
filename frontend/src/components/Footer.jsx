import { FiGithub } from 'react-icons/fi';
import useAgentStore from '../store/useAgentStore';

export default function Footer() {
    const teamName = useAgentStore((s) => s.result?.team_name || s.teamName);

    return (
        <footer className="border-t border-border-light mt-8">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-text-muted">
                <p>
                    Built for <span className="text-primary-light font-medium">RIFT 2026 Hackathon</span> • AI/ML Track
                </p>
                <div className="flex items-center gap-3">
                    {teamName && <span className="text-text-secondary">{teamName}</span>}
                    <a
                        href="https://github.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-text-muted hover:text-primary transition-colors"
                    >
                        <FiGithub size={16} />
                    </a>
                </div>
            </div>
        </footer>
    );
}
