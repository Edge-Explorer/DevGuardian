# 🛡️ DevGuardian Project — Core Module
"""
Debug tool — sends error messages / stack traces to Gemini and returns a fix.

Accepts an optional project_path so Gemini understands the full codebase
and gives fixes that fit the actual project structure and patterns.
"""

from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.file_reader import build_project_context

_SYSTEM = (
    "You are DevGuardian, an elite software debugger. "
    "When given an error message, stack trace, or broken code, you:\n"
    "1. Identify the ROOT CAUSE clearly.\n"
    "2. Explain it in simple terms.\n"
    "3. Provide the EXACT fix with corrected code.\n"
    "4. Mention any related pitfalls to watch out for.\n"
    "If a '🛡️ DevGuardian — Project Context' section is provided, use it to "
    "understand the codebase structure and give a fix that fits the existing patterns. "
    "Be concise, precise, and developer-friendly."
)


def debug_error(
    error_message: str,
    stack_trace: str = "",
    code_snippet: str = "",
    language: str = "",
    project_path: str = "",
) -> str:
    """
    Analyse an error and return a structured fix.

    Args:
        error_message : The error text (e.g. "TypeError: 'NoneType' object is not subscriptable").
        stack_trace   : Optional full stack trace.
        code_snippet  : Optional code that caused the error.
        language      : Optional programming language (e.g. "Python", "JavaScript").
        project_path  : Optional path to project root — gives Gemini full project
                        context so the fix matches the existing codebase structure.

    Returns:
        Gemini's structured debugging response with root cause and exact fix.
    """
    ctx = ""
    if project_path:
        ctx = f"\n\n🛡️ DevGuardian — Project Context:\n{build_project_context(project_path, code_snippet)}\n"

    lang_hint = f"Language: {language}\n" if language else ""

    prompt = f"{lang_hint}{ctx}\n## Error Message\n{error_message}\n"

    if stack_trace:
        prompt += f"\n## Stack Trace\n```\n{stack_trace}\n```\n"

    if code_snippet:
        prompt += f"\n## Code That Caused the Error\n```\n{code_snippet}\n```\n"

    prompt += "\nPlease debug this and provide a clear fix."

    return ask_gemini(prompt, system_instruction=_SYSTEM)
