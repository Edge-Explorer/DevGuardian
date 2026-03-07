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
import sys
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from dotenv import load_dotenv

load_dotenv()

# Configure logging to stderr (MCP captures this as debug info)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("devguardian")

# _run_sync: used ONLY for blocking Gemini AI calls
async def _run_sync(func, *args, **kwargs):
    """Run a blocking function in a thread pool."""
    return await asyncio.to_thread(func, *args, **kwargs)

# Lightweight tool imports
from devguardian.tools.debugger import debug_error
from devguardian.tools.code_helper import explain_code, review_code, generate_code, improve_code
from devguardian.tools.git_ops import (
    git_status, git_add, git_commit, git_push, git_pull,
    git_log, git_diff, git_branch, git_checkout,
    git_stash, git_reset, git_remote, smart_commit,
)
from devguardian.utils.security import format_env_validation_report, pre_push_security_gate

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
app = Server("devguardian")

# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # AI Coding Assistance
        types.Tool(
            name="debug_error",
            description="Analyze an error and get a fix (Gemini 2.0 Flash).",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {"type": "string"},
                    "stack_trace":   {"type": "string"},
                    "code_snippet":  {"type": "string"},
                    "language":      {"type": "string"},
                    "project_path":  {"type": "string"},
                },
                "required": ["error_message"],
            },
        ),
        types.Tool(
            name="explain_code",
            description="Explain code structure and logic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code":         {"type": "string"},
                    "question":     {"type": "string"},
                    "language":     {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["code"],
            },
        ),
        types.Tool(
            name="review_code",
            description="AI code review (security, performance, style).",
            inputSchema={
                "type": "object",
                "properties": {
                    "code":         {"type": "string"},
                    "language":     {"type": "string"},
                    "focus":        {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["code"],
            },
        ),
        types.Tool(
            name="generate_code",
            description="Generate code from description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description":   {"type": "string"},
                    "language":      {"type": "string"},
                    "project_path":  {"type": "string"},
                },
                "required": ["description"],
            },
        ),
        types.Tool(
            name="improve_code",
            description="Refactor and improve existing code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code":         {"type": "string"},
                    "instructions": {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["code"],
            },
        ),

        # Security
        types.Tool(
            name="validate_env",
            description="Validate .env format (never leaks values).",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_path": {"type": "string"},
                },
                "required": ["env_path"],
            },
        ),
        types.Tool(
            name="security_scan",
            description="Scan repo for credential leaks and gitignore issues.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),

        # Git Operations
        types.Tool(
            name="git_status",
            description="Git status.",
            inputSchema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}},
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_add",
            description="Git add.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "files": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_commit",
            description="Git commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["repo_path", "message"],
            },
        ),
        types.Tool(
            name="git_push",
            description="Git push (security checked).",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "remote": {"type": "string"},
                    "branch": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_pull",
            description="Git pull.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "remote": {"type": "string"},
                    "branch": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_log",
            description="Git history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "count": {"type": "integer"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_diff",
            description="Git diff.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "staged": {"type": "boolean"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_branch",
            description="List branches.",
            inputSchema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}},
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_checkout",
            description="Git checkout.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "branch_name": {"type": "string"},
                    "create": {"type": "boolean"},
                },
                "required": ["repo_path", "branch_name"],
            },
        ),
        types.Tool(
            name="git_stash",
            description="Git stash (push, pop, list).",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "action": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_reset",
            description="Git reset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "mode": {"type": "string"},
                    "target": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_remote",
            description="Git remotes.",
            inputSchema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}},
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="smart_commit",
            description="AI-generated commit message and commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "extra_context": {"type": "string"},
                },
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="autonomous_engineer",
            description="Autonomous coding agent (LangGraph).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["task", "project_path"],
            },
        ),
    ]

# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    logger.info(f"Executing tool: {name}")

    def text(result: str) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=str(result))]

    try:
        # ── AI Tools ──────────────────────────────────────────────────────────
        if name == "debug_error":
            return text(await _run_sync(debug_error, **arguments))
        elif name == "explain_code":
            return text(await _run_sync(explain_code, **arguments))
        elif name == "review_code":
            return text(await _run_sync(review_code, **arguments))
        elif name == "generate_code":
            return text(await _run_sync(generate_code, **arguments))
        elif name == "improve_code":
            return text(await _run_sync(improve_code, **arguments))
        elif name == "smart_commit":
            return text(await _run_sync(smart_commit, **arguments))

        # ── Security & Git Tools (Sync) ───────────────────────────────────────
        elif name == "validate_env":
            return text(format_env_validation_report(arguments["env_path"]))
        elif name == "security_scan":
            _, report = pre_push_security_gate(arguments["repo_path"])
            return text(report)
        elif name == "git_status":
            return text(git_status(arguments["repo_path"]))
        elif name == "git_add":
            return text(git_add(**arguments))
        elif name == "git_commit":
            return text(git_commit(**arguments))
        elif name == "git_push":
            return text(git_push(**arguments))
        elif name == "git_pull":
            return text(git_pull(**arguments))
        elif name == "git_log":
            return text(git_log(**arguments))
        elif name == "git_diff":
            return text(git_diff(**arguments))
        elif name == "git_branch":
            return text(git_branch(arguments["repo_path"]))
        elif name == "git_checkout":
            return text(git_checkout(**arguments))
        elif name == "git_stash":
            return text(git_stash(**arguments))
        elif name == "git_reset":
            return text(git_reset(**arguments))
        elif name == "git_remote":
            return text(git_remote(arguments["repo_path"]))

        # ── Heavy Tools (Agent) ───────────────────────────────────────────────
        elif name == "autonomous_engineer":
            from devguardian.agents.engineer import create_engineer_graph
            from devguardian.utils.memory import init_db
            from langchain_core.messages import HumanMessage

            await init_db()
            graph = create_engineer_graph()
            task = arguments["task"]
            initial_state = {
                "messages": [HumanMessage(content=task)],
                "project_path": arguments["project_path"],
                "task_description": task,
                "is_resolved": False
            }
            result = await graph.ainvoke(initial_state)
            return text(result["messages"][-1].content)

        else:
            logger.error(f"Unknown tool: {name}")
            return text(f"❌ Error: Tool '{name}' not found.")

    except Exception as e:
        logger.exception(f"Fatal error in tool '{name}'")
        return text(f"❌ DevGuardian Error: {str(e)}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    asyncio.run(_run())

async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    main()
