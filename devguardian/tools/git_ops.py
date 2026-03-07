"""
Git operations tool — wraps common git commands using asyncio.create_subprocess_exec.

All functions are NATIVE ASYNC — no thread pools, no blocking, no Windows handle issues.
This is the correct way to run subprocesses inside an asyncio event loop.
"""

import asyncio
from devguardian.utils.gemini_client import ask_gemini

_GIT_TIMEOUT = 30  # seconds before giving up on a git command

_GIT_SYSTEM = (
    "You are a Git expert. Generate a concise, professional Git commit message "
    "following the Conventional Commits specification "
    "(feat, fix, docs, style, refactor, test, chore, perf, ci, build). "
    "Format: <type>(<optional scope>): <short description>\n"
    "Optionally add a blank line and a longer body if the change is complex. "
    "Keep the first line under 72 characters. Be specific, not vague."
)


# ---------------------------------------------------------------------------
# Internal async helper
# ---------------------------------------------------------------------------
async def _run_git(args: list[str], cwd: str) -> tuple[str, str, int]:
    """
    Run a git command asynchronously using asyncio.create_subprocess_exec.
    Returns (stdout, stderr, returncode).
    Times out after _GIT_TIMEOUT seconds.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=_GIT_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return "", f"Git command timed out after {_GIT_TIMEOUT}s.", 1

        stdout = stdout_b.decode("utf-8", errors="replace").strip()
        stderr = stderr_b.decode("utf-8", errors="replace").strip()
        return stdout, stderr, proc.returncode

    except FileNotFoundError:
        return "", "Git is not installed or not in PATH.", 1
    except Exception as exc:
        return "", str(exc), 1


def _fmt(stdout: str, stderr: str, code: int) -> str:
    """Format git output into a readable response string."""
    if code == 0:
        return f"Success\n\n{stdout}" if stdout else "Done."
    return f"Git error (exit {code})\n\n{stderr or stdout}"


# ---------------------------------------------------------------------------
# Git tools — all async, called directly from server.py with await
# ---------------------------------------------------------------------------

async def git_status(repo_path: str) -> str:
    """Show the working tree status."""
    out, err, code = await _run_git(["status"], repo_path)
    return _fmt(out, err, code)


async def git_add(repo_path: str, files: str = ".") -> str:
    """Stage files for commit."""
    args = files.split() if files != "." else ["."]
    out, err, code = await _run_git(["add"] + args, repo_path)
    return _fmt(out, err, code)


async def git_commit(repo_path: str, message: str) -> str:
    """Commit staged changes with the given message."""
    out, err, code = await _run_git(["commit", "-m", message], repo_path)
    return _fmt(out, err, code)


async def git_push(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """Push commits to the remote."""
    args = ["push", remote]
    if branch:
        args.append(branch)
    out, err, code = await _run_git(args, repo_path)
    return _fmt(out, err, code)


async def git_pull(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """Pull latest changes from remote."""
    args = ["pull", remote]
    if branch:
        args.append(branch)
    out, err, code = await _run_git(args, repo_path)
    return _fmt(out, err, code)


async def git_log(repo_path: str, count: int = 10) -> str:
    """Show recent commit history (oneline format)."""
    out, err, code = await _run_git(
        ["log", f"--max-count={count}", "--oneline", "--decorate", "--graph"],
        repo_path,
    )
    return _fmt(out, err, code)


async def git_diff(repo_path: str, staged: bool = False) -> str:
    """Show file differences."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    out, err, code = await _run_git(args, repo_path)
    if code == 0 and not out:
        return "No differences found."
    return _fmt(out, err, code)


async def git_branch(repo_path: str) -> str:
    """List all local branches."""
    out, err, code = await _run_git(["branch", "-a"], repo_path)
    return _fmt(out, err, code)


async def git_checkout(repo_path: str, branch_name: str, create: bool = False) -> str:
    """Switch to a branch, or create and switch."""
    args = ["checkout", "-b", branch_name] if create else ["checkout", branch_name]
    out, err, code = await _run_git(args, repo_path)
    return _fmt(out, err, code)


async def git_stash(repo_path: str, action: str = "push", message: str = "") -> str:
    """Stash or restore uncommitted changes."""
    if action == "push":
        args = ["stash", "push", "-m", message] if message else ["stash", "push"]
    elif action == "pop":
        args = ["stash", "pop"]
    elif action == "list":
        args = ["stash", "list"]
    else:
        return f"Unknown stash action: '{action}'. Use 'push', 'pop', or 'list'."
    out, err, code = await _run_git(args, repo_path)
    return _fmt(out, err, code)


async def git_reset(repo_path: str, mode: str = "soft", target: str = "HEAD~1") -> str:
    """Reset the current HEAD to the specified state."""
    if mode not in ("soft", "mixed", "hard"):
        return "mode must be 'soft', 'mixed', or 'hard'."
    out, err, code = await _run_git(["reset", f"--{mode}", target], repo_path)
    return _fmt(out, err, code)


async def git_remote(repo_path: str) -> str:
    """List all configured remotes with their URLs."""
    out, err, code = await _run_git(["remote", "-v"], repo_path)
    return _fmt(out, err, code)


# ---------------------------------------------------------------------------
# Smart commit — async version
# ---------------------------------------------------------------------------
async def smart_commit(repo_path: str, extra_context: str = "") -> str:
    """
    1. Runs `git diff --staged` to see what's changed.
    2. Sends the diff to Gemini to generate a Conventional Commit message.
    3. Commits automatically with that message.
    """
    # Step 1: Check for staged changes
    diff_out, diff_err, diff_code = await _run_git(["diff", "--staged"], repo_path)
    if diff_code != 0:
        return f"Could not get staged diff: {diff_err}"
    if not diff_out:
        return (
            "No staged changes found.\n"
            "Run git_add first to stage your files, then try smart_commit again."
        )

    # Step 2: Ask Gemini for a commit message (run in thread since ask_gemini is sync)
    context_hint = f"\n\nAdditional context: {extra_context}" if extra_context else ""
    prompt = (
        f"Generate a Git commit message for the following diff:{context_hint}\n\n"
        f"```diff\n{diff_out[:6000]}\n```"
    )
    commit_message = await asyncio.to_thread(ask_gemini, prompt, _GIT_SYSTEM)

    # Clean up in case Gemini wraps it in markdown code fences
    commit_message = commit_message.strip().strip("`").strip()
    if commit_message.startswith("git commit"):
        commit_message = commit_message.split("-m", 1)[-1].strip().strip('"').strip("'")

    # Step 3: Commit
    out, err, code = await _run_git(["commit", "-m", commit_message], repo_path)
    if code == 0:
        return (
            f"Smart commit successful!\n\n"
            f"Generated message:\n  {commit_message}\n\n"
            f"{out}"
        )
    return f"Commit failed.\n\nMessage was:\n  {commit_message}\n\nError:\n{err}"
