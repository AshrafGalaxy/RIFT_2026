# RIFT 2026 — Self-Healing CI/CD Agent

> **Autonomous DevOps Agent with React Dashboard**
> Built for the RIFT 2026 Hackathon — AI/ML Track

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Deployed-brightgreen)](#)
[![Video Demo](https://img.shields.io/badge/LinkedIn-Video%20Demo-blue)](#)

---

## Project Overview

An **Autonomous CI/CD Healing Agent** that takes a GitHub repository URL, clones and analyzes the codebase, discovers and runs all test files automatically, identifies failures, generates targeted fixes, commits them with `[AI-AGENT]` prefix to a new branch, and iterates until all tests pass — all displayed in a real-time React dashboard.

### Key Features

- **Zero Human Intervention** — fully autonomous from URL input to healed pipeline
- **Multi-Strategy Error Detection** — `py_compile` syntax scan + pytest output parsing + import chain tracing + unused import linting
- **Verified Fixes** — every fix is validated with `py_compile` before committing; failed fixes are auto-reverted
- **Fast Execution** — complete pipeline runs in ~20-30 seconds (direct agent calls bypass LLM overhead)
- **Comprehensive Dashboard** — input section, run summary, score breakdown, fixes table, CI/CD timeline, activity log

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                  React Dashboard                      │
│  (Input → Summary → Score → Fixes → Timeline → Log)  │
└───────────────────────┬──────────────────────────────┘
                        │ REST API (POST /api/run)
                        ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8000)               │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │           Crew Orchestrator (Pipeline)            │ │
│  │                                                    │ │
│  │  1. Clone Agent ─────→ git clone repo              │ │
│  │  2. Discover Agent ──→ detect framework, run tests │ │
│  │  3. ┌── Loop (max 5 iterations) ──────────────┐   │ │
│  │     │  Analyze Agent → find errors (4 strategies)│  │ │
│  │     │  Heal Agent ───→ fix & verify with py_compile│ │
│  │     │  Verify Agent ─→ re-run tests               │ │
│  │     └─────────────────────────────────────────┘   │ │
│  │  4. Compute Score & Save results.json              │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  5 CrewAI Agents (multi-agent architecture)            │
│  Docker sandbox (with local subprocess fallback)       │
└──────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 7, Tailwind CSS 4, Zustand, Recharts, Framer Motion |
| **Backend** | Python 3.10, FastAPI, Uvicorn, CrewAI |
| **AI/LLM** | Google Gemini 2.0 Flash (via LiteLLM) |
| **Version Control** | GitPython |
| **Containerization** | Docker (with local fallback) |

---

## Supported Bug Types

| Bug Type | Detection Method | Fix Strategy |
|----------|-----------------|-------------|
| **SYNTAX** | `py_compile` scan | Add missing colon, close parens/brackets, remove garbage |
| **INDENTATION** | `py_compile` scan | Realign to surrounding context, tabs → spaces |
| **IMPORT** | Pytest output + import chain tracing | Fix module typos, trace to root cause source file |
| **TYPE_ERROR** | Pytest output parsing | Add type conversions (`str()`, `int()`) |
| **LINTING** | AST-free unused import scan | Remove unused import lines |
| **LOGIC** | Pytest output parsing | Fix `=` vs `==`, off-by-one errors |

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git
- A Gemini API key (or Anthropic API key)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_REPO_URL
cd Rift
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `/backend`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Start Both Servers

**Backend** (port 8000):
```bash
cd backend
python main.py
```

**Frontend** (port 5173):
```bash
cd frontend
npm run dev
```

### 5. Open Dashboard

Navigate to `http://localhost:5173` in your browser.

---

## Usage

1. Enter a **GitHub repository URL** (e.g., `https://github.com/riddhiBalapure/error`)
2. Enter your **Team Name** and **Team Leader Name**
3. Click **"Analyze Repository"**
4. Watch the agent automatically:
   - Clone the repo
   - Discover and run tests
   - Detect all errors
   - Apply verified fixes
   - Push to `TEAM_NAME_LEADER_NAME_AI_Fix` branch
   - Iterate until all tests pass
5. View results in the dashboard: summary, score, fixes table, CI/CD timeline

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Start the self-healing pipeline |
| `GET` | `/api/results` | Get the latest run results |
| `GET` | `/api/health` | Health check |

### Example Request

```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo", "team_name": "KODA", "leader_name": "Riddhi"}'
```

---

## Branch Naming

Branches are created in the format:
```
TEAM_NAME_LEADER_NAME_AI_Fix
```

All uppercase, spaces replaced with underscores, ending with `_AI_Fix`.

Example: Team "Code Warriors", Leader "John Doe" → `CODE_WARRIORS_JOHN_DOE_AI_Fix`

---

## Scoring

| Component | Points |
|-----------|--------|
| Base Score (all tests pass) | 100 |
| Speed Bonus (< 5 minutes) | +10 |
| Efficiency Penalty (> 20 commits) | -2 each |
| **Maximum** | **110** |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Google Gemini API key |
| `ANTHROPIC_API_KEY` | Alt* | Anthropic Claude API key |
| `VITE_API_URL` | No | Backend URL (default: `http://localhost:8000`) |

*At least one AI provider key is required.

---

## Known Limitations

- Logic bugs (e.g., wrong algorithm) require LLM reasoning and are harder to auto-fix
- Only Python and Node.js projects are supported for test discovery
- Docker sandbox requires Docker Desktop running (falls back to local subprocess)
- Push to remote requires the repo to have write access configured

---

## Project Structure

```
Rift/
├── README.md
├── results.json              # Generated after each run
├── backend/
│   ├── main.py               # FastAPI app
│   ├── config.py             # Configuration constants
│   ├── crew_orchestrator.py  # Pipeline orchestrator
│   ├── models.py             # Pydantic models
│   ├── utils.py              # Scoring, branch naming
│   ├── agents/
│   │   ├── clone_agent.py    # Repository cloning
│   │   ├── discover_agent.py # Test discovery & execution
│   │   ├── analyze_agent.py  # Error detection (4 strategies)
│   │   ├── heal_agent.py     # Fix generation & verification
│   │   └── verify_agent.py   # Post-fix test re-run
│   └── services/
│       ├── docker_service.py # Sandbox execution
│       ├── git_service.py    # Branch, commit, push
│       └── results_service.py# results.json persistence
└── frontend/
    └── src/
        ├── App.jsx
        ├── store/useAgentStore.js  # Zustand state management
        └── components/
            ├── HeroInput.jsx       # Input section
            ├── RunSummary.jsx      # Run summary card
            ├── ScoreBreakdown.jsx  # Score panel + chart
            ├── FixesTable.jsx      # Fixes applied table
            ├── CICDTimeline.jsx    # CI/CD timeline
            ├── ActivityLog.jsx     # Live activity log
            └── Navbar.jsx / Footer.jsx
```

---

## Team

| Role | Name |
|------|------|
| Team Name | KODA |
| Team Leader | Riddhi |

---

## Deployment

- **Frontend**: Deployed on [Vercel/Netlify/Railway] — *URL TBD*
- **Backend**: Deployed on [Railway/Render] — *URL TBD*

---

## License

Built for the RIFT 2026 Hackathon — AI/ML Track.
