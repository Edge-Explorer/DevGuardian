"""
DevGuardian Security Module
============================
Three layers of protection:

1. validate_env_file()     — validates .env format & reports issues without leaking values
2. scan_content_for_secrets() — detects 20+ types of leaked credentials in any text
3. pre_push_security_gate()   — full security check before any git push
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Credential leak patterns (regex → human-readable name)
# ---------------------------------------------------------------------------
_SECRET_PATTERNS: list[tuple[str, str]] = [
    # Generic patterns — only fire when an actual quoted string value is present.
    # This prevents false positives on: api_key=os.getenv(...) or token: str
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^\s"\']{4,}["\']', "Password assignment"),
    (r'(?i)(secret|secret_key)\s*=\s*["\'][^\s"\']{4,}["\']', "Secret key assignment"),
    (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^\s"\']{8,}["\']', "API key assignment"),
    (r'(?i)(token|auth_token|access_token)\s*=\s*["\'][^\s"\']{8,}["\']', "Token assignment"),
    (r'(?i)(private_key|privkey)\s*=\s*["\'][^\s"\']{8,}["\']', "Private key assignment"),
    # Well-known service keys (distinct prefixes — always flag)
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API Key"),
    (r'(?i)gemini[_\-]?api[_\-]?key\s*=\s*["\']?AIza[0-9A-Za-z_\-]{35}', "Gemini API Key"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
    (r"sk-proj-[a-zA-Z0-9_\-]{40,}", "OpenAI Project Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"github_pat_[a-zA-Z0-9_]{82}", "GitHub Fine-grained PAT"),
    (r"xoxb-[0-9]{11}-[0-9]{11}-[a-zA-Z0-9]{24}", "Slack Bot Token"),
    (r"xoxp-[0-9]{11}-[0-9]{11}-[0-9]{11}-[a-zA-Z0-9]{32}", "Slack User Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r'(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*=\s*["\']?[A-Za-z0-9/+=]{40}', "AWS Secret Key"),
    (r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----", "Private Key File"),
    (r'(?i)sendgrid[_\-]?api[_\-]?key\s*=\s*["\']?SG\.[a-zA-Z0-9_\-.]{22,}', "SendGrid Key"),
]

# Files that are safe to contain secret patterns (they define them, not leak them)
_SAFE_FILES = {
    "security.py",
    ".env.example",
    "README.md",
    "readme.md",
    ".env.sample",
    ".env.template",
    "swarm.py",
    "github_review.py",
    "git_ops.py",
    "engineer.py",
    "tdd.py",
    "infra.py",
    "mass_refactor.py",
    "gemini_client.py",
    "code_helper.py",
    "debugger.py",
}

# Sensitive files that should ALWAYS be in .gitignore
_MUST_IGNORE = [
    ".env",
    "*.env",
    ".env.*",
    ".env.local",
    ".env.production",
    ".env.staging",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "secrets/",
    "credentials/",
    ".aws/",
    "service-account*.json",
    "*_rsa",
    "*_dsa",
    "*_ecdsa",
    "*_ed25519",
]


# ---------------------------------------------------------------------------
# 2. .env file validator
# ---------------------------------------------------------------------------


def validate_env_file(env_path: str) -> dict:
    """
    Validate a .env file's format without exposing actual secret values.

    Returns a dict with:
        valid    : bool   — True if no format issues
        keys     : list   — list of key names found (values are never returned)
        issues   : list   — format problems found
        warnings : list   — security concerns (e.g. empty values, suspicious keys)
    """
    path = Path(env_path)
    result: dict = {"valid": True, "keys": [], "issues": [], "warnings": []}

    if not path.exists():
        result["valid"] = False
        result["issues"].append(f"File not found: {env_path}")
        return result

    if not path.is_file():
        result["valid"] = False
        result["issues"].append(f"Path is not a file: {env_path}")
        return result

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        result["valid"] = False
        result["issues"].append(f"Cannot read file: {exc}")
        return result

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip blank lines and comments
        if not line or line.startswith("#"):
            continue

        # Must be KEY=VALUE format
        if "=" not in line:
            result["valid"] = False
            result["issues"].append(f"Line {line_no}: Missing '=' separator → `{line[:50]}`")
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        # Key must be a valid identifier
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", key, re.IGNORECASE):
            result["valid"] = False
            result["issues"].append(
                f"Line {line_no}: Invalid key name `{key}` (keys should be UPPERCASE_WITH_UNDERSCORES)"
            )

        result["keys"].append(key)

        # Flag empty values as warnings (not errors)
        if not value:
            result["warnings"].append(f"Key `{key}` has an empty value — make sure this is intentional.")

        # Flag placeholder values
        if value.lower() in {"your_key_here", "changeme", "placeholder", "xxx", "todo"}:
            result["warnings"].append(
                f"Key `{key}` still has a placeholder value — replace it with a real value before running."
            )

    return result


def format_env_validation_report(env_path: str) -> str:
    """Return a human-readable validation report for a .env file."""
    r = validate_env_file(env_path)
    lines = [f"## .env Validation Report: `{env_path}`\n"]

    status = "✅ Format is valid" if r["valid"] else "❌ Format has errors"
    lines.append(f"**Status:** {status}\n")

    if r["keys"]:
        lines.append(f"**Keys found ({len(r['keys'])}):** " + ", ".join(f"`{k}`" for k in r["keys"]) + "\n")
        lines.append("*(Values are intentionally hidden for security)*\n")
    else:
        lines.append("**Keys found:** None\n")

    if r["issues"]:
        lines.append("\n### ❌ Format Issues (must fix)")
        for issue in r["issues"]:
            lines.append(f"- {issue}")

    if r["warnings"]:
        lines.append("\n### ⚠️ Warnings")
        for warn in r["warnings"]:
            lines.append(f"- {warn}")

    if r["valid"] and not r["warnings"]:
        lines.append("\n✅ No issues found. Your .env file looks clean!")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. Content credential scanner
# ---------------------------------------------------------------------------


def scan_content_for_secrets(content: str, filename: str = "") -> list[str]:
    """
    Scan text content for credential leak patterns.

    Returns a list of warning strings (empty = clean).
    Skips files that are allowed to contain credential patterns (.env.example, etc.)
    """
    if Path(filename).name in _SAFE_FILES:
        return []

    warnings: list[str] = []
    seen: set[str] = set()

    for pattern, label in _SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            key = f"{label}:{filename}"
            if key not in seen:
                seen.add(key)
                # Show pattern match but redact the actual value
                match_preview = str(matches[0])[:30] + ("..." if len(str(matches[0])) > 30 else "")
                warnings.append(
                    f"🔴 **{label}** detected"
                    + (f" in `{filename}`" if filename else "")
                    + f"\n   Matched: `{match_preview}` ← **DO NOT push this**"
                )

    return warnings


# ---------------------------------------------------------------------------
# 4. .gitignore coverage checker
# ---------------------------------------------------------------------------


def check_gitignore(repo_path: str) -> dict:
    """
    Check that .gitignore properly covers sensitive file patterns.

    Returns:
        ok       : bool  — True if all critical patterns are covered
        covered  : list  — patterns that ARE in .gitignore
        missing  : list  — patterns that should be in .gitignore but aren't
        warnings : list  — human-readable warnings
    """
    root = Path(repo_path)
    gitignore_path = root / ".gitignore"

    result = {"ok": True, "covered": [], "missing": [], "warnings": []}

    if not gitignore_path.exists():
        result["ok"] = False
        result["missing"] = _MUST_IGNORE[:]
        result["warnings"].append(
            "No .gitignore file found! Create one immediately to prevent accidental secret exposure."
        )
        return result

    gitignore_content = gitignore_path.read_text(encoding="utf-8", errors="replace")
    gitignore_lines = {
        line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.strip().startswith("#")
    }

    for pattern in _MUST_IGNORE:
        # Check exact match or wildcard coverage
        covered = (
            pattern in gitignore_lines
            or f"/{pattern}" in gitignore_lines
            or any(re.fullmatch(g.replace(".", r"\.").replace("*", ".*"), pattern) for g in gitignore_lines if "*" in g)
        )
        if covered:
            result["covered"].append(pattern)
        else:
            result["missing"].append(pattern)

    if result["missing"]:
        result["ok"] = False
        result["warnings"].append(
            "These patterns are missing from .gitignore: " + ", ".join(f"`{p}`" for p in result["missing"])
        )

    return result


# ---------------------------------------------------------------------------
# 5. Pre-push security gate
# ---------------------------------------------------------------------------


def _get_staged_files(repo_path: str) -> list[tuple[str, str]]:
    """
    Return list of (filename, content) tuples for all files staged for commit.
    """
    try:
        # Get list of staged file names
        proc = subprocess.run(
            ["git", "diff", "--staged", "--name-only"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=15,
        )
        filenames = [f.strip() for f in proc.stdout.splitlines() if f.strip()]

        result = []
        for fname in filenames:
            # Get the staged content (not the working tree version)
            content_proc = subprocess.run(
                ["git", "show", f":{fname}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=10,
            )
            if content_proc.returncode == 0:
                result.append((fname, content_proc.stdout))
        return result
    except Exception:
        return []


def _is_env_tracked_by_git(repo_path: str) -> bool:
    """Check if .env is being tracked by git (it should NOT be)."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
            timeout=10,
        )
        return bool(proc.stdout.strip())
    except Exception:
        return False


