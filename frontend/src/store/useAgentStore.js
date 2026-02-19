import { create } from 'zustand';

const STEPS = [
    'Cloning repository',
    'Discovering test files',
    'Running tests',
    'Generating fixes',
    'Pushing to branch',
    'Monitoring CI/CD',
];

// Transform backend RunResult → frontend component format
function transformBackendResult(data) {
    const isError = data.status === 'ERROR';
    const fixes = data.fixes || [];
    const iterations = data.iterations || [];

    // Determine the real status: if backend says ERROR, honor it.
    // If pipeline didn't explicitly pass AND there are zero fixes with failures present, mark as ERROR.
    let finalStatus = data.status;
    if (!isError && fixes.length === 0 && iterations.length === 0 && data.status !== 'PASSED') {
        finalStatus = 'ERROR';
    }

    const isErrorFinal = finalStatus === 'ERROR';

    // Score: if ERROR, everything is 0. Otherwise derive dynamically.
    const rawScore = isErrorFinal ? 0 : (data.score || 0);
    const base = isErrorFinal ? 0 : 100;
    const speedBonus = rawScore > 100 ? rawScore - 100 : 0;
    const efficiencyPenalty = (!isErrorFinal && rawScore < 100) ? (100 - rawScore) : 0;

    return {
        repo_url: data.repo_url,
        team_name: data.team_name,
        leader_name: data.leader_name,
        branch_name: data.branch_name,
        total_failures: iterations[0]?.failed || 0,
        total_fixes: fixes.length,
        final_status: finalStatus,
        error_message: data.error_message || null,
        time_taken: data.started_at && data.finished_at
            ? (new Date(data.finished_at) - new Date(data.started_at)) / 1000
            : 0,
        fixes: fixes.map(f => ({
            file: f.file,
            bug_type: f.bug_type,
            line_number: f.line_number,
            commit_message: f.commit_message,
            status: f.status === 'VERIFIED' ? 'Fixed' : f.status === 'APPLIED' ? 'Applied' : 'Failed',
            dashboard_output: `${f.bug_type} error in ${f.file} line ${f.line_number}`,
            original_code: f.original_code || '',
            fixed_code: f.fixed_code || '',
        })),
        cicd_runs: iterations.map(iter => ({
            iteration: iter.number,
            status: iter.status,
            timestamp: iter.timestamp ? new Date(iter.timestamp).getTime() / 1000 : Date.now() / 1000,
            failures: iter.failed || 0,
            passed: iter.passed || 0,
            total: iter.total || 0,
        })),
        score: {
            base,
            speed_bonus: speedBonus,
            efficiency_penalty: efficiencyPenalty,
            total: rawScore,
        },
    };
}

