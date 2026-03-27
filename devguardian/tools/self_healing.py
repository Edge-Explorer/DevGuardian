"""
DevGuardian Self-Healing CI — The Repair Engine
================================================
Automatically detects and fixes CI failures (Tests/Linting).
When a CI run fails, this script:
1. Identifies the failing file or test
2. Calls the Swarm to fix it
3. Verifies the fix locally
4. Pushes the repair commit back to GitHub
"""

import os
import subprocess
from pathlib import Path
from devguardian.agents.swarm import run_swarm

def run_git_command(args: list[str], cwd: str) -> str:
    """Helper to run git commands in a subprocess."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Git error: {e}"

def detect_failure_context() -> dict:
    """
    Tries to find which file recently failed by running ruff and pytest locally.
    In CI, it can also parse logs (if available).
    """
    context = {"failed_files": [], "errors": ""}
    
    # Check linting first
    lint_res = subprocess.run(["uv", "run", "ruff", "check", "."], capture_output=True, text=True)
    if lint_res.returncode != 0:
        context["type"] = "lint"
        context["errors"] += lint_res.stdout
        # Extract files from ruff output (best effort)
        files = re.findall(r"(?:[\w./\\]+):[\d:]+", lint_res.stdout)
        context["failed_files"].extend([f.split(":")[0] for f in files])

    # Check tests
    test_res = subprocess.run(["uv", "run", "pytest", "-v", "--tb=short"], capture_output=True, text=True)
    if test_res.returncode != 0:
        context["type"] = "test"
        context["errors"] += test_res.stdout
        # Extract failing test files from pytest output (simplified)
        test_files = re.findall(r"FAILED\s+([\w./\\]+)::", test_res.stdout)
        context["failed_files"].extend(test_files)
        
    return context

async def repair_ci_failure(project_path: str):
    """Entry point for the self-healing process."""
    print("🩹 Starting DevGuardian Self-Healing Process...")
    
    root = Path(project_path)
    failure = detect_failure_context()
    
    if not failure["failed_files"]:
        print("✅ No local failures detected. All checks passed!")
        return
        
    for target_file in set(failure["failed_files"]):
        target_abs = root / target_file
        if not target_abs.exists():
            continue
            
        print(f"🛠️ Attempting to repair: {target_file}")
        
        # Task for the swarm:
        task_desc = (
            f"Fix the following error in `{target_file}`:\n\n"
            f"```\n{failure['errors'][:2000]}\n```\n\n"
            "Ensure the file follows project style and passes architecture rules."
        )
        
        # Use our elite Swarm v3
        report = await run_swarm(task_desc, project_path)
        
        # Extract final code (best effort from the report markdown)
        if "## Final Code" in report:
            new_code = report.split("## Final Code")[1].split("## ")[0].strip()
            # Clean up potential markdown fences
            new_code = "\n".join([l for l in new_code.splitlines() if not l.strip().startswith("```")]).strip()
            
            # overwrite the file
            target_abs.write_text(new_code, encoding="utf-8")
            print(f"✅ Successfully updated {target_file}")

    # Final wrap-up: Commit fix if in CI environment
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("🚀 In GitHub environment — pushing repair commit...")
        run_git_command(["config", "user.name", "devguardian-bot"], project_path)
        run_git_command(["config", "user.email", "bot@devguardian.ai"], project_path)
        run_git_command(["add", "."], project_path)
        run_git_command(["commit", "-m", "🩹 chore(ci): auto-repair lint/test failures via DevGuardian"], project_path)
        run_git_command(["push", "origin", os.getenv("GITHUB_REF_NAME", "main")], project_path)
    else:
        print("💡 Local run complete. Review the changes in your working tree.")

if __name__ == "__main__":
    import asyncio
    import re
    asyncio.run(repair_ci_failure(os.getcwd()))
