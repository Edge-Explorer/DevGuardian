"""
Code helper tool — explain, review, and generate code via Gemini.
"""

from devguardian.utils.gemini_client import ask_gemini
from devguardian.utils.file_reader import build_project_context

_SYSTEM = (
    "You are DevGuardian, a world-class software engineer and coding mentor. "
    "You write clean, efficient, well-commented code and give crystal-clear explanations. "
    "When explaining: be concise but complete. "
    "When generating code: follow best practices, add docstrings, handle edge cases. "
    "When reviewing: highlight bugs, security issues, performance problems, and style issues."
)


def explain_code(code: str, question: str = "", language: str = "") -> str:
    """
    Explain what a piece of code does.

    Args:
        code     : The code to explain.
        question : Optional specific question about the code.
        language : Optional language hint.

    Returns:
        Gemini's explanation.
    """
    lang = f"({language})" if language else ""
    q = f"\n\nSpecific question: {question}" if question else ""
    prompt = f"Explain the following code {lang}:\n\n```\n{code}\n```{q}"
    return ask_gemini(prompt, system_instruction=_SYSTEM)


def review_code(code: str, language: str = "", focus: str = "") -> str:
    """
    Perform a code review.

    Args:
        code     : The code to review.
        language : Optional language hint.
        focus    : Optional focus area (e.g. "security", "performance", "readability").

    Returns:
        Gemini's code review with suggestions.
    """
    lang = f"Language: {language}\n" if language else ""
    focus_hint = f"Focus especially on: {focus}\n" if focus else ""
    prompt = (
        f"{lang}{focus_hint}"
        f"Please do a thorough code review of the following:\n\n```\n{code}\n```\n\n"
        "Provide: bugs found, security issues, performance tips, and style improvements."
    )
    return ask_gemini(prompt, system_instruction=_SYSTEM)


def generate_code(description: str, language: str = "Python", context_path: str = "") -> str:
    """
    Generate code from a natural language description.

    Args:
        description  : What the code should do.
        language     : Target programming language (default: Python).
        context_path : Optional path to project folder for additional context.

    Returns:
        Generated code with explanation.
    """
    context = ""
    if context_path:
        ctx = build_project_context(context_path)
        context = f"\n\n## Project Context\n{ctx}\n"

    prompt = (
        f"Write {language} code that does the following:\n\n{description}"
        f"{context}\n\n"
        "Include: docstrings, type hints (if applicable), error handling, and a brief usage example."
    )
    return ask_gemini(prompt, system_instruction=_SYSTEM)


def improve_code(code: str, language: str = "", instructions: str = "") -> str:
    """
    Refactor or improve existing code.

    Args:
        code         : The code to improve.
        language     : Optional language hint.
        instructions : Specific improvement instructions.

    Returns:
        Improved version of the code with explanation of changes.
    """
    lang = f"Language: {language}\n" if language else ""
    extra = f"Specific instructions: {instructions}\n" if instructions else ""
    prompt = (
        f"{lang}{extra}"
        f"Improve and refactor the following code:\n\n```\n{code}\n```\n\n"
        "Return the improved code and a summary of all changes made."
    )
    return ask_gemini(prompt, system_instruction=_SYSTEM)
