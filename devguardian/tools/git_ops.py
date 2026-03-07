"""
Git operations tool — wraps common git commands using subprocess.run().

IMPORTANT (Windows + MCP): asyncio.create_subprocess_exec() hangs on Windows
when called after the MCP library imports (likely a ProactorEventLoop/anyio conflict).
subprocess.run() in a synchronous function called directly from the async handler
is the proven-working approach — git commands complete in ~60ms so blocking
the event loop for that duration is completely acceptable for an MCP server.
"""

import subprocess
from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.security import pre_push_security_gate, format_env_validation_report

_GIT_TIMEOUT = 30  # seconds

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
    Run a git command synchronously. Returns (stdout, stderr, returncode).
    Times out after _GIT_TIMEOUT seconds.
    
    NOTE: Called directly from async handlers — git ops are ~60ms so blocking
    the event loop briefly is acceptable and avoids asyncio subprocess issues on Windows.
    """
    try:
        result = subprocess.run(
            ["git"] + args,  # shell=False: args go directly to OS, no shell injection risk
            cwd=cwd,
            stdin=subprocess.DEVNULL,   # CRITICAL: prevents git from inheriting the
                                        # MCP server's stdin (JSON-RPC pipe). Without
                                        # this, git blocks waiting for terminal input
                                        # that never comes, hanging the entire server.
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Git command timed out after {_GIT_TIMEOUT}s.", 1
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
# Git tools — synchronous, called directly from async server handlers
# ---------------------------------------------------------------------------

def git_status(repo_path: str) -> str:
    out, err, code = _run_git(["status"], repo_path)
    return _fmt(out, err, code)


def git_add(repo_path: str, files: str = ".") -> str:
    args = files.split() if files != "." else ["."]
    out, err, code = _run_git(["add"] + args, repo_path)
    return _fmt(out, err, code)


def git_commit(repo_path: str, message: str) -> str:
    out, err, code = _run_git(["commit", "-m", message], repo_path)
    return _fmt(out, err, code)


def git_push(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    """Push commits to the remote — runs security gate first."""
    # Security gate: block push if secrets or .gitignore issues found
    safe, security_report = pre_push_security_gate(repo_path)
    if not safe:
        return (
            f"🚨 PUSH BLOCKED BY DEVGUARDIAN SECURITY GATE\n\n"
            f"{security_report}\n\n"
            f"Fix the issues above, then try pushing again."
        )

    args = ["push", remote]
    if branch:
        args.append(branch)
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_pull(repo_path: str, remote: str = "origin", branch: str = "") -> str:
    args = ["pull", remote]
    if branch:
        args.append(branch)
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_log(repo_path: str, count: int = 10) -> str:
    out, err, code = _run_git(
        ["log", f"--max-count={count}", "--oneline", "--decorate", "--graph"],
        repo_path,
    )
    return _fmt(out, err, code)


def git_diff(repo_path: str, staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--staged")
    out, err, code = _run_git(args, repo_path)
    if code == 0 and not out:
        return "No differences found."
    return _fmt(out, err, code)


def git_branch(repo_path: str) -> str:
    out, err, code = _run_git(["branch", "-a"], repo_path)
    return _fmt(out, err, code)


def git_checkout(repo_path: str, branch_name: str, create: bool = False) -> str:
    args = ["checkout", "-b", branch_name] if create else ["checkout", branch_name]
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_stash(repo_path: str, action: str = "push", message: str = "") -> str:
    if action == "push":
        args = ["stash", "push", "-m", message] if message else ["stash", "push"]
    elif action == "pop":
        args = ["stash", "pop"]
    elif action == "list":
        args = ["stash", "list"]
    else:
        return f"Unknown stash action: '{action}'. Use 'push', 'pop', or 'list'."
    out, err, code = _run_git(args, repo_path)
    return _fmt(out, err, code)


def git_reset(repo_path: str, mode: str = "soft", target: str = "HEAD~1") -> str:
    if mode not in ("soft", "mixed", "hard"):
        return "mode must be 'soft', 'mixed', or 'hard'."
    out, err, code = _run_git(["reset", f"--{mode}", target], repo_path)
    return _fmt(out, err, code)


def git_remote(repo_path: str) -> str:
    out, err, code = _run_git(["remote", "-v"], repo_path)
    return _fmt(out, err, code)


# ---------------------------------------------------------------------------
# Smart commit
# ---------------------------------------------------------------------------
def smart_commit(repo_path: str, extra_context: str = "") -> str:
    """
    1. Runs `git diff --staged` to see what's changed.
    2. Scans staged files for leaked secrets — blocks if found.
    3. Sends the diff to Gemini to generate a Conventional Commit message.
    4. Commits automatically with that message.
    """
    # Step 1: Check for staged changes
    diff_out, diff_err, diff_code = _run_git(["diff", "--staged"], repo_path)
    if diff_code != 0:
        return f"Could not get staged diff: {diff_err}"
    if not diff_out:
        return "No staged changes found. Run git_add first, then try smart_commit again."

    # Step 2: Security scan on staged content before committing
    safe, security_report = pre_push_security_gate(repo_path)
    if not safe:
        return (
            f"🚨 COMMIT BLOCKED BY DEVGUARDIAN SECURITY GATE\n\n"
            f"{security_report}\n\n"
            f"Fix the issues above, then try committing again."
        )

    # Step 3: Ask Gemini for a commit message
    context_hint = f"\n\nAdditional context: {extra_context}" if extra_context else ""
    prompt = (
        f"Generate a Git commit message for the following diff:{context_hint}\n\n"
        f"```diff\n{diff_out[:6000]}\n```"
    )
    commit_message = ask_gemini(prompt, system_instruction=_GIT_SYSTEM)
    commit_message = commit_message.strip().strip("`").strip()
    if commit_message.startswith("git commit"):
        commit_message = commit_message.split("-m", 1)[-1].strip().strip('"').strip("'")

    # Step 4: Commit
    out, err, code = _run_git(["commit", "-m", commit_message], repo_path)
    if code == 0:
        return f"Smart commit successful!\n\nGenerated message:\n  {commit_message}\n\n{out}"
    return f"Commit failed.\n\nMessage was:\n  {commit_message}\n\nError:\n{err}"
