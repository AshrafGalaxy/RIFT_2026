# RIFT 2026 — Frontend Remaining Tasks

> **Context**: The backend is fully built and working (FastAPI + CrewAI + Gemini 2.0 Flash). The frontend UI components are fully built. The core API integration (`POST /api/run`) is working correctly. The `transformBackendResult()` function correctly maps backend data to component format.
>
> **Your job**: Implement the 5 remaining UX/polish features listed below. All changes are in `src/store/useAgentStore.js`, `src/App.jsx`, `src/components/Navbar.jsx`, and `src/components/HeroInput.jsx`.

---

## CURRENT STATE (What Already Works ✅)

| Component | File | Status |
|-----------|------|--------|
| Navbar | `Navbar.jsx` | ✅ Good — has a hardcoded "System Online" green dot |
| HeroInput | `HeroInput.jsx` | ✅ Good — 3 fields, "Analyze Repository" + "Load Demo" buttons |
| RunSummary | `RunSummary.jsx` | ✅ Good — shows repo, team, branch, failures, fixes, time, PASSED/FAILED badge |
| ScoreBreakdown | `ScoreBreakdown.jsx` | ✅ Good — animated ring + bar chart |
| FixesTable | `FixesTable.jsx` | ✅ Good — file, bug type, line #, commit msg, status with filter |
| CICDTimeline | `CICDTimeline.jsx` | ✅ Good — per-iteration visualization |
| ActivityLog | `ActivityLog.jsx` | ✅ Good — timestamped log entries |
| Footer | `Footer.jsx` | ✅ Good |
| Skeletons | `Skeletons.jsx` | ✅ Good — loading states |
| **Store** | `useAgentStore.js` | ✅ Good — `startAgent()`, `transformBackendResult()`, `loadDemo()`, `reset()` all work |

> [!NOTE]
> The store already has a `reset()` function defined. It's just not wired to any button in the UI.

---

## TASK 1: Add "New Run" / Reset Button

**Priority**: 🔴 P0 — Critical

**Problem**: After a run completes (result is displayed), the user has to refresh the page to start a new run. There's no way to go back to the input form.

**Where to change**: `src/components/HeroInput.jsx`

**What to do**: After a run completes (`result !== null && !isRunning`), show a "🔄 New Run" button that calls the existing `reset()` action from the store.

```jsx
// In HeroInput.jsx, add `reset` to the destructured store values:
const {
    repoUrl, teamName, leaderName, isRunning, currentStep, steps,
    setField, startAgent, loadDemo, reset,
    result,   // ← ADD THIS
} = useAgentStore();

// Then add a "New Run" button next to the existing buttons.
// Show it when result exists and agent is not running:
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
```

**Where to place it**: Inside the `{/* Buttons */}` flex container (line 67), alongside the existing "Analyze Repository" and "Load Demo" buttons.

---

## TASK 2: Error State UI Banner

**Priority**: 🔴 P0 — Critical

**Problem**: When the backend returns an error (e.g., network failure, 500 error), the `error` state is set in the Zustand store. But the error only shows inside the ActivityLog component as a log entry. There's no visible banner the user can see without scrolling down.

**Where to change**: `src/App.jsx`

**What to do**: Add an `ErrorBanner` component that reads the `error` state from the store and renders a dismissible error banner at the top of the page.

```jsx
// In App.jsx, add this component above the export:
import { AnimatePresence, motion } from 'framer-motion';
import useAgentStore from './store/useAgentStore';

function ErrorBanner() {
    const error = useAgentStore((s) => s.error);
    const reset = useAgentStore((s) => s.reset);

    if (!error) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="max-w-5xl mx-auto px-4 sm:px-6 pt-6"
            >
                <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span className="text-xl">❌</span>
                        <div>
                            <p className="text-accent-red font-semibold text-sm">Pipeline Error</p>
                            <p className="text-text-secondary text-xs mt-0.5">{error}</p>
                        </div>
                    </div>
                    <button
                        onClick={reset}
                        className="text-text-muted hover:text-text-primary text-xs px-3 py-1.5 rounded-lg
                          border border-border hover:border-primary transition-all cursor-pointer"
                    >
                        Dismiss
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}

// Then add it in the App layout, right after <HeroInput />:
export default function App() {
    return (
        <div className="min-h-screen flex flex-col">
            <Navbar />
            <main className="flex-1">
                <HeroInput />
                <ErrorBanner />      {/* ← ADD THIS */}
                <RunSummary />
                <ScoreBreakdown />
                <FixesTable />
                <CICDTimeline />
                <ActivityLog />
            </main>
            <Footer />
        </div>
    );
}
```

