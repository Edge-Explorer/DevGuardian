"""
Gemini 2.0 Flash API client wrapper for DevGuardian.
All AI interactions go through this single module.
"""

import os
from google import genai
from google.genai import types
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

_CLIENT = genai.Client(api_key=_API_KEY)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------
def ask_gemini(prompt: str, system_instruction: str | None = None) -> str:
    """
    Send a prompt to Gemini 2.0 Flash using the modern google-genai SDK.

    Args:
        prompt: The user/task prompt.
        system_instruction: Optional system-level instruction to steer the model.

    Returns:
        The model's text response as a string.
    """
    try:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ) if system_instruction else None

        # Use the unified client.models.generate_content method
        response = _CLIENT.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config,
        )

        # The response.text property still works similarly
        return response.text.strip() if response.text else "⚠️ Empty response from Gemini."

    except Exception as exc:
        return f"❌ Gemini API error: {exc}"
