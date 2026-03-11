# 🛡️ DevGuardian Project — Core Module
"""
🧪 TDD Auto-Pilot
==================
Generates pytest tests for a target file, runs them, and iteratively fixes
the source code if tests fail — up to 3 rounds. Returns a full report.
"""

import subprocess
import sys
from pathlib import Path

from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.file_reader import build_project_context


_SYSTEM = (
    "You are an expert Python Test Engineer. "
    "Write clean, meaningful pytest test cases. "
    "Return ONLY valid Python code — no markdown, no fences."
)

_FIX_SYSTEM = (
    "You are an expert Python developer. "
    "Fix the given source code so that the failing tests pass. "
    "Return ONLY the complete, corrected source file — no markdown, no fences."
)


def test_and_fix(project_path: str, target_file: str, max_rounds: int = 3) -> str:
    """
    1. Generate tests for `target_file` using Gemini.
    2. Write tests to tests/test_<name>.py.
    3. Run pytest and capture output.
    4. If tests fail, ask Gemini to fix the source. Repeat up to max_rounds.

    Args:
        project_path: Absolute path to the project root.
        target_file:  Path to the file under test (relative to project_path or absolute).
        max_rounds:   Max fix-retry iterations (default 3).
    """
    root = Path(project_path)
    target = Path(target_file) if Path(target_file).is_absolute() else root / target_file

    if not target.exists():
        return f"❌ Target file not found: {target}"

    source_code = target.read_text(encoding="utf-8")
    file_name = target.stem                         # e.g. "security"
    test_file = root / "tests" / f"test_{file_name}.py"
    test_file.parent.mkdir(exist_ok=True)

    # ──────────────────────────────────────────────
    # Step 1 — Generate tests
    # ──────────────────────────────────────────────
    ctx = build_project_context(project_path, code=source_code)
    prompt = (
        f"{ctx}\n\n"
        f"## TARGET FILE TO TEST: {target.name}\n\n"
        f"```python\n{source_code}\n```\n\n"
        "Write comprehensive pytest unit tests for the functions/classes above. "
        "Use only the stdlib and pytest. Assume the module can be imported as-is."
    )
    tests_code = ask_gemini(prompt, system_instruction=_SYSTEM)

    # Strip accidental markdown fences
    if "```" in tests_code:
        lines = tests_code.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        tests_code = "\n".join(lines)

    test_file.write_text(tests_code, encoding="utf-8")
    report_parts = [
        f"## 🧪 TDD Auto-Pilot Report for `{target.name}`\n",
        f"✅ Tests written to: `{test_file.relative_to(root)}`\n",
    ]

    python_exe = sys.executable

    # ──────────────────────────────────────────────
    # Step 2 — Run → Fix loop
    # ──────────────────────────────────────────────
    for round_num in range(1, max_rounds + 1):
        result = subprocess.run(
            [python_exe, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0

        report_parts.append(f"\n### Round {round_num} — {'✅ PASSED' if passed else '❌ FAILED'}\n")
        report_parts.append(f"```\n{output[:3000]}\n```\n")

        if passed:
            report_parts.append("\n🎉 **All tests passed!** No fixes needed.")
            break

        if round_num == max_rounds:
            report_parts.append("\n⚠️ Max rounds reached. Manual review needed.")
            break

        # Ask Gemini to fix the source
        current_source = target.read_text(encoding="utf-8")
        fix_prompt = (
            f"The following pytest tests are failing:\n\n```\n{output[:2000]}\n```\n\n"
            f"Here is the source file `{target.name}`:\n\n```python\n{current_source}\n```\n\n"
            "Fix the source code so the tests pass. Return ONLY the corrected Python file."
        )
        fixed_code = ask_gemini(fix_prompt, system_instruction=_FIX_SYSTEM)

        if "```" in fixed_code:
            lines = fixed_code.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            fixed_code = "\n".join(lines)

        target.write_text(fixed_code, encoding="utf-8")
        report_parts.append(f"\n🔧 Applied AI fix (round {round_num}) to `{target.name}`.\n")

    return "\n".join(report_parts)