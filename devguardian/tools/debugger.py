"""
Debug tool — sends error messages / stack traces to Gemini and returns a fix.
"""

from devguardian.utils.gemini_client import ask_gemini

_SYSTEM = (
    "You are DevGuardian, an elite software debugger. "
    "When given an error message, stack trace, or broken code, you:\n"
    "1. Identify the ROOT CAUSE clearly.\n"
    "2. Explain it in simple terms.\n"
    "3. Provide the EXACT fix with corrected code.\n"
    "4. Mention any related pitfalls to watch out for.\n"
    "Be concise, precise, and developer-friendly."
)


def debug_error(
    error_message: str,
    stack_trace: str = "",
    code_snippet: str = "",
    language: str = "",
) -> str:
    """
    Analyse an error and return a structured fix.

    Args:
        error_message : The error text (e.g. "TypeError: 'NoneType' object is not subscriptable").
        stack_trace   : Optional full stack trace.
        code_snippet  : Optional code that caused the error.
        language      : Optional programming language (e.g. "Python", "JavaScript").

    Returns:
        Gemini's structured debugging response.
    """
    lang_hint = f"Language: {language}\n" if language else ""

    prompt = f"""{lang_hint}## Error Message
{error_message}
"""

    if stack_trace:
        prompt += f"\n## Stack Trace\n```\n{stack_trace}\n```\n"

    if code_snippet:
        prompt += f"\n## Code That Caused the Error\n```\n{code_snippet}\n```\n"

    prompt += "\nPlease debug this and provide a clear fix."

    return ask_gemini(prompt, system_instruction=_SYSTEM)
