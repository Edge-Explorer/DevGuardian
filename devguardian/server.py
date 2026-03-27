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

# Configure logging to stderr (visible in MCP host debug logs)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr
)
logger = logging.getLogger("devguardian")


# Run a blocking function in the thread pool (for Gemini calls)
async def _run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


# ── Tool imports ──────────────────────────────────────────────────────────────
from devguardian.tools.debugger import debug_error
from devguardian.tools.code_helper import explain_code, review_code, generate_code, improve_code
from devguardian.tools.tdd import test_and_fix
from devguardian.tools.github_review import review_pull_request
from devguardian.tools.infra import dockerize, generate_ci, generate_gitignore
from devguardian.tools.architect import generate_architecture_map, generate_technical_docs
from devguardian.tools.mass_refactor import mass_refactor
from devguardian.tools.git_ops import (
    git_status,
    git_add,
    git_commit,
    git_push,
    git_pull,
    git_log,
    git_diff,
    git_branch,
    git_checkout,
    git_stash,
    git_reset,
    git_remote,
    smart_commit,
)
from devguardian.utils.security import format_env_validation_report, pre_push_security_gate

# NOTE: LangGraph agent imports are intentionally lazy (see call_tool handlers)

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
        # ── AI Code Tools ─────────────────────────────────────────────────────
        types.Tool(
            name="debug_error",
            description="Analyze an error and get a fix (Gemini 2.0 Flash).",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {"type": "string"},
                    "stack_trace": {"type": "string"},
                    "code_snippet": {"type": "string"},
                    "language": {"type": "string"},
                    "project_path": {"type": "string"},
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
                    "code": {"type": "string"},
                    "question": {"type": "string"},
                    "language": {"type": "string"},
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
                    "code": {"type": "string"},
                    "language": {"type": "string"},
                    "focus": {"type": "string"},
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
                    "description": {"type": "string"},
                    "language": {"type": "string"},
                    "project_path": {"type": "string"},
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
                    "code": {"type": "string"},
                    "instructions": {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["code"],
            },
        ),
        # ── Security ──────────────────────────────────────────────────────────
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
        # ── Advanced Power Tools ──────────────────────────────────────────────
        types.Tool(
            name="agent_swarm",
            description=(
                "🤖 3-Agent Swarm: Coder + Tester + Reviewer pipeline. "
                "Builds a feature, audits it for bugs, and returns production-ready code."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "What to build or fix."},
                    "project_path": {"type": "string", "description": "Absolute path to project root."},
                },
                "required": ["task", "project_path"],
            },
        ),
        types.Tool(
            name="test_and_fix",
            description=(
                "🧪 TDD Auto-Pilot: generates pytest tests for a file, runs them, "
                "and iteratively fixes the source until tests pass."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "target_file": {
                        "type": "string",
                        "description": "Path to the file to test (absolute or relative to project_path).",
                    },
                    "max_rounds": {"type": "integer", "description": "Max fix iterations (default: 3)."},
                },
                "required": ["project_path", "target_file"],
            },
        ),
        types.Tool(
            name="review_pull_request",
            description=(
                "🌐 GitHub PR Reviewer: fetches a PR's diffs from GitHub and performs "
                "an AI-powered code review. Set GITHUB_TOKEN in .env for private repos."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Full repo name, e.g. 'owner/repo'."},
                    "pr_number": {"type": "integer", "description": "Pull Request number."},
                    "project_path": {"type": "string", "description": "Optional local project path for extra context."},
                },
                "required": ["repo", "pr_number"],
            },
        ),
        types.Tool(
            name="dockerize",
            description=(
                "🐳 Generates a production-grade Dockerfile and docker-compose.yml "
                "tailored to the project's detected tech stack."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                },
                "required": ["project_path"],
            },
        ),
        types.Tool(
            name="generate_ci",
            description=(
                "🚀 Generates a GitHub Actions CI/CD workflow (.github/workflows/ci.yml) "
                "tailored to the project's stack (tests, linting, Docker, etc.)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "deploy_target": {
                        "type": "string",
                        "description": "e.g. 'docker', 'railway', 'heroku' (optional).",
                    },
                },
                "required": ["project_path"],
            },
        ),
        types.Tool(
            name="generate_gitignore",
            description=(
                "🛡️ Smart .gitignore Generator: analyzes the project structure and "
                "generates a tailored .gitignore file via AI."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "include_env": {
                        "type": "boolean",
                        "description": "If true, explicitly include .env and credentials in the ignore list. (User Permission)",
                    },
                },
                "required": ["project_path"],
            },
        ),
        types.Tool(
            name="mass_refactor",
            description=(
                "🏗️ God-Mode Mass Refactoring: applies a single instruction across "
                "every Python file in the project. E.g. 'Add type hints to all functions'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "instruction": {
                        "type": "string",
                        "description": "What to change across the whole codebase.",
                    },
                },
                "required": ["project_path", "instruction"],
            },
        ),
        types.Tool(
            name="generate_architecture_map",
            description="Generates a Mermaid.js diagram of the project's internal dependencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                },
                "required": ["project_path"],
            },
        ),
        types.Tool(
            name="generate_technical_docs",
            description="Generates a high-density, professional architecture summary of the project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                },
                "required": ["project_path"],
            },
        ),
        # ── Git ───────────────────────────────────────────────────────────────
        types.Tool(
            name="git_status",
            description="Git status.",
            inputSchema={"type": "object", "properties": {"repo_path": {"type": "string"}}, "required": ["repo_path"]},
        ),
        types.Tool(
            name="git_add",
            description="Git add.",
            inputSchema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}, "files": {"type": "string"}},
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_commit",
            description="Git commit.",
            inputSchema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}, "message": {"type": "string"}},
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
                "properties": {"repo_path": {"type": "string"}, "count": {"type": "integer"}},
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_diff",
            description="Git diff.",
            inputSchema={
                "type": "object",
                "properties": {"repo_path": {"type": "string"}, "staged": {"type": "boolean"}},
                "required": ["repo_path"],
            },
        ),
        types.Tool(
            name="git_branch",
            description="List branches.",
            inputSchema={"type": "object", "properties": {"repo_path": {"type": "string"}}, "required": ["repo_path"]},
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
            inputSchema={"type": "object", "properties": {"repo_path": {"type": "string"}}, "required": ["repo_path"]},
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
        # ── Autonomous Agent ──────────────────────────────────────────────────
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
    # 🕵️ Reload environment variables on every call to support hot-updating .env files
    load_dotenv(override=True)
    logger.info(f"Tool called: {name}")

    def text(result) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=str(result))]

    try:
        # ── AI Code Tools ─────────────────────────────────────────────────────
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

        # ── Security ──────────────────────────────────────────────────────────
        elif name == "validate_env":
            return text(format_env_validation_report(arguments["env_path"]))
        elif name == "security_scan":
            _, report = pre_push_security_gate(arguments["repo_path"])
            return text(report)

        # ── Power Tools ───────────────────────────────────────────────────────
        elif name == "agent_swarm":
            from devguardian.agents.swarm import run_swarm

            return text(
                await run_swarm(
                    task=arguments["task"],
                    project_path=arguments["project_path"],
                )
            )
        elif name == "test_and_fix":
            return text(await _run_sync(test_and_fix, **arguments))
        elif name == "review_pull_request":
            return text(await _run_sync(review_pull_request, **arguments))
        elif name == "dockerize":
            return text(await _run_sync(dockerize, **arguments))
        elif name == "generate_ci":
            return text(await _run_sync(generate_ci, **arguments))
        elif name == "generate_gitignore":
            return text(await _run_sync(generate_gitignore, **arguments))
        elif name == "mass_refactor":
            return text(await _run_sync(mass_refactor, **arguments))
        elif name == "generate_architecture_map":
            return text(await _run_sync(generate_architecture_map, **arguments))
        elif name == "generate_technical_docs":
            return text(await _run_sync(generate_technical_docs, **arguments))

        # ── Git ───────────────────────────────────────────────────────────────
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

        # ── Legacy Autonomous Agent ───────────────────────────────────────────
        elif name == "autonomous_engineer":
            from devguardian.agents.engineer import create_engineer_graph
            from devguardian.utils.memory import init_db
            from langchain_core.messages import HumanMessage

            await init_db()
            graph = create_engineer_graph()
            task = arguments["task"]
            result = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=task)],
                    "project_path": arguments["project_path"],
                    "task_description": task,
                    "is_resolved": False,
                }
            )
            return text(result["messages"][-1].content)

        else:
            logger.warning(f"Unknown tool: {name}")
            return text(f"❌ Tool '{name}' not found.")

    except Exception as e:
        logger.exception(f"Error in tool '{name}'")
        return text(f"❌ DevGuardian Error in '{name}': {e}")


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
