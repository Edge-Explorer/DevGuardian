"""
Gemini 2.0 Flash API client wrapper for DevGuardian.
All AI interactions go through this single module.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------
_API_KEY = os.getenv("GEMINI_API_KEY")
if not _API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. "
        "Copy .env.example → .env and fill in your key."
    )

genai.configure(api_key=_API_KEY)

# Use Gemini 2.0 Flash — fast, free-tier friendly
_MODEL = genai.GenerativeModel("gemini-2.0-flash")


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------
def ask_gemini(prompt: str, system_instruction: str | None = None) -> str:
    """
    Send a prompt to Gemini 2.0 Flash and return the text response.

    Args:
        prompt: The user/task prompt.
        system_instruction: Optional system-level instruction to steer the model.

    Returns:
        The model's text response as a string.
    """
    try:
        if system_instruction:
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=system_instruction,
            )
        else:
            model = _MODEL

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        return f"❌ Gemini API error: {exc}"
