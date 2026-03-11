# 🛡️ DevGuardian Project — Core Module
"""
Gemini 2.0 Flash API client wrapper for DevGuardian.
All AI interactions go through this single module.

LAZY INIT: The client is created on first use, not at import time.
This keeps server startup near-instant so the MCP initialize handshake never times out.
"""

import os
# Note: load_dotenv() is called once by server.py at startup — no need to repeat it here.

# ---------------------------------------------------------------------------
# Lazy client — created on first call to ask_gemini()
# ---------------------------------------------------------------------------
_CLIENT = None


def _get_client():
    """Return the shared Gemini client, creating it on first call."""
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Copy .env.example -> .env and fill in your key."
            )
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


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
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ) if system_instruction else None

        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config,
        )

        return response.text.strip() if response.text else "Empty response from Gemini."

    except Exception as exc:
        return f"Gemini API error: {exc}"