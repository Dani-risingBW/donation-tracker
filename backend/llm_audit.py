"""Optional, redacted LLM analysis for admin audit events.

The LLM is never the source of truth for audit records. It only summarizes
metadata that has already been recorded by the application.
"""

import json
import logging
import os


logger = logging.getLogger(__name__)
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
ALLOWED_FIELDS = {
    "action",
    "actor_role",
    "outcome",
    "target_type",
    "timestamp",
}


def analyze_audit_events(events):
    """Return an optional security summary for already-redacted events.

    Returns None when the feature is disabled or its optional dependency is
    unavailable. Raw donor details, screenshots, and request payloads are not
    accepted into the prompt.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    safe_events = [
        {key: event[key] for key in ALLOWED_FIELDS if key in event}
        for event in events
        if isinstance(event, dict)
    ]
    if not safe_events:
        return "No audit activity to analyze."

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=(
                "Review these redacted admin audit events. Summarize unusual "
                "patterns and recommend follow-up actions. Do not invent facts. "
                "Return concise plain text.\n\n"
                + json.dumps(safe_events, separators=(",", ":"))
            ),
        )
        return response.text.strip()
    except ImportError:
        logger.warning("Gemini audit analysis skipped: google-genai is not installed.")
    except Exception:
        logger.exception("Gemini audit analysis failed.")
    return None