---

## TASK 3: Fetch Latest Results on Page Load

**Priority**: 🟡 P1 — Important

**Problem**: When the user returns to the page after a previous run, they see a blank page. The `GET /api/results` endpoint returns the latest `results.json` from the server, but the frontend never calls it.

**Where to change**: `src/store/useAgentStore.js` + `src/App.jsx`

**What to do**:

### Step 1: Add `fetchLatestResult()` to the store

```javascript
// Add this action to the store (inside create()):

fetchLatestResult: async () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
        const res = await fetch(`${apiUrl}/api/results`);
        if (!res.ok) return; // 404 means no previous run, that's fine
        const data = await res.json();
        const transformed = transformBackendResult(data);
        set({ result: transformed });
    } catch {
        // Silently ignore — page just shows empty state
    }
},
```

### Step 2: Call it on mount in `App.jsx`

```jsx
import { useEffect } from 'react';
import useAgentStore from './store/useAgentStore';

export default function App() {
    const fetchLatestResult = useAgentStore((s) => s.fetchLatestResult);

    useEffect(() => {
        fetchLatestResult();
    }, []);

    return (
        // ... existing JSX
    );
}
```

---

## TASK 4: Loading Timeout Warning

**Priority**: 🟡 P1 — Important

**Problem**: If the backend takes > 5 minutes, the frontend shows the loading spinner forever. No timeout or warning is shown.

**Where to change**: `src/store/useAgentStore.js` → inside `startAgent()`

**What to do**: Add a 3-minute timeout that logs a warning message. The request still continues, but the user gets feedback.

```javascript
// Inside startAgent(), right after the stepInterval declaration, add:

const timeoutWarning = setTimeout(() => {
    addLog('⏰ This is taking longer than expected. Please wait...', 'progress');
}, 180000); // 3 minutes

// Then in BOTH the try block (after clearInterval) and catch block:
clearTimeout(timeoutWarning);
```

**Full updated startAgent with timeout**:

```javascript
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
```

---

## TASK 5: Live Health Check Indicator in Navbar

**Priority**: 🟡 P1 — Nice to Have

**Problem**: The Navbar currently shows a hardcoded "System Online" green dot. It doesn't actually check if the backend is running.

**Where to change**: `src/components/Navbar.jsx`

**What to do**: On mount, call `GET /api/health` and show the real status. Optionally poll every 30 seconds.

```jsx
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export default function Navbar() {
    const [backendStatus, setBackendStatus] = useState('checking'); // 'online' | 'offline' | 'checking'

    useEffect(() => {
        const checkHealth = async () => {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            try {
                const res = await fetch(`${apiUrl}/api/health`);
                if (res.ok) {
                    setBackendStatus('online');
                } else {
                    setBackendStatus('offline');
                }
            } catch {
                setBackendStatus('offline');
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 30000); // Re-check every 30s
        return () => clearInterval(interval);
    }, []);

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
                    <span className="text-2xl sm:text-3xl">🤖</span>
                    <div>
                        <h1 className="text-lg sm:text-xl font-bold gradient-text leading-tight">
                            CI/CD Healing Agent
                        </h1>
                        <p className="text-[10px] sm:text-xs text-text-muted tracking-wider uppercase">
                            Autonomous DevOps • Powered by AI
                        </p>
                    </div>
                </div>

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
        </motion.nav>
    );
}
```

---

## 🔌 BACKEND API REFERENCE (For Your Reference)

