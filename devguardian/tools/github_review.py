"""
🌐 GitHub PR Reviewer
======================
Fetches a pull request's file diffs from the GitHub REST API and performs
an expert AI code review using Gemini + project context.

Requires GITHUB_TOKEN in .env for private repos (public repos work without it).
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path

from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.file_reader import build_project_context


_REVIEW_SYSTEM = (
    "You are an expert code reviewer. "
    "Analyze the given GitHub Pull Request diff and produce a structured review covering: "
    "🐛 Bugs, 🛡️ Security Issues, ⚡ Performance, ✨ Style, and ✅ Summary. "
    "Be specific — cite file names and line-level issues."
)


def _github_request(url: str, token: str | None = None) -> dict | list:
    """Make a GitHub API GET request and return parsed JSON."""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevGuardian-MCP/1.0",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API error {e.code}: {e.reason}") from e


def review_pull_request(
    repo: str,
    pr_number: int,
    project_path: str = "",
) -> str:
    """
    Fetch a GitHub PR's diffs and produce a Gemini-powered code review.

    Args:
        repo:         Full repo name, e.g. "Edge-Explorer/DevGuardian"
        pr_number:    Pull Request number
        project_path: Optional local project path for additional context
    """
    token = os.getenv("GITHUB_TOKEN")
    base = "https://api.github.com"

    # ── Fetch PR metadata ────────────────────────────────────────────────────
    try:
        pr_meta = _github_request(f"{base}/repos/{repo}/pulls/{pr_number}", token)
    except RuntimeError as e:
        return (
            f"❌ Could not fetch PR #{pr_number} from `{repo}`.\n"
            f"Error: {e}\n\n"
            "💡 Tip: Set `GITHUB_TOKEN` in your `.env` for private repos."
        )

    title = pr_meta.get("title", "N/A")
    author = pr_meta.get("user", {}).get("login", "unknown")
    body = pr_meta.get("body") or "No description provided."
    base_branch = pr_meta.get("base", {}).get("ref", "main")
    head_branch = pr_meta.get("head", {}).get("ref", "feature")

    # ── Fetch changed files ───────────────────────────────────────────────────
    try:
        files = _github_request(f"{base}/repos/{repo}/pulls/{pr_number}/files", token)
    except RuntimeError as e:
        return f"❌ Could not fetch PR files: {e}"

    # Build a compact diff summary (cap at ~6000 chars for Gemini context)
    diff_parts = []
    total_chars = 0
    for f in files:
        filename = f.get("filename", "unknown")
        status = f.get("status", "modified")    # added / modified / removed
        additions = f.get("additions", 0)
        deletions = f.get("deletions", 0)
        patch = f.get("patch", "")              # unified diff text

        header = f"\n### {status.upper()}: `{filename}` (+{additions} -{deletions})\n"
        diff_parts.append(header)

        if patch:
            allowed = max(0, 6000 - total_chars - len(header))
            diff_parts.append(f"```diff\n{patch[:allowed]}\n```\n")
            total_chars += len(header) + len(patch[:allowed])

        if total_chars >= 6000:
            diff_parts.append("\n*(diff truncated — too large)*\n")
            break

    diff_text = "".join(diff_parts)

    # ── Build prompt ──────────────────────────────────────────────────────────
    ctx = build_project_context(project_path) if project_path else ""
    prompt = (
        f"{ctx}\n\n"
        f"## 🔀 Pull Request #{pr_number}: {title}\n"
        f"**Author:** {author} | **{head_branch}** → **{base_branch}**\n\n"
        f"**Description:**\n{body[:500]}\n\n"
        f"## Changed Files\n{diff_text}\n\n"
        "Please provide a detailed, structured code review of this PR."
    )

    review = ask_gemini(prompt, system_instruction=_REVIEW_SYSTEM)

    return (
        f"# 🌐 DevGuardian PR Review — #{pr_number}\n"
        f"**{title}** by @{author}\n\n"
        f"{review}"
    )
