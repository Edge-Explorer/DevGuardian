"""
DevGuardian MCP Server — Main Entry Point
==========================================
Exposes all DevGuardian tools over the Model Context Protocol so that
any MCP-compatible host (Antigravity, Claude Desktop, etc.) can call them.

NOTE: UTF-8 encoding is handled via PYTHONIOENCODING=utf-8 in mcp_config.json.
Do NOT reconfigure sys.stdout here — the MCP stdio_server captures it at startup
and any reconfigure after that will corrupt the JSON-RPC pipe.
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from dotenv import load_dotenv

load_dotenv()


# _run_sync: used ONLY for blocking Gemini AI calls (subprocess git ops are now native async)
async def _run_sync(func, *args, **kwargs):
    """
    Run a blocking (sync) function in a thread pool without blocking the event loop.
    Uses asyncio.to_thread() — the correct Python 3.9+ API.
    Only needed for synchronous Gemini API calls in code_helper/debugger.
    """
    return await asyncio.to_thread(func, *args, **kwargs)

# Lightweight tool imports (fast to load)
from devguardian.tools.debugger import debug_error
from devguardian.tools.code_helper import explain_code, review_code, generate_code, improve_code
from devguardian.tools.git_ops import (
    git_status, git_add, git_commit, git_push, git_pull,
    git_log, git_diff, git_branch, git_checkout,
    git_stash, git_reset, git_remote, smart_commit,
)
# NOTE: LangGraph / LangChain imports are intentionally lazy (see autonomous_engineer handler)
# This keeps the server startup instant and avoids MCP initialize timeout.

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
app = Server("devguardian")


# ---------------------------------------------------------------------------
# Tool listing — what tools does this server expose?
# ---------------------------------------------------------------------------
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── Debugging ─────────────────────────────────────────────────────
        types.Tool(
            name="debug_error",
            description=(
                "Analyze an error message, stack trace, or broken code using Gemini 2.0 Flash. "
                "Returns root cause, explanation, and corrected code. "
                "Provide project_path for full project-aware debugging."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {"type": "string", "description": "The error text (required)."},
                    "stack_trace":   {"type": "string", "description": "Full stack trace (optional)."},
                    "code_snippet":  {"type": "string", "description": "Code that caused the error (optional)."},
                    "language":      {"type": "string", "description": "Programming language, e.g. Python (optional)."},
                    "project_path":  {"type": "string", "description": "Absolute path to project root for full codebase context (optional)."},
                },
                "required": ["error_message"],
            },
        ),

        # ── Code Helper ───────────────────────────────────────────────────
        types.Tool(
            name="explain_code",
            description=(
                "Explain what a piece of code does in plain English. "
                "Provide project_path to get a project-aware explanation that references "
                "the actual modules, patterns, and architecture of your codebase."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code":         {"type": "string", "description": "The code to explain (required)."},
                    "question":     {"type": "string", "description": "Specific question about the code (optional)."},
                    "language":     {"type": "string", "description": "Programming language (optional)."},
                    "project_path": {"type": "string", "description": "Absolute path to project root for full codebase context (optional)."},
                },
                "required": ["code"],
            },
        ),
        types.Tool(
            name="review_code",
            description=(
                "Perform a code review: find bugs, security issues, performance problems, and style issues. "
                "Provide project_path for a project-aware review that also checks consistency "
                "with the rest of your codebase (naming, patterns, libraries)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code":         {"type": "string", "description": "The code to review (required)."},
                    "language":     {"type": "string", "description": "Programming language (optional)."},
                    "focus":        {"type": "string", "description": "Focus area: security, performance, readability (optional)."},
                    "project_path": {"type": "string", "description": "Absolute path to project root for full codebase context (optional)."},
                },
                "required": ["code"],
            },
        ),
        types.Tool(
            name="generate_code",
            description=(
                "Generate clean, well-documented code from a natural language description. "
                "Provide project_path to generate code that perfectly fits your existing "
                "architecture, libraries, and coding patterns."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description":   {"type": "string", "description": "What the code should do (required)."},
                    "language":      {"type": "string", "description": "Target language (default: Python)."},
                    "project_path":  {"type": "string", "description": "Absolute path to project root for full codebase context (optional)."},
                    "context_path":  {"type": "string", "description": "Alias for project_path (backwards compatible)."},
                },
                "required": ["description"],
            },
        ),
        types.Tool(
            name="improve_code",
            description=(
                "Refactor or improve existing code and explain what was changed. "
                "Provide project_path to ensure improvements stay consistent with "
                "the rest of your codebase."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code":         {"type": "string", "description": "The code to improve (required)."},
                    "language":     {"type": "string", "description": "Programming language (optional)."},
                    "instructions": {"type": "string", "description": "Specific improvement goals (optional)."},
                    "project_path": {"type": "string", "description": "Absolute path to project root for full codebase context (optional)."},
                },
                "required": ["code"],
            },
        ),

        # ── Git Operations ────────────────────────────────────────────────
        types.Tool(
            name="git_status",
            description="Show the git working tree status for a repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_add",
            description="Stage files for commit (default: all changes).",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "files":     {"type": "string", "description": "Files to stage, space-separated. Default: '.' (all)."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_commit",
            description="Commit staged changes with a custom message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "message":   {"type": "string", "description": "Commit message."},
                },
                "required": ["repo_path", "message"],
            },
        ),
        types.Tool(
            name="git_push",
            description="Push commits to the remote repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "remote":    {"type": "string", "description": "Remote name (default: origin)."},
                    "branch":    {"type": "string", "description": "Branch name (default: current branch)."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_pull",
            description="Pull latest changes from the remote repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "remote":    {"type": "string", "description": "Remote name (default: origin)."},
                    "branch":    {"type": "string", "description": "Branch name (default: current branch)."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_log",
            description="Show recent git commit history in a readable format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "count":     {"type": "integer", "description": "Number of commits to show (default: 10)."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_diff",
            description="Show file differences — staged or unstaged.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "staged":    {"type": "boolean", "description": "If true, show staged diff. Otherwise unstaged."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_branch",
            description="List all local and remote branches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_checkout",
            description="Switch to a branch, or create a new branch and switch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path":   {"type": "string",  "description": "Absolute path to the git repo."},
                    "branch_name": {"type": "string",  "description": "Name of the branch."},
                    "create":      {"type": "boolean", "description": "If true, create the branch before switching."},
                },
                "required": ["repo_path", "branch_name"],
            },
        ),
        types.Tool(
            name="git_stash",
            description="Stash uncommitted changes or restore them. Actions: push, pop, list.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "action":    {"type": "string", "description": "push | pop | list (default: push)."},
                    "message":   {"type": "string", "description": "Stash message (optional, for push only)."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_reset",
            description="Reset HEAD to a previous commit. Modes: soft, mixed, hard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                    "mode":      {"type": "string", "description": "soft | mixed | hard (default: soft)."},
                    "target":    {"type": "string", "description": "Commit ref (default: HEAD~1)."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_remote",
            description="List all configured remotes and their URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the git repo."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="smart_commit",
            description=(
                "⭐ KILLER FEATURE: Automatically reads staged changes (git diff --staged), "
                "uses Gemini AI to generate a Conventional Commit message, and commits. "
                "Stage your files with git_add first!"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path":      {"type": "string", "description": "Absolute path to the git repo (required)."},
                    "extra_context":  {"type": "string", "description": "Optional hint to help AI write a better message."},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="autonomous_engineer",
            description=(
                "🚀 STATEFUL AGENT: A LangGraph-powered autonomous coding agent. "
                "It can plan, use tools in loops, and verify its own work. "
                "Use this for complex debugging or refactoring tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task":         {"type": "string", "description": "The coding task or bug description (required)."},
                    "project_path": {"type": "string", "description": "Absolute path to the project (required)."},
                    "thread_id":    {"type": "string", "description": "Conversation ID for state persistence (optional)."},
                },
                "required": ["task", "project_path"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool dispatcher — routes incoming calls to the right function
# ---------------------------------------------------------------------------
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    def text(result: str) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=result)]

    # ── Debugging ─────────────────────────────────────────────────────────────
    if name == "debug_error":
        return text(await _run_sync(
            debug_error,
            error_message=arguments["error_message"],
            stack_trace=arguments.get("stack_trace", ""),
            code_snippet=arguments.get("code_snippet", ""),
            language=arguments.get("language", ""),
            project_path=arguments.get("project_path", ""),
        ))

    # ── Code Helper ───────────────────────────────────────────────────────────
    elif name == "explain_code":
        return text(await _run_sync(
            explain_code,
            code=arguments["code"],
            question=arguments.get("question", ""),
            language=arguments.get("language", ""),
            project_path=arguments.get("project_path", ""),
        ))
    elif name == "review_code":
        return text(await _run_sync(
            review_code,
            code=arguments["code"],
            language=arguments.get("language", ""),
            focus=arguments.get("focus", ""),
            project_path=arguments.get("project_path", ""),
        ))
    elif name == "generate_code":
        return text(await _run_sync(
            generate_code,
            description=arguments["description"],
            language=arguments.get("language", "Python"),
            context_path=arguments.get("context_path", ""),
            project_path=arguments.get("project_path", ""),
        ))
    elif name == "improve_code":
        return text(await _run_sync(
            improve_code,
            code=arguments["code"],
            language=arguments.get("language", ""),
            instructions=arguments.get("instructions", ""),
            project_path=arguments.get("project_path", ""),
        ))

    # ── Git Operations ───────────────────────────────────────────────────
    # subprocess.run() is sync but ~60ms — acceptable to call directly here.
    # asyncio.create_subprocess_exec() hangs on Windows after MCP imports.
    elif name == "git_status":
        return text(git_status(arguments["repo_path"]))
    elif name == "git_add":
        return text(git_add(arguments["repo_path"], arguments.get("files", ".")))
    elif name == "git_commit":
        return text(git_commit(arguments["repo_path"], arguments["message"]))
    elif name == "git_push":
        return text(git_push(
            arguments["repo_path"],
            arguments.get("remote", "origin"),
            arguments.get("branch", ""),
        ))
    elif name == "git_pull":
        return text(git_pull(
            arguments["repo_path"],
            arguments.get("remote", "origin"),
            arguments.get("branch", ""),
        ))
    elif name == "git_log":
        return text(git_log(arguments["repo_path"], arguments.get("count", 10)))
    elif name == "git_diff":
        return text(git_diff(arguments["repo_path"], arguments.get("staged", False)))
    elif name == "git_branch":
        return text(git_branch(arguments["repo_path"]))
    elif name == "git_checkout":
        return text(git_checkout(
            arguments["repo_path"],
            arguments["branch_name"],
            arguments.get("create", False),
        ))
    elif name == "git_stash":
        return text(git_stash(
            arguments["repo_path"],
            arguments.get("action", "push"),
            arguments.get("message", ""),
        ))
    elif name == "git_reset":
        return text(git_reset(
            arguments["repo_path"],
            arguments.get("mode", "soft"),
            arguments.get("target", "HEAD~1"),
        ))
    elif name == "git_remote":
        return text(git_remote(arguments["repo_path"]))
    elif name == "smart_commit":
        return text(await _run_sync(
            smart_commit,
            arguments["repo_path"],
            arguments.get("extra_context", ""),
        ))
    elif name == "autonomous_engineer":
        # Lazy imports — only loaded when this tool is actually called
        from devguardian.agents.engineer import create_engineer_graph
        from devguardian.utils.memory import init_db
        from langchain_core.messages import HumanMessage

        # Ensure DB is ready before running the agent
        await init_db()

        # Initialize graph
        graph = create_engineer_graph()

        # Prepare state
        task = arguments["task"]
        path = arguments["project_path"]

        initial_state = {
            "messages": [HumanMessage(content=task)],
            "project_path": path,
            "task_description": task,
            "is_resolved": False
        }

        result = await graph.ainvoke(initial_state)
        final_msg = result["messages"][-1].content
        return text(f"DevGuardian Autonomous Engineer Report:\n\n{final_msg}")

    else:
        return text(f"❌ Unknown tool: '{name}'")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """Run the DevGuardian MCP server over stdio."""
    asyncio.run(_run())


async def _run():
    # Start the server immediately — no heavy init at startup
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    main()