### `POST /api/run` — Trigger Healing Pipeline

```json
// REQUEST
{
    "repo_url": "https://github.com/user/repo",
    "team_name": "Code Warriors",
    "leader_name": "John Doe"
}

// RESPONSE (RunResult)
{
    "repo_url": "https://github.com/user/repo",
    "branch_name": "CODE_WARRIORS_JOHN_DOE_AI_Fix",
    "team_name": "Code Warriors",
    "leader_name": "John Doe",
    "status": "PASSED",                          // PASSED | FAILED | ERROR
    "score": 110,
    "total_commits": 3,
    "started_at": "2026-02-19T08:30:00.000000",
    "finished_at": "2026-02-19T08:30:45.000000",
    "error_message": null,
    "fixes": [
        {
            "file": "src/utils.py",
            "bug_type": "IMPORT",
            "line_number": 3,
            "original_code": "import colections",
            "fixed_code": "import collections",
            "commit_message": "[AI-AGENT] Fix IMPORT in src/utils.py:3",
            "status": "VERIFIED"                // PENDING | APPLIED | VERIFIED | FAILED
        }
    ],
    "iterations": [
        {
            "number": 0,
            "passed": 8,
            "failed": 3,
            "total": 11,
            "errors_found": 0,
            "fixes_applied": 0,
            "status": "FAILED",
            "timestamp": "2026-02-19T08:30:00.000000"
        }
    ]
}
```

### `GET /api/results` — Fetch Latest Run Results

Returns the same `RunResult` JSON from the most recent run. Returns `404` if no run has been done yet.

### `GET /api/health` — Health Check

```json
{ "status": "healthy", "service": "RIFT Self-Healing CI/CD", "version": "1.0.0" }
```

---

## EXISTING DESIGN SYSTEM (Use These Classes)

| Class | Effect | Use For |
|-------|--------|---------|
| `.glass` | Glassmorphism card (blur + border) | Card containers |
| `.glass-strong` | Stronger glassmorphism | Navbar, elevated elements |
| `.gradient-text` | Purple-pink gradient text | Headings |
| `.btn-gradient` | Purple-pink gradient button with hover glow | Primary actions |
| `.glow-green` / `.glow-red` / `.glow-purple` | Subtle glow effects | Status indicators |
| `text-text-primary` / `text-text-secondary` / `text-text-muted` | Text hierarchy | All text |
| `text-accent-green` / `text-accent-red` / `text-accent-yellow` | Status colors | Success/Error/Warning |
| `border-border` / `border-border-light` | Border colors | Containers, dividers |
| `bg-surface-input` | Input field background | Form elements |
| `.pulse-dot` | Green pulsing dot | Online indicator |

---

## 📝 SUMMARY CHECKLIST

| # | Task | Files to Change | Priority |
|---|------|----------------|----------|
| 1 | Add "New Run" / Reset Button | `HeroInput.jsx` | 🔴 P0 |
| 2 | Error State Banner | `App.jsx` | 🔴 P0 |
| 3 | Fetch Latest Results on Load | `useAgentStore.js`, `App.jsx` | 🟡 P1 |
| 4 | Loading Timeout Warning | `useAgentStore.js` | 🟡 P1 |
| 5 | Live Health Check in Navbar | `Navbar.jsx` | 🟡 P1 |

---

## 🧪 HOW TO TEST

1. Start backend:

   ```bash
   cd backend
   py -3.12 -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Start frontend:

   ```bash
   cd frontend
   npm run dev
   ```

3. Open `http://localhost:5173`
4. **Test Task 5**: Check Navbar shows green "System Online" (if backend is running) or red "Backend Offline" (if not)
5. **Test Task 1 & 2**: Click "Load Demo" → results appear → click "New Run" → form resets
6. **Test Task 2**: Stop the backend → click "Analyze Repository" → error banner should appear
7. **Test Task 3**: Run the pipeline once → refresh page → results should load from `GET /api/results`
8. **Test Task 4**: Only testable with a slow repo or by adding a `sleep()` in backend
