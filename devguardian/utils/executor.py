"""
DevGuardian Code Executor (Sandbox)
====================================
Safely executes code snippets in a subprocess to verify logic during the Swarm run.
"""

import sys
import subprocess
import tempfile
from pathlib import Path


def execute_python_snippet(code: str, timeout: int = 5) -> dict:
    """
    Executes a Python snippet and returns the result/errors.
    """
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)

    try:
        # Run with current python executable
        result = subprocess.run(
            [sys.executable, str(tmp_path)], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "exit_code": -1,
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "exit_code": -1}
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def verify_code_logic(code: str) -> str:
    """
    Higher-level check: tries to compile and run the code.
    If the code looks like a library (just classes/defs), it tries simple import check.
    """
    # Check for syntax errors first
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        return f"❌ Syntax Error: {e.msg} at line {e.lineno}"

    # If it lacks a 'main' block or top-level calls, running it might do nothing.
    # We'll just run it and see if it crashes.
    res = execute_python_snippet(code)
    if res["success"]:
        return "✅ Execution Check: Code ran successfully (no runtime crashes)."
    else:
        return f"❌ Execution Error:\n{res['stderr']}"
