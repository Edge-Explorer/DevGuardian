# 🛡️ DevGuardian MCP Server

> An AI-powered coding assistant MCP server built with **Gemini 2.0 Flash** and **UV**.
> Plug it into **Antigravity** or **Claude Desktop** for AI-assisted coding, debugging, and Git — all in one place.

---

## ✨ Features

| Tool | Description |
|---|---|
| `debug_error` | Analyze errors & stack traces, get root cause + fix |
| `explain_code` | Understand what any code does in plain English |
| `review_code` | Full code review: bugs, security, performance, style |
| `generate_code` | Generate clean code from a natural language description |
| `improve_code` | Refactor and improve existing code |
| `git_status` | Show working tree status |
| `git_add` | Stage files for commit |
| `git_commit` | Commit with a custom message |
| `git_push` | Push to remote |
| `git_pull` | Pull from remote |
| `git_log` | View commit history |
| `git_diff` | Show staged or unstaged diffs |
| `git_branch` | List all branches |
| `git_checkout` | Switch or create branches |
| `git_stash` | Stash / unstash changes |
| `git_reset` | Reset HEAD (soft, mixed, hard) |
| `git_remote` | List configured remotes |
| ⭐ `smart_commit` | **AI reads your diff → generates commit message → commits automatically!** |

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

### Debug an error
> "I have this error: `KeyError: 'user_id'` in my Flask app. Here's the stack trace..."
→ DevGuardian will identify the root cause and show you the exact fix.

### Smart commit
> "Stage all my changes and commit them"
→ DevGuardian runs `git add .`, reads the diff, Gemini writes the commit message, done!

### Generate code
> "Generate a Python function that validates an email address with regex"
→ Clean, typed, documented code in seconds.

---

## 📁 Project Structure
```
DevGuardian/
├── .env.example          ← Copy to .env, add your API key
├── .gitignore
├── pyproject.toml        ← UV project config
├── README.md
└── devguardian/
    ├── server.py         ← MCP server entry point (18 tools)
    ├── tools/
    │   ├── debugger.py       debug_error
    │   ├── code_helper.py    explain, review, generate, improve
    │   └── git_ops.py        13 git tools + ⭐smart_commit
    └── utils/
        ├── gemini_client.py  Gemini 2.0 Flash wrapper
        └── file_reader.py    project context builder
```

---

## 🔐 Security
- **Never commit your `.env` file** — it's in `.gitignore`
- The server runs locally; your code never leaves your machine except for API calls to Gemini
- Git operations run in the directory you specify — they can't affect other folders

---

*Built with ❤️ using Gemini 2.0 Flash + MCP SDK + UV*
