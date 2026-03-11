# 🛡️ DevGuardian MCP Server: v2 — The Autonomous Engineering Edition

> An AI-powered, **Project-Aware** coding assistant MCP server built with **Gemini 2.0 Flash** and **UV**.  
> Plug it into **Antigravity** or **Claude Desktop** and get a full AI engineering team: debugging, reviewing, testing, deploying, and securing your code — all autonomously.

---

## 🌟 What makes DevGuardian a "Monster"?

DevGuardian v2 is no longer a single script. It is a **multi-agent autonomous engineering ecosystem**:

1. **🧠 Project DNA Awareness** — Before writing a single line of code, DevGuardian reads your `README`, `pyproject.toml`, full file tree, and import graph. It generates code that *fits your architecture*.
2. **🤖 Agent Swarm** — A 3-agent pipeline (Coder → Tester → Reviewer) that builds features autonomously, finds bugs, and returns production-ready code.
3. **🧪 TDD Auto-Pilot** — Generates pytest tests, runs them, reads failures, fixes the source code, and loops until green.
4. **🌐 GitHub PR Reviewer** — Connects to live GitHub PRs, reads the diffs, and posts a structured expert review.
5. **🐳 DevOps Generator** — Produces a production-grade `Dockerfile`, `docker-compose.yml`, and GitHub Actions `ci.yml` by reading your project stack.
6. **🏗️ God-Mode Mass Refactoring** — Applies a single instruction across **every Python file** in the project simultaneously.
7. **🛡️ Pre-Push Security Gate** — Actively blocks accidental pushes of API keys, tokens, and passwords.

---

## ✨ Complete Tool Reference (27 Tools)

### 🤖 Autonomous Agents
| Tool | Description |
|---|---|
| 🤖 `agent_swarm` | **3-Agent Pipeline**: Coder → Tester → Reviewer. Builds features, audits for bugs, returns production-ready code. |
| 🚀 `autonomous_engineer` | **Stateful LangGraph Agent**: Plans, executes tools in loops, verifies work, and self-corrects. |

### 🧠 AI Code Intelligence
| Tool | Description |
|---|---|
| `debug_error` | Analyze errors & stack traces; get root cause + fix with project context |
| `explain_code` | Understand what any code does in plain English |
| `review_code` | Full project-aware codebase review: bugs, security, performance, style |
| `generate_code` | Generate clean code tailored to your project's architecture |
| `improve_code` | Refactor and improve existing code consistently |

### 🔬 Quality & Testing
| Tool | Description |
|---|---|
| 🧪 `test_and_fix` | **TDD Auto-Pilot**: generates pytest tests, runs them, fixes source until tests pass |
| 🌐 `review_pull_request` | **GitHub PR Reviewer**: fetches PR diffs from GitHub & performs AI code review |

### 🐳 DevOps & Infrastructure
| Tool | Description |
|---|---|
| 🐳 `dockerize` | Auto-generates `Dockerfile` + `docker-compose.yml` for your project |
| 🚀 `generate_ci` | Auto-generates `.github/workflows/ci.yml` (linting, testing, Docker) |

### 🏗️ Mass Operations
| Tool | Description |
|---|---|
| 🏗️ `mass_refactor` | **God-Mode**: applies one instruction across ALL Python files simultaneously |

### 🛡️ Security
| Tool | Description |
|---|---|
| 🛂 `validate_env` | Validates `.env` file format safely — never exposes secret values |
| 🔍 `security_scan` | Scans repo for 20+ credential types + missing `.gitignore` rules |

### ⚡ Version Control (Git Suite)
| Tool | Description |
|---|---|
| ⭐ `smart_commit` | **AI reads your diff → writes commit message → scans for leaks → commits!** |
| `git_status` | Show working tree status |
| `git_add` | Stage files for commit |
| `git_commit` | Commit with a custom message |
| `git_push` | Push to remote **(Protected by Security Gate)** |
| `git_pull` | Pull from remote |
| `git_log` | View commit history |
| `git_diff` | Show staged or unstaged diffs |
| `git_branch` | List all branches |
| `git_checkout` | Switch or create branches |
| `git_stash` | Stash / unstash changes |
| `git_reset` | Reset HEAD (soft, mixed, hard) |
| `git_remote` | List configured remotes |

---

## 🚀 Setup