const useAgentStore = create((set, get) => ({
    // Inputs
    repoUrl: '',
    teamName: '',
    leaderName: '',

    // Run state
    isRunning: false,
    currentStep: 0,
    steps: STEPS,

    // Live log
    liveLog: [],

    // Result
    result: null,
    error: null,

    // UI state
    fixFilterType: 'ALL',
    isLogExpanded: true,

    // Actions
    setField: (field, value) => set({ [field]: value }),
    setFixFilter: (filterType) => set({ fixFilterType: filterType }),
    toggleLog: () => set((s) => ({ isLogExpanded: !s.isLogExpanded })),

    addLog: (message, type = 'info') =>
        set((s) => ({
            liveLog: [
                ...s.liveLog,
                { timestamp: new Date().toISOString(), message, type },
            ],
        })),

    reset: () =>
        set({
            isRunning: false,
            currentStep: 0,
            liveLog: [],
            result: null,
            error: null,
        }),

    startAgent: async () => {
        const { repoUrl, teamName, leaderName, addLog } = get();
        if (!repoUrl || !teamName || !leaderName) return;

        set({ isRunning: true, currentStep: 0, liveLog: [], result: null, error: null });

        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

        addLog('🚀 Starting CI/CD Healing Agent...', 'info');

        // Simulate step progress while waiting for backend
        const stepInterval = setInterval(() => {
            const current = get().currentStep;
            if (current < STEPS.length - 1) {
                set({ currentStep: current + 1 });
                addLog(`⏳ ${STEPS[current + 1]}...`, 'progress');
            }
        }, 3000);

        // Warn user if taking too long
        const timeoutWarning = setTimeout(() => {
            addLog('⏰ This is taking longer than expected. The AI agent is still working...', 'progress');
        }, 180000); // 3 minutes

        try {
            const res = await fetch(`${apiUrl}/api/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    team_name: teamName,
                    leader_name: leaderName,
                }),
            });

            clearInterval(stepInterval);
            clearTimeout(timeoutWarning);

            if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
            const data = await res.json();

            // Transform backend response to match our store format
            const transformed = transformBackendResult(data);

            set({ result: transformed, isRunning: false, currentStep: STEPS.length });
            addLog('✅ Agent completed successfully!', 'success');
        } catch (err) {
            clearInterval(stepInterval);
            clearTimeout(timeoutWarning);
            set({ error: err.message, isRunning: false });
            addLog(`❌ Error: ${err.message}`, 'error');
        }
    },

    // Fetch latest results on page load
    fetchLatestResult: async () => {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        try {
            const res = await fetch(`${apiUrl}/api/results`);
            if (!res.ok) return; // 404 means no previous run
            const data = await res.json();
            const transformed = transformBackendResult(data);
            set({ result: transformed });
        } catch {
            // Silently ignore — page just shows empty state
        }
    },

    // Demo mode — load sample data without API
    loadDemo: () => {
        const demoResult = {
            repo_url: 'https://github.com/user/repo',
            team_name: 'RIFT ORGANISERS',
            leader_name: 'Saiyam Kumar',
            branch_name: 'RIFT_ORGANISERS_SAIYAM_KUMAR_AI_Fix',
            total_failures: 5,
            total_fixes: 5,
            final_status: 'PASSED',
            time_taken: 187.3,
            fixes: [
                { file: 'src/utils.py', bug_type: 'LINTING', line_number: 15, commit_message: '[AI-AGENT] Fix: remove unused import in src/utils.py', status: 'Fixed', dashboard_output: 'LINTING error in src/utils.py line 15 → Fix: remove the import statement' },
                { file: 'src/main.py', bug_type: 'SYNTAX', line_number: 42, commit_message: '[AI-AGENT] Fix: missing colon in if statement src/main.py', status: 'Fixed', dashboard_output: 'SYNTAX error in src/main.py line 42 → Fix: add missing colon' },
                { file: 'tests/test_api.py', bug_type: 'IMPORT', line_number: 3, commit_message: '[AI-AGENT] Fix: update import path in tests/test_api.py', status: 'Fixed', dashboard_output: 'IMPORT error in tests/test_api.py line 3 → Fix: correct import path' },
                { file: 'src/handler.py', bug_type: 'TYPE_ERROR', line_number: 87, commit_message: '[AI-AGENT] Fix: cast string to int in src/handler.py', status: 'Fixed', dashboard_output: 'TYPE_ERROR in src/handler.py line 87 → Fix: add int() cast' },
                { file: 'src/config.py', bug_type: 'LOGIC', line_number: 22, commit_message: '[AI-AGENT] Fix: correct comparison operator in src/config.py', status: 'Fixed', dashboard_output: 'LOGIC error in src/config.py line 22 → Fix: use == instead of =' },
            ],
            cicd_runs: [
                { iteration: 1, status: 'FAILED', timestamp: 1708300000, failures: 5 },
                { iteration: 2, status: 'FAILED', timestamp: 1708300060, failures: 3 },
                { iteration: 3, status: 'FAILED', timestamp: 1708300120, failures: 1 },
                { iteration: 4, status: 'PASSED', timestamp: 1708300180, failures: 0 },
            ],
            score: { base: 100, speed_bonus: 10, efficiency_penalty: 0, total: 110 },
        };

        set({
            repoUrl: 'https://github.com/user/repo',
            teamName: 'RIFT ORGANISERS',
            leaderName: 'Saiyam Kumar',
            result: demoResult,
            isRunning: false,
            currentStep: 6,
            liveLog: [
                { timestamp: '2026-02-19T12:00:00Z', message: '🚀 Starting CI/CD Healing Agent...', type: 'info' },
                { timestamp: '2026-02-19T12:00:01Z', message: '📂 Cloning repository...', type: 'progress' },
                { timestamp: '2026-02-19T12:00:05Z', message: '🔍 Discovered 12 test files', type: 'success' },
                { timestamp: '2026-02-19T12:00:10Z', message: '🧪 Running pytest suite...', type: 'progress' },
                { timestamp: '2026-02-19T12:00:15Z', message: '❌ 5 failures detected', type: 'error' },
                { timestamp: '2026-02-19T12:00:20Z', message: '🤖 Generating AI-powered fixes...', type: 'progress' },
                { timestamp: '2026-02-19T12:00:30Z', message: '✅ Fix applied: remove unused import in src/utils.py', type: 'success' },
                { timestamp: '2026-02-19T12:00:35Z', message: '✅ Fix applied: missing colon in src/main.py', type: 'success' },
                { timestamp: '2026-02-19T12:00:40Z', message: '✅ Fix applied: update import path in tests/test_api.py', type: 'success' },
                { timestamp: '2026-02-19T12:00:45Z', message: '✅ Fix applied: cast string to int in src/handler.py', type: 'success' },
                { timestamp: '2026-02-19T12:00:50Z', message: '✅ Fix applied: correct comparison in src/config.py', type: 'success' },
                { timestamp: '2026-02-19T12:00:55Z', message: '📤 Pushing fixes to branch...', type: 'progress' },
                { timestamp: '2026-02-19T12:01:00Z', message: '🔄 CI/CD Iteration 1/5 — FAILED (5 failures)', type: 'error' },
                { timestamp: '2026-02-19T12:02:00Z', message: '🔄 CI/CD Iteration 2/5 — FAILED (3 failures)', type: 'error' },
                { timestamp: '2026-02-19T12:03:00Z', message: '🔄 CI/CD Iteration 3/5 — FAILED (1 failure)', type: 'error' },
                { timestamp: '2026-02-19T12:03:07Z', message: '🔄 CI/CD Iteration 4/5 — PASSED ✅', type: 'success' },
                { timestamp: '2026-02-19T12:03:10Z', message: '🎉 All tests passing! Pipeline healed.', type: 'success' },
            ],
        });
    },
}));

export default useAgentStore;
