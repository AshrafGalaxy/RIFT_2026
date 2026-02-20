# Autonomous Self-Healing CI CD Pipeline

**Autonomous Self-Healing CI/CD Pipeline**

[![Deployment](https://img.shields.io/badge/Deployment-Live-brightgreen)](https://rift26-one.vercel.app/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Watch%20Demo-blue)](https://www.linkedin.com/posts/purvesh-didpaye-05b723345_rift2026-hackathon-ai-ugcPost-7430439869786755072-0yq9?utm_source=share&utm_medium=member_android&rcm=ACoAAFZtGocBtZQO4BlNgkBzcVnDZVnJdFQomQw)

## 🚀 Deployment

- **Frontend**: [Vercel](https://rift26-one.vercel.app/)
- **Backend**: Render

## 🏗️ Architecture Diagram

```mermaid
graph LR
    %% Styles
    classDef user fill:#FFB6C1,stroke:#333,stroke-width:2px,color:black,font-weight:bold
    classDef frontend fill:#E0F7FA,stroke:#00ACC1,stroke-width:2px,color:black,font-weight:bold
    classDef backend fill:#E8F5E9,stroke:#43A047,stroke-width:2px,color:black,font-weight:bold
    classDef ai fill:#F3E5F5,stroke:#8E24AA,stroke-width:2px,color:black,font-weight:bold
    classDef ext fill:#FFF3E0,stroke:#FB8C00,stroke-width:2px,color:black
    classDef db fill:#ECEFF1,stroke:#546E7A,stroke-width:2px,color:black

    subgraph Canvas [Autonomous CI/CD Ecosystem]
        direction LR
        style Canvas fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black

        %% Nodes
        User([👤 User]):::user
        GitHub[🐱 GitHub Repo]:::ext
        Gemini[🧠 Gemini AI]:::ai

        subgraph Platform [Platform Internal]
            direction TB
            style Platform fill:#fff,stroke:#999,stroke-width:1px
            
            Frontend[🖥️ Dashboard]:::frontend
            Backend[⚙️ Backend API]:::backend
            Results[(📊 Results)]:::db
            
            subgraph Engine [Execution Engine]
                style Engine fill:#F5F5F5,stroke:#ccc,stroke-width:1px
                Orchestrator[🎼 Agents]:::backend
                Sandbox[📦 Sandbox]:::ext
            end
        end

        %% Connections within Canvas
        User -->|1. URL| Frontend
        Frontend -->|2. Start| Backend
        Backend -->|3. Init| Orchestrator
        
        Orchestrator <-->|4. Code| GitHub
        Orchestrator <-->|5. Fix| Gemini
        Orchestrator <-->|6. Test| Sandbox
        
        Orchestrator -->|7. Data| Results
        Results -->|8. View| Frontend
    end
```

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite 7
- **Styling**: TailwindCSS 4
- **State Management**: Zustand
- **Animations**: Framer Motion
- **Visualization**: Recharts

### Backend
- **Language**: Python 3.12
- **API Framework**: FastAPI
- **AI Framework**: CrewAI
- **LLM**: Google Gemini 2.0 Flash
- **Containerization**: Docker (Sandbox Execution)

## 🐛 Supported Bug Types

The agent autonomously detects and fixes the following Python error types:
1.  **SYNTAX**: Missing colons, unmatched parentheses, invalid syntax.
2.  **INDENTATION**: Inconsistent code alignment, mixed tabs/spaces.
3.  **IMPORT**: Missing modules, typo in package names, circular imports.
4.  **TYPE_ERROR**: Invalid data type operations (e.g., `str` + `int`).
5.  **LINTING**: Unused imports, variable redefinitions (via AST analysis).
6.  **LOGIC**: Incorrect return values, off-by-one errors (detected via Pytest output).

## ⚙️ Installation Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker Desktop (for sandboxed execution)
- Google Gemini API Key

### Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Create a `.env` file:
    ```bash
    cp .env.example .env
    # Edit .env and add your GEMINI_API_KEY
    ```
4.  Start the server:
    ```bash
    python main.py
    ```

### Frontend Setup
1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```

## 🌍 Environment Setup

Create a `.env` file in the `backend/` directory with the following keys:

```ini
GEMINI_API_KEY=your_api_key_here
# Optional: ANTHROPIC_API_KEY=your_anthropic_key
```

## 📖 Usage Examples

1.  Open the frontend at `http://localhost:5173`.
2.  Enter the **GitHub Repository URL** you want to fix (e.g., a repo with known bugs).
3.  Enter your **Team Name** and **Leader Name**.
4.  Click **"Analyze Repository"**.
5.  The agent will:
    -   Clone the repository.
    -   Run tests to identify failures.
    -   Iteratively fix bugs (Syntax -> Import -> Logic, etc.).
    -   Push fixed code to a new branch: `TEAM_NAME_LEADER_NAME_AI_Fix`.

## ⚠️ Known Limitations

-   **Complex Logic Bugs**: Deep algorithmic flaws may require human intervention if the LLM cannot infer the correct logic from test cases alone.
-   **Execution Time**: While fast (~20-30s), complex repos with many dependencies may take longer to install/test in the sandbox.
-   **Rate Limits**: Heavy usage depends on the Gemini API quota.

## 👥 Team Members

| Role | Name |
| :--- | :--- |
| **Team Leader** | **Ashraf Ahmed** |
| Member | Purvesh Didpaye |
| Member | Prajwal Bahekar |
| Member | Riddhi Balapure |

---
*Built for RIFT 2026 Hackathon*
