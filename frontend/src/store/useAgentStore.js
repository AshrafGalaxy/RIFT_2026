import { create } from 'zustand';

const BACKEND = 'http://localhost:8000';

// Steps in the pipeline, updated in real-time from SSE
const PIPELINE_STEPS = [
  'Cloning repository',
  'Discovering tests',
  'Running tests',
  'Generating fixes',
  'Pushing to branch',
  'Monitoring CI/CD',
];

const useAgentStore = create((set, get) => ({
  // ---- State ----
  repoUrl: '',
  teamName: '',
  leaderName: '',
  maxIterations: 5,
  isRunning: false,
  currentStep: -1,            // index into PIPELINE_STEPS
  result: null,
  liveLog: [],                // array of { message, type, agent?, timestamp }
  error: null,
  backendOnline: false,
  fixFilterType: 'ALL',

  // ---- Actions ----
  setRepoUrl: (url) => set({ repoUrl: url }),
  setTeamName: (name) => set({ teamName: name }),
  setLeaderName: (name) => set({ leaderName: name }),
  setMaxIterations: (n) => set({ maxIterations: n }),
  setFixFilter: (type) => set({ fixFilterType: type }),

  checkBackend: async () => {
    try {
      const res = await fetch(`${BACKEND}/api/health`);
      set({ backendOnline: res.ok });
    } catch {
      set({ backendOnline: false });
    }
  },

  // Start the pipeline with SSE streaming
  startRun: async () => {
    const { repoUrl, teamName, leaderName } = get();
    if (!repoUrl) return;

    set({
      isRunning: true,
      currentStep: 0,
      result: null,
      liveLog: [],
      error: null,
      fixFilterType: 'ALL',
    });

    const addLog = (message, type = 'info', agent = null) => {
      set((state) => ({
        liveLog: [
          ...state.liveLog,
          {
            message,
            type,
            agent,
            timestamp: new Date().toISOString(),
          },
        ],
      }));
    };

    addLog('Pipeline started — connecting to backend...', 'info', 'System');

    try {
      const response = await fetch(`${BACKEND}/api/run-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          team_name: teamName || 'RIFT_Team',
          leader_name: leaderName || 'Agent',
          max_iterations: get().maxIterations,
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        let eventType = 'log';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
            continue;
          }
          if (line.startsWith('data: ')) {
            const rawData = line.slice(6);
            try {
              const data = JSON.parse(rawData);
              handleSSEEvent(eventType, data, set, get, addLog);
            } catch {
              // Not JSON — plain text
              if (rawData.trim()) {
                addLog(rawData, 'info');
              }
            }
            eventType = 'log'; // Reset after consuming
            continue;
          }
        }
      }

    } catch (err) {
      console.error('SSE stream error:', err);
      set({ error: err.message });
      addLog(`Connection error: ${err.message}`, 'error', 'System');

      // Fallback: try blocking POST
      try {
        addLog('Falling back to blocking API call...', 'info', 'System');
        const res = await fetch(`${BACKEND}/api/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repo_url: get().repoUrl,
            team_name: get().teamName || 'RIFT_Team',
            leader_name: get().leaderName || 'Agent',
          }),
        });
        if (res.ok) {
          const data = await res.json();
          const transformed = transformBackendResult(data);
          set({ result: transformed, error: null });
          addLog('Pipeline complete (blocking fallback)', 'success', 'System');
        }
      } catch (fallbackErr) {
        set({ error: fallbackErr.message });
        addLog(`Fallback also failed: ${fallbackErr.message}`, 'error', 'System');
      }
    }

    set({ isRunning: false, currentStep: -1 });
  },

  // Load demo data (no backend needed)
  loadDemo: () => {
    const demo = generateDemoData();
    set({
      result: demo,
      isRunning: false,
      currentStep: -1,
      error: null,
      liveLog: [
        { message: 'Demo data loaded — this is simulated data', type: 'info', agent: 'System', timestamp: new Date().toISOString() },
        { message: 'Clone Agent: Cloned demo repository', type: 'info', agent: 'Clone Agent', timestamp: new Date().toISOString() },
        { message: 'Discover Agent: Found 8 tests (pytest)', type: 'info', agent: 'Discover Agent', timestamp: new Date().toISOString() },
        { message: 'Analyze Agent: Found 3 errors (SYNTAX, IMPORT, INDENTATION)', type: 'info', agent: 'Analyze Agent', timestamp: new Date().toISOString() },
        { message: 'Heal Agent: Applied 3 fixes, pushed to branch', type: 'success', agent: 'Heal Agent', timestamp: new Date().toISOString() },
        { message: 'Verify Agent: All 8 tests passed!', type: 'success', agent: 'Verify Agent', timestamp: new Date().toISOString() },
        { message: 'Pipeline complete: PASSED -- Score: 110/120', type: 'success', agent: 'System', timestamp: new Date().toISOString() },
      ],
    });
  },

  // Reset
  reset: () =>
    set({
      isRunning: false,
      currentStep: -1,
      result: null,
      liveLog: [],
      error: null,
    }),
}));


