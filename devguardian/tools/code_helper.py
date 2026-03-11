# 🛡️ DevGuardian Project — Core Module
"""
Code helper tool — explain, review, generate, and improve code via Gemini.

All functions accept an optional `project_path` argument. When provided,
DevGuardian reads the project's README, dependencies, file structure, and
any files directly imported by the code — giving Gemini full project context
so it generates code that fits perfectly into the existing codebase.
"""

from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.file_reader import build_project_context

_SYSTEM = (
    "You are DevGuardian, a world-class software engineer and coding mentor. "
    "You write clean, efficient, well-commented code and give crystal-clear explanations. "
    "When you receive a '🛡️ DevGuardian — Project Context' section, USE IT: "
    "follow the same patterns, libraries, naming conventions, and architecture "
    "that already exist in the project. Never suggest tools or approaches that "
    "conflict with the existing stack. "
    "When explaining: be concise but complete. "
    "When generating code: follow best practices, add docstrings, handle edge cases. "
    "When reviewing: highlight bugs, security issues, performance problems, and style issues."
)


def explain_code(
    code: str,
    question: str = "",
    language: str = "",
    project_path: str = "",
) -> str:
    """
    Explain what a piece of code does in plain English.

    Args:
        code         : The code to explain.
        question     : Optional specific question about the code.
        language     : Optional language hint.
        project_path : Optional path to the project root for full context.

    Returns:
        Gemini's explanation, project-aware if project_path is provided.
    """
    ctx = ""
    if project_path:
        ctx = f"\n\n{build_project_context(project_path, code=code)}\n"

    lang = f"({language})" if language else ""
    q = f"\n\nSpecific question: {question}" if question else ""
    prompt = f"Explain the following code {lang}:{ctx}\n\n```\n{code}\n```{q}"
    return ask_gemini(prompt, system_instruction=_SYSTEM)


def review_code(
    code: str,
    language: str = "",
    focus: str = "",
    project_path: str = "",
) -> str:
    """
    Perform a thorough code review — bugs, security, performance, style.

    Args:
        code         : The code to review.
        language     : Optional language hint.
        focus        : Optional focus area (e.g. "security", "performance").
        project_path : Optional path to the project root for full context.
                       When provided, DevGuardian checks for consistency with
                       the rest of the codebase (naming, patterns, libraries).

    Returns:
        Review report with findings and suggestions.
    """
    ctx = ""
    if project_path:
        ctx = f"\n\n{build_project_context(project_path, code=code)}\n"

    lang = f"Language: {language}\n" if language else ""
    focus_hint = f"Focus especially on: {focus}\n" if focus else ""
    prompt = (
        f"{lang}{focus_hint}{ctx}"
        f"\nPlease do a thorough code review of the following:\n\n```\n{code}\n```\n\n"
        "Provide: bugs found, security issues, performance tips, style improvements, "
        "and — if project context was provided — any inconsistencies with the existing codebase."
    )
    return ask_gemini(prompt, system_instruction=_SYSTEM)


def generate_code(
    description: str,
    language: str = "Python",
    context_path: str = "",
    project_path: str = "",
) -> str:
    """
    Generate code from a natural language description.

    Args:
        description  : What the code should do.
        language     : Target programming language (default: Python).
        context_path : Alias for project_path (backwards-compatible).
        project_path : Path to the project root — gives Gemini the full stack,
                       structure, and patterns to generate perfectly fitting code.

    Returns:
        Generated code with docstrings, type hints, error handling, and usage example.
    """
    # Support both parameter names for backwards compatibility
    root = project_path or context_path
    ctx = ""
    if root:
        ctx = f"\n\n{build_project_context(root, code=description)}\n"

    prompt = (
        f"Write {language} code that does the following:\n\n{description}"
        f"{ctx}\n\n"
        "Requirements:\n"
        "- Include docstrings and type hints\n"
        "- Add error handling for edge cases\n"
        "- Follow the project's existing patterns if context was provided\n"
        "- Include a brief usage example at the end"
    )
    return ask_gemini(prompt, system_instruction=_SYSTEM)


def improve_code(
    code: str,
    language: str = "",
    instructions: str = "",
    project_path: str = "",
) -> str:
    """
    Refactor or improve existing code.

    Args:
        code         : The code to improve.
        language     : Optional language hint.
        instructions : Specific improvement goals (e.g. "make it async", "add caching").
        project_path : Optional path to project root — ensures the improved code
                       stays consistent with the rest of the codebase.

    Returns:
        Improved version of the code with a summary of all changes made.
    """
    ctx = ""
    if project_path:
        ctx = f"\n\n{build_project_context(project_path, code=code)}\n"

    lang = f"Language: {language}\n" if language else ""
    extra = f"Specific instructions: {instructions}\n" if instructions else ""
    prompt = (
        f"{lang}{extra}{ctx}"
        f"\nImprove and refactor the following code:\n\n```\n{code}\n```\n\n"
        "Return the improved code and a clear summary of every change made."
    )
    return ask_gemini(prompt, system_instruction=_SYSTEM)
