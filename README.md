# 🛡️ DevGuardian MCP Server: The "Mini-Antigravity" Edition

> An AI-powered, **Project-Aware** coding assistant MCP server built with **Gemini 2.0 Flash** and **UV**.
> Plug it into **Antigravity** or **Claude Desktop** for AI-assisted coding, debugging, and robust Git operations — now with a built-in **Pre-Push Security Gate**.

---

## 🌟 What makes it a "Monster"?

DevGuardian isn't just a generic script runner anymore. It now has a 360-degree view of your codebase and a built-in security shield. 

1. **🧠 Project DNA Awareness:** When you ask it to review, explain, or improve code, DevGuardian no longer just looks at the file. It inhales your `README.md`, dependencies (`pyproject.toml`), full file tree, and import relationships before generating an answer. It writes code that *fits your architecture*.
2. **🛡️ Built-in Security Gate:** DevGuardian actively watches your Git operations. If you attempt to `git push` or `smart_commit` an API key, password, or GitHub token, DevGuardian will **BLOCK the push** and alert you instantly.
3. **Robust Architecture:** All 20+ tools are backed by standard async patterns, graceful error handling, and `stderr` logging so the host MCP client won't crash when edge cases hit. 

---

## ✨ Features (20+ Tools)

| Tool | Category | Description |
|---|---|---|
| `debug_error` | Code | Analyze errors & stack traces; get contextual root cause + fix |
| `explain_code` | Code | Understand what any code does with full project context |
| `review_code` | Code | Full codebase review: bugs, security, performance, style |
| `generate_code` | Code | Generate clean code tailored to your project's architecture |
| `improve_code` | Code | Refactor and improve existing code consistently |
| 🛂 `validate_env` | Security | Validates `.env` files safely (never exposes secrets in UI) |
| 🛡️ `security_scan` | Security | Scans repo for 20+ types of credential leaks and missing `.gitignore` rules |
| `git_status` | Version Control | Show working tree status |
| `git_add` | Version Control | Stage files for commit |
| `git_commit` | Version Control | Commit with a custom message |
| `git_push` | Version Control | **Push to remote (Protected by Security Gate)** |
| `git_pull` | Version Control | Pull from remote |
| `git_log` | Version Control | View commit history |
| `git_diff` | Version Control | Show staged or unstaged diffs |
| `git_branch` | Version Control | List all branches |
| `git_checkout` | Version Control | Switch or create branches |
| `git_stash` | Version Control | Stash / unstash changes |
| `git_reset` | Version Control | Reset HEAD (soft, mixed, hard) |
| `git_remote` | Version Control | List configured remotes |
| ⭐ `smart_commit`| Automation | **Reads diff → generates commit message → checks for leaks → commits!** |
| 🚀 `autonomous_engineer` | Agent | **LangGraph agent that plans, uses tools in loops, and verifies work!** |

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
```

### 4. Test the server runs
```bash
uv run devguardian
```
You should see no errors — the server waits for MCP connections on stdio.

---

## 🔌 MCP Configuration

### Antigravity (VS Code)
Add to your `.gemini/settings.json` or MCP config file:
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

### Debug an error (Project-Aware)
> "DevGuardian, debug the AttributeError I'm seeing in my flask app."
→ DevGuardian reads your file tree, finds the offending class, and fixes the bug matching your specific project style.

### Push Code (Safely)
> "Push changes to main."
→ DevGuardian scans your staged files. If you accidentally left `api_key = "AIzaSy..."` inside a file, DevGuardian BLOCKS the push and warns you to remove it.

### Smart commit
> "Commit my changes."
→ DevGuardian runs `git add .`, scans for leaks, Gemini writes the commit message based on the diff, and the commit is saved.

### Autonomous Engineering
> "Implement a new database endpoint to fetch users."
→ DevGuardian starts a LangGraph loop, analyzes the existing database files, writes the new code, and ensures it doesn't break existing tests.

---

## 📁 Project Structure
```
DevGuardian/
├── .env.example          ← Copy to .env, add your API key
├── .gitignore
├── pyproject.toml        ← UV project config (dependencies)
├── README.md
└── devguardian/
    ├── server.py         ← Robust MCP server entry point (20+ tools, global try/except, live logging)
    ├── agents/
    │   └── engineer.py       ← Stateful Langgraph agent
    ├── tools/
    │   ├── debugger.py       ← debug_error 
    │   ├── code_helper.py    ← explain, review, generate, improve
    │   └── git_ops.py        ← Git commands + ⭐smart_commit 
    └── utils/
        ├── gemini_client.py  ← Gemini 2.0 Flash wrapper
        ├── file_reader.py    ← 🧠 Project DNA Context Builder 
        ├── security.py       ← 🛡️ Pre-push secret gate & .env validator
        └── memory.py         ← Threading & Agent state management
```

---

## 🔐 Enterprise-Grade Security
- **Anti-Leak Shield:** `security.py` checks for over 20+ types of keys (AWS, GitHub, OpenAI, Google) before any `git push` or `smart_commit`.
- **.env formatting:** `.env` validation ensures no placeholders or empty values are pushed to production by mistake.
- **Local execution:** The server runs locally; your code never leaves your machine except for API calls to Gemini.

---

*Built with ❤️ using Gemini 2.0 Flash + MCP SDK + UV*