// ---- SSE Event Handler ----

function handleSSEEvent(type, data, set, get, addLog) {
  switch (type) {
    case 'step':
      // { step, index, message }
      set({ currentStep: data.index ?? get().currentStep });
      addLog(data.message || `Step: ${data.step}`, 'info', null);
      break;

    case 'agent':
      // { agent, message, type }
      addLog(data.message, data.type || 'info', data.agent);
      break;

    case 'iteration':
      // { number, passed, failed, total, status, fixes_applied, new_fixes }
      addLog(
        `Iteration ${data.number}: ${data.passed} passed, ${data.failed} failed (${data.status})`,
        data.status === 'PASSED' ? 'success' : 'error',
        'Verify Agent'
      );

      // Update result state incrementally so UI updates in real-time
      const incomingFixes = (data.new_fixes || []).map(f => ({
          file: f.file,
          bug_type: f.bug_type,
          line_number: f.line_number,
          original_code: f.original_code || '',
          fixed_code: f.fixed_code || '',
          commit_message: f.commit_message || '',
          status: f.status || 'PENDING'
      }));

      set((state) => {
          // Initialize result if null (so UI shows up early)
          const currentResult = state.result || {
              repo_url: '...', // placeholder
              iterations: [],
              fixes: [],
              final_status: 'RUNNING',
              score: { overall: 0, breakdown: [] },
              total_commits: 0
          };

          // Append iteration
          const newIterations = [...(currentResult.iterations || []), {
              number: data.number,
              passed: data.passed,
              failed: data.failed,
              total: data.total,
              status: data.status,
              fixes_applied: data.fixes_applied || 0,
              timestamp: new Date().toISOString()
          }];

          // Append fixes
          const newFixesList = [...(currentResult.fixes || []), ...incomingFixes];
          
          // Compute derived fields for UI
          const totalFixes = newFixesList.filter(f => f.status === 'APPLIED' || f.status === 'VERIFIED').length;
          const startDate = currentResult.started_at ? new Date(currentResult.started_at) : new Date();
          const timeTaken = (new Date() - startDate) / 1000;

          return {
              result: {
                  ...currentResult,
                  started_at: currentResult.started_at || startDate.toISOString(),
                  iterations: newIterations,
                  fixes: newFixesList,
                  failed_tests: data.failed,
                  passed_tests: data.passed,
                  total_tests: data.total,
                  final_status: data.status, // Update status too
                  // Computed fields
                  total_failures: data.failed, 
                  total_fixes: totalFixes,
                  time_taken: timeTaken,
              }
          };
      });
      break;

    case 'log':
      // { message, type }
      addLog(data.message, data.type || 'info', null);
      break;

    case 'error':
      // { message }
      set({ error: data.message });
      addLog(`Error: ${data.message}`, 'error', 'System');
      break;

    case 'result':
      // Full RunResult JSON
      const transformed = transformBackendResult(data);
      set({ result: transformed, error: null });
      break;

    case 'done':
      addLog('Stream ended — pipeline complete', 'info', 'System');
      break;

    default:
      if (data.message) {
        addLog(data.message, data.type || 'info', data.agent || null);
      }
  }
}


// ---- Transform Backend Result for Components ----

function transformBackendResult(data) {
  if (!data) return null;

  const iterations = (data.iterations || []).map((iter) => ({
    number: iter.number,
    passed: iter.passed || 0,
    failed: iter.failed || 0,
    total: iter.total || 0,
    errors_found: iter.errors_found || 0,
    fixes_applied: iter.fixes_applied || 0,
    status: iter.status || 'FAILED',
    timestamp: iter.timestamp,
  }));

  const fixes = (data.fixes || []).map((f) => ({
    file: f.file,
    bug_type: f.bug_type,
    line_number: f.line_number,
    original_code: f.original_code || '',
    fixed_code: f.fixed_code || '',
    commit_message: f.commit_message || '',
    status: f.status || 'PENDING',
  }));

  // Determine final status from the last iteration (most accurate)
  let finalStatus = data.status || 'FAILED';
  if (iterations.length > 0) {
    const lastIter = iterations[iterations.length - 1];
    if (lastIter.status === 'PASSED' || (lastIter.failed === 0 && lastIter.total > 0)) {
      finalStatus = 'PASSED';
    }
  }

  const totalTests = iterations.length > 0 ? iterations[iterations.length - 1].total : 0;
  const passedTests = iterations.length > 0 ? iterations[iterations.length - 1].passed : 0;
  const failedTests = iterations.length > 0 ? iterations[iterations.length - 1].failed : 0;

  // Compute score breakdown from raw integer (backend returns 0-120)
  const rawScore = data.score ?? 0;
  const scoreObj = computeScoreBreakdown(rawScore, data.total_commits || 0, finalStatus);

  // Compute time_taken from started_at / finished_at
  let timeTaken = 0;
  if (data.started_at && data.finished_at) {
    timeTaken = (new Date(data.finished_at) - new Date(data.started_at)) / 1000;
  }

  // Count total failures (initial) and fixes applied
  const totalFixes = fixes.filter(f => f.status === 'APPLIED' || f.status === 'VERIFIED').length;

  return {
    repo_url: data.repo_url || '',
    branch_name: data.branch_name || '',
    team_name: data.team_name || '',
    leader_name: data.leader_name || '',
    final_status: finalStatus,
    score: scoreObj,
    total_commits: data.total_commits || 0,
    total_tests: totalTests,
    passed_tests: passedTests,
    failed_tests: failedTests,
    total_failures: failedTests,
    total_fixes: totalFixes,
    time_taken: timeTaken,
    iterations,
    fixes,
    cicd_runs: iterations,
    started_at: data.started_at || '',
    finished_at: data.finished_at || '',
    error_message: data.error_message || null,
  };
}