### 1. Prerequisites
- [UV](https://docs.astral.sh/uv/getting-started/installation/) installed
- Python 3.10+
- Git installed
- A [Gemini API Key](https://aistudio.google.com/app/apikey) (free)

### 2. Create virtual environment & install dependencies
```bash
cd DevGuardian
uv venv
uv pip install -e .
```

### 3. Configure your API key
```bash
copy .env.example .env
# Open .env and paste your Gemini API key
# Optionally add GITHUB_TOKEN for private repo PR reviews
```

### 4. Test the server runs
```bash
uv run devguardian
```
You should see no errors — the server waits for MCP connections on stdio.

---

## 🔌 MCP Configuration

### Antigravity (VS Code)
Add to your `.gemini/settings.json`:
```json
{
  "mcpServers": {
    "devguardian": {
      "command": "uv",
      "args": ["--directory", "C:\\Users\\ASUS\\OneDrive\\Desktop\\DevGuardian", "run", "devguardian"],
      "env": {
        "GEMINI_API_KEY": "your_key_here",
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

### Claude Desktop
Add to `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "devguardian": {
      "command": "uv",
      "args": ["--directory", "C:\\Users\\ASUS\\OneDrive\\Desktop\\DevGuardian", "run", "devguardian"],
      "env": {
        "GEMINI_API_KEY": "your_key_here"
      }
    }
  }
}
```

---

## 💡 Usage Examples

### 🤖 Agent Swarm — Build a feature with 3 AI agents
> "DevGuardian, use the agent swarm to create a rate-limiting utility for our API."  
→ Coder writes a `RateLimiter` class, Tester finds 5 edge cases, Reviewer incorporates all fixes and returns the final production-ready file.

### 🧪 TDD Auto-Pilot — Test-driven bug fixing
> "Run test_and_fix on `devguardian/tools/debugger.py`"  
→ DevGuardian writes pytest tests, runs them, reads the failures, patches the source, and loops until all tests go green.

### 🌐 GitHub PR Review — Review any live PR
> "Review PR #42 in myorg/myrepo"  
→ DevGuardian fetches the diff from GitHub and gives you a structured review: Bugs, Security, Performance, Style, and a final verdict.

### 🐳 Dockerize a project in seconds
> "Dockerize this project."  
→ DevGuardian reads your stack from `pyproject.toml`, generates a multi-stage `Dockerfile` and `docker-compose.yml`, and writes them to your project root.

### 🏗️ Mass Refactoring
> "Add type hints to all function signatures in the project."  
→ DevGuardian scans every `.py` file, rewrites functions that need type hints, and reports all 14 files it modified.

### 🛡️ Push Code Safely
> "Push my changes to main."  
→ DevGuardian scans all staged files. If it finds `api_key = "AIzaSy..."` hardcoded anywhere, it **BLOCKS the push** and tells you exactly which file and line contains the secret.

---

## 📁 Project Structure
```
DevGuardian/
├── .env.example              ← Copy to .env, add your API key
├── .gitignore                ← Comprehensive security-focused rules
├── pyproject.toml            ← UV project config (dependencies)
├── Dockerfile                ← 🐳 Auto-generated production container
├── docker-compose.yml        ← 🐳 Auto-generated service orchestration
├── README.md
├── tests/
│   └── test_debugger.py      ← 🧪 TDD Auto-Pilot generated tests
├── .github/
│   └── workflows/
│       └── ci.yml            ← 🚀 Auto-generated GitHub Actions CI/CD
└── devguardian/
    ├── server.py             ← Robust MCP server (27 tools, logging, error handling)
    ├── agents/
    │   ├── engineer.py       ← Single stateful LangGraph agent
    │   └── swarm.py          ← 🤖 3-Agent Swarm (Coder + Tester + Reviewer)
    ├── tools/
    │   ├── debugger.py       ← debug_error
    │   ├── code_helper.py    ← explain, review, generate, improve
    │   ├── git_ops.py        ← Full git suite + ⭐ smart_commit
    │   ├── tdd.py            ← 🧪 TDD Auto-Pilot
    │   ├── github_review.py  ← 🌐 GitHub PR Reviewer
    │   ├── infra.py          ← 🐳 Dockerfile + CI/CD generator
    │   └── mass_refactor.py  ← 🏗️ God-Mode mass refactoring
    └── utils/
        ├── gemini_client.py  ← Gemini 2.0 Flash wrapper (lazy init)
        ├── file_reader.py    ← 🧠 Project DNA Context Builder
        ├── security.py       ← 🛡️ Pre-push secret gate & .env validator
        └── memory.py         ← Threading & Agent state management
```

---

## 🔐 Enterprise-Grade Security

- **Anti-Leak Shield**: `security.py` detects 20+ credential types (AWS, GitHub, OpenAI, Google, Stripe, Slack…) before any `git push` or `smart_commit`.
- **Smart Detection**: Only flags **hardcoded quoted values** — never false-positives on `os.getenv()` calls.
- **`.env` Safety**: `validate_env` reviews your `.env` file format — shows keys but **never exposes values**.
- **Local Execution**: Your code never leaves your machine except for Gemini API calls.

---

## 🐳 Docker

```bash
# Build and run DevGuardian in a container
docker compose up --build
```

---

*Built with ❤️ by **Karan** using Gemini 2.0 Flash + LangGraph + MCP SDK + UV*
