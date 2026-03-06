"""
Git operations tool — wraps common git commands using subprocess.
Includes a 'smart_commit' that uses Gemini to auto-generate commit messages.
"""

import subprocess
import asyncio
from pathlib import Path

from devguardian.utils.gemini_client import ask_gemini

# Max seconds to wait for any git command before giving up
_GIT_TIMEOUT = 30

_GIT_SYSTEM = (
    "You are a Git expert. Generate a concise, professional Git commit message "
    "following the Conventional Commits specification "
    "(feat, fix, docs, style, refactor, test, chore, perf, ci, build). "
    "Format: <type>(<optional scope>): <short description>\n"
    "Optionally add a blank line and a longer body if the change is complex. "
    "Keep the first line under 72 characters. Be specific, not vague."
)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _run_git(args: list[str], cwd: str) -> tuple[str, str, int]:
    """
    Run a git command in the given directory.
    Returns (stdout, stderr, returncode).
    Times out after _GIT_TIMEOUT seconds to prevent infinite hangs.
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"⏰ Git command timed out after {_GIT_TIMEOUT}s. Is the repo on a slow network drive or waiting for credentials?", 1
    except FileNotFoundError:
        return "", "Git is not installed or not in PATH.", 1
    except Exception as exc:
        return "", str(exc), 1


def _fmt(stdout: str, stderr: str, code: int) -> str:
    """Format git output into a readable response string."""
    if code == 0:
        return f"✅ Success\n\n{stdout}" if stdout else "✅ Done."
    return f"❌ Git error (exit {code})\n\n{stderr or stdout}"


# ---------------------------------------------------------------------------
# Git tools (each exposed as an MCP tool)
# ---------------------------------------------------------------------------

def git_status(repo_path: str) -> str:
    """Show the working tree status."""
    out, err, code = _run_git(["status"], repo_path)
    return _fmt(out, err, code)


def git_add(repo_path: str, files: str = ".") -> str:
    """
    Stage files for commit.
    
    Args:
        repo_path : Absolute path to the git repo.
        files     : Files to stage. Defaults to '.' (all changes).
    """
    args = files.split() if files != "." else ["."]
    out, err, code = _run_git(["add"] + args, repo_path)
    return _fmt(out, err, code)


def git_commit(repo_path: str, message: str) -> str:
    """
    Commit staged changes with the given message.

    Args:
        repo_path : Absolute path to the git repo.
        message   : Commit message.
    """
    out, err, code = _run_git(["commit", "-m", message], repo_path)
    return _fmt(out, err, code)


def git_push(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """
    Push commits to the remote.

    Args:
        repo_path : Absolute path to the git repo.
        remote    : Remote name (default: origin).
        branch    : Branch name. If empty, uses current branch.
    """
    args = ["push", remote]
    if branch:
        args.append(branch)
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_pull(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """
    Pull latest changes from remote.

    Args:
        repo_path : Absolute path to the git repo.
        remote    : Remote name (default: origin).
        branch    : Branch name. If empty, uses current branch.
    """
    args = ["pull", remote]
    if branch:
        args.append(branch)
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_log(repo_path: str, count: int = 10) -> str:
    """
    Show recent commit history (oneline format).

    Args:
        repo_path : Absolute path to the git repo.
        count     : Number of commits to show (default: 10).
    """
    out, err, code = _run_git(
        ["log", f"--max-count={count}", "--oneline", "--decorate", "--graph"],
        repo_path,
    )
    return _fmt(out, err, code)


def git_diff(repo_path: str, staged: bool = False) -> str:
    """
    Show file differences.

    Args:
        repo_path : Absolute path to the git repo.
        staged    : If True, shows staged diff. Otherwise unstaged diff.
    """
    args = ["diff"]
    if staged:
        args.append("--staged")
    out, err, code = _run_git(args, repo_path)
    if code == 0 and not out:
        return "✅ No differences found."
    return _fmt(out, err, code)


def git_branch(repo_path: str) -> str:
    """List all local branches."""
    out, err, code = _run_git(["branch", "-a"], repo_path)
    return _fmt(out, err, code)


def git_checkout(repo_path: str, branch_name: str, create: bool = False) -> str:
    """
    Switch to a branch, or create and switch.

    Args:
        repo_path   : Absolute path to the git repo.
        branch_name : Name of the branch.
        create      : If True, creates the branch before switching (-b flag).
    """
    args = ["checkout", "-b", branch_name] if create else ["checkout", branch_name]
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_stash(repo_path: str, action: str = "push", message: str = "") -> str:
    """
    Stash or restore uncommitted changes.

    Args:
        repo_path : Absolute path to the git repo.
        action    : 'push' to stash, 'pop' to restore, 'list' to view stashes.
        message   : Optional stash message (only for push).
    """
    if action == "push":
        args = ["stash", "push", "-m", message] if message else ["stash", "push"]
    elif action == "pop":
        args = ["stash", "pop"]
    elif action == "list":
        args = ["stash", "list"]
    else:
        return f"❌ Unknown stash action: '{action}'. Use 'push', 'pop', or 'list'."
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_reset(repo_path: str, mode: str = "soft", target: str = "HEAD~1") -> str:
    """
    Reset the current HEAD to the specified state.

    Args:
        repo_path : Absolute path to the git repo.
        mode      : 'soft', 'mixed', or 'hard'.
        target    : Commit ref to reset to (default: HEAD~1).
    """
    if mode not in ("soft", "mixed", "hard"):
        return "❌ mode must be 'soft', 'mixed', or 'hard'."
    out, err, code = _run_git(["reset", f"--{mode}", target], repo_path)
    return _fmt(out, err, code)


def git_remote(repo_path: str) -> str:
    """List all configured remotes with their URLs."""
    out, err, code = _run_git(["remote", "-v"], repo_path)
    return _fmt(out, err, code)


# ---------------------------------------------------------------------------
# ⭐ KILLER FEATURE: smart_commit
# ---------------------------------------------------------------------------
def smart_commit(repo_path: str, extra_context: str = "") -> str:
    """
    ⭐ The killer feature!
    1. Runs `git diff --staged` to see what's changed.
    2. Sends the diff to Gemini to generate a Conventional Commit message.
    3. Commits automatically with that message.

    Args:
        repo_path     : Absolute path to the git repo.
        extra_context : Optional hint to help Gemini write a better message
                        (e.g. "This is part of the authentication feature").

    Returns:
        Success message with the generated commit message, or an error.
    """
    # Step 1: Check we have staged changes
    diff_out, diff_err, diff_code = _run_git(["diff", "--staged"], repo_path)
    if diff_code != 0:
        return f"❌ Could not get staged diff: {diff_err}"
    if not diff_out:
        return (
            "⚠️  No staged changes found.\n"
            "Run git_add first to stage your files, then try smart_commit again."
        )

    # Step 2: Ask Gemini for a commit message
    context_hint = f"\n\nAdditional context: {extra_context}" if extra_context else ""
    prompt = (
        f"Generate a Git commit message for the following diff:{context_hint}\n\n"
        f"```diff\n{diff_out[:6000]}\n```"  # cap diff to avoid token overflow
    )
    commit_message = ask_gemini(prompt, system_instruction=_GIT_SYSTEM)

    # Clean up in case Gemini wraps it in markdown code fences
    commit_message = commit_message.strip().strip("`").strip()
    if commit_message.startswith("git commit"):
        # Sometimes models output the full command — strip it
        commit_message = commit_message.split("-m", 1)[-1].strip().strip('"').strip("'")

    # Step 3: Commit
    out, err, code = _run_git(["commit", "-m", commit_message], repo_path)
    if code == 0:
        return (
            f"✅ Smart commit successful!\n\n"
            f"📝 Generated message:\n  {commit_message}\n\n"
            f"{out}"
        )
    return f"❌ Commit failed.\n\nMessage was:\n  {commit_message}\n\nError:\n{err}"