// ---- Score Breakdown Computation ----

function computeScoreBreakdown(rawScore, totalCommits, finalStatus) {
  // Backend rules: base=100, speed_bonus=10 (if <5min), penalty=-2 per commit over 20
  // If pipeline didn't pass, show the raw score directly
  if (rawScore === 0) {
    return { base: 0, speed_bonus: 0, efficiency_penalty: 0, total: 0 };
  }

  const base = Math.min(rawScore, 100);
  const hasSpeedBonus = rawScore > 100;
  const speed_bonus = hasSpeedBonus ? Math.min(rawScore - 100, 10) : 0;
  const excessCommits = Math.max(0, totalCommits - 20);
  const efficiency_penalty = excessCommits * 2;
  const total = rawScore;

  return { base, speed_bonus, efficiency_penalty, total };
}

// ---- Demo Data ----

function generateDemoData() {
  const now = new Date();
  return {
    repo_url: 'https://github.com/AshrafGalaxy/dummy-python-healing-repo',
    branch_name: 'ASHRAFGALAXY_AGENT_AI_Fix',
    team_name: 'AshrafGalaxy',
    leader_name: 'Agent',
    final_status: 'PASSED',
    score: { base: 100, speed_bonus: 10, efficiency_penalty: 0, total: 110 },
    total_commits: 3,
    total_tests: 8,
    passed_tests: 8,
    failed_tests: 0,
    total_failures: 3,
    total_fixes: 3,
    time_taken: 45,
    iterations: [
      {
        number: 1,
        passed: 5,
        failed: 3,
        total: 8,
        errors_found: 3,
        fixes_applied: 3,
        status: 'FAILED',
        timestamp: new Date(now - 60000).toISOString(),
      },
      {
        number: 2,
        passed: 8,
        failed: 0,
        total: 8,
        errors_found: 0,
        fixes_applied: 0,
        status: 'PASSED',
        timestamp: new Date(now - 30000).toISOString(),
      },
    ],
    fixes: [
      {
        file: 'calculator.py',
        bug_type: 'SYNTAX',
        line_number: 15,
        original_code: 'def add(a, b)',
        fixed_code: 'def add(a, b):',
        commit_message: '[AI-AGENT] Fix SYNTAX in calculator.py:15',
        status: 'VERIFIED',
      },
      {
        file: 'utils.py',
        bug_type: 'IMPORT',
        line_number: 3,
        original_code: 'from colections import OrderedDict',
        fixed_code: 'from collections import OrderedDict',
        commit_message: '[AI-AGENT] Fix IMPORT in utils.py:3',
        status: 'VERIFIED',
      },
      {
        file: 'models.py',
        bug_type: 'INDENTATION',
        line_number: 22,
        original_code: '      return self.value',
        fixed_code: '        return self.value',
        commit_message: '[AI-AGENT] Fix INDENTATION in models.py:22',
        status: 'VERIFIED',
      },
    ],
    cicd_runs: [
      {
        number: 1,
        passed: 5,
        failed: 3,
        total: 8,
        errors_found: 3,
        fixes_applied: 3,
        status: 'FAILED',
        timestamp: new Date(now - 60000).toISOString(),
      },
      {
        number: 2,
        passed: 8,
        failed: 0,
        total: 8,
        errors_found: 0,
        fixes_applied: 0,
        status: 'PASSED',
        timestamp: new Date(now - 30000).toISOString(),
      },
    ],
    started_at: new Date(now - 90000).toISOString(),
    finished_at: now.toISOString(),
    error_message: null,
  };
}


export default useAgentStore;