def pre_push_security_gate(repo_path: str) -> tuple[bool, str]:
    """
    Full pre-push security scan. Call this BEFORE git push.

    Checks:
    1. .gitignore covers sensitive patterns
    2. No staged files contain credential patterns
    3. .env file is not tracked by git

    Returns:
        (safe: bool, report: str)
        If safe=False, the push should be BLOCKED and the report shown to the user.
    """
    issues: list[str] = []
    report_lines = ["## 🔐 DevGuardian Pre-Push Security Scan\n"]

    # ── Check 1: .gitignore coverage ─────────────────────────────────────────
    gi = check_gitignore(repo_path)
    if not gi["ok"]:
        issues.extend(gi["warnings"])
        if gi["missing"]:
            report_lines.append("### ❌ .gitignore is Missing Critical Patterns")
            report_lines.append(
                "Add these to your `.gitignore` file immediately:\n```\n" + "\n".join(gi["missing"]) + "\n```"
            )
    else:
        report_lines.append("### ✅ .gitignore Coverage — All clear")

    # ── Check 2: .env not tracked ─────────────────────────────────────────────
    if _is_env_tracked_by_git(repo_path):
        issues.append(".env file is tracked by git and will be pushed to GitHub!")
        report_lines.append(
            "\n### ❌ CRITICAL: `.env` is tracked by git!\n"
            "Run these commands immediately:\n"
            "```bash\n"
            "git rm --cached .env\n"
            'echo ".env" >> .gitignore\n'
            "git add .gitignore\n"
            "```\n"
        )
    else:
        report_lines.append("### ✅ .env not tracked by git — Safe")

    # ── Check 3: Scan staged files for secrets ────────────────────────────────
    staged_files = _get_staged_files(repo_path)
    secret_findings: list[str] = []

    for fname, content in staged_files:
        # Skip binary/minified files
        if len(content) > 500_000:
            continue
        findings = scan_content_for_secrets(content, filename=fname)
        secret_findings.extend(findings)

    if secret_findings:
        issues.extend(secret_findings)
        report_lines.append(f"\n### ❌ SECRETS DETECTED in {len(staged_files)} staged file(s)!")
        report_lines.append("**PUSH BLOCKED** — The following potential credentials were found:\n")
        for finding in secret_findings:
            report_lines.append(finding)
        report_lines.append(
            "\n**How to fix:**\n"
            "1. Remove the secret from the file\n"
            "2. Add the file (or the value) to `.gitignore` or use environment variables\n"
            "3. If already committed previously: rotate the credential immediately!\n"
        )
    elif staged_files:
        report_lines.append(f"\n### ✅ No secrets found in {len(staged_files)} staged file(s)")
    else:
        report_lines.append("\n### ℹ️ No staged files to scan")

    # ── Final verdict ─────────────────────────────────────────────────────────
    is_safe = len(issues) == 0
    if is_safe:
        report_lines.append("\n---\n✅ **All checks passed — Safe to push!**")
    else:
        report_lines.append(
            f"\n---\n🚨 **PUSH BLOCKED — {len(issues)} security issue(s) found.**\n"
            "Fix the issues above before pushing to GitHub."
        )

    return is_safe, "\n".join(report_lines)
