# 🛡️ DevGuardian Project — Core Module
"""
🏗️ Mass Refactoring Tool
==========================
Applies a single refactoring instruction across an entire Python project.
DevGuardian reads every .py file, identifies which ones need changes,
rewrites them with Gemini, and reports what was modified.

Example instructions:
  "Replace requests with aiohttp (async)"
  "Add type hints to all function signatures"
  "Convert all print() calls to logging.info()"
"""

from pathlib import Path
from devguardian.utils.gemini_client import ask_gemini


_REFACTOR_SYSTEM = (
    "You are an expert Python refactoring engineer. "
    "Given a Python file and a specific refactoring instruction, "
    "return ONLY the complete, updated Python file — no markdown fences, no explanations. "
    "If the file does NOT need changes based on the instruction, return the exact word: SKIP"
)

# Directories to always skip
_SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", "dist", "build"}

# Max file size to send to Gemini (characters)
_MAX_FILE_CHARS = 8_000


def mass_refactor(project_path: str, instruction: str) -> str:
    """
    Apply a refactoring instruction to all Python files in a project.

    Args:
        project_path: Absolute path to the project root.
        instruction:  What to change, e.g. "Replace requests with httpx".

    Returns:
        A detailed report of all modified files.
    """
    root = Path(project_path)

    if not root.exists():
        return f"❌ Project path not found: {project_path}"

    # Collect all .py files, filtering skip dirs
    all_py_files = [
        f for f in root.rglob("*.py")
        if not any(part in _SKIP_DIRS for part in f.parts)
    ]

    if not all_py_files:
        return "❌ No Python files found in project."

    modified = []
    skipped = []
    errors = []

    report_parts = [
        "## 🏗️ Mass Refactor Report\n",
        f"**Instruction:** `{instruction}`\n",
        f"**Scanning {len(all_py_files)} Python files...**\n\n",
    ]

    for py_file in all_py_files:
        rel_path = py_file.relative_to(root)
        try:
            source = py_file.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"- ⚠️ Could not read `{rel_path}`: {e}")
            continue

        # Skip files that are too large
        if len(source) > _MAX_FILE_CHARS:
            skipped.append(f"- ⏭️ `{rel_path}` (too large: {len(source)} chars)")
            continue

        prompt = (
            f"## Refactoring Instruction\n{instruction}\n\n"
            f"## File: {rel_path}\n\n"
            f"```python\n{source}\n```\n\n"
            "Apply the instruction to this file. "
            "If no changes are needed, reply with exactly: SKIP"
        )

        result = ask_gemini(prompt, system_instruction=_REFACTOR_SYSTEM)

        # Strip accidental markdown fences
        if "```" in result:
            lines = result.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            result = "\n".join(lines).strip()

        if result.strip().upper() == "SKIP":
            skipped.append(f"- ⬜ `{rel_path}` (no changes needed)")
            continue

        # Write the refactored content back
        try:
            py_file.write_text(result, encoding="utf-8")
            modified.append(f"- ✅ `{rel_path}`")
        except Exception as e:
            errors.append(f"- ❌ Failed to write `{rel_path}`: {e}")

    # Build the report
    if modified:
        report_parts.append(f"### ✅ Modified Files ({len(modified)})\n")
        report_parts.extend(modified)
        report_parts.append("\n")

    if skipped:
        report_parts.append(f"### ⬜ Skipped ({len(skipped)})\n")
        report_parts.extend(skipped[:10])   # Show max 10
        if len(skipped) > 10:
            report_parts.append(f"... and {len(skipped) - 10} more\n")
        report_parts.append("\n")

    if errors:
        report_parts.append(f"### ⚠️ Errors ({len(errors)})\n")
        report_parts.extend(errors)
        report_parts.append("\n")

    total = len(modified)
    report_parts.append(
        f"\n---\n**Result:** {total} file(s) refactored successfully. "
        f"Run `git diff` to review changes before committing."
    )

    return "\n".join(report_parts)
