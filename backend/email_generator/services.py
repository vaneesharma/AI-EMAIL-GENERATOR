"""Everything that talks to the AI API lives here, so views stay simple.

Flow:  build prompt -> call_ai() -> parse_email() -> (subject, body)
Any problem is raised as AIServiceError with a message that is safe to show
to the user (no keys, URLs or stack traces).
"""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """An error whose message can be shown directly to the user."""


LANGUAGE_NOTES = {
    "English": "English",
    "Hindi": "Hindi written in Devanagari script",
    "Hinglish": "Hinglish (Hindi written in the English/Roman alphabet, mixed naturally with common English words)",
}

MODIFY_INSTRUCTIONS = {
    "improve": "Improve the clarity, grammar and professionalism of this email. Keep the same meaning and roughly the same length.",
    "shorter": "Make this email shorter and more concise. Keep every key point and stay polite.",
    "formal": "Rewrite this email in a more formal, professional tone.",
    "friendly": "Rewrite this email in a warm, polite and friendly tone, while staying respectful.",
}

OUTPUT_FORMAT = (
    "Reply in EXACTLY this format and nothing else:\n"
    "SUBJECT: <one-line email subject>\n"
    "BODY:\n"
    "<the complete email body, starting with the greeting and ending with the sign-off>"
)

SYSTEM_PROMPT = (
    "You are an expert email writer. Write natural, well-structured emails that are "
    "relevant to the details the user gives you. Use only the facts provided: do not "
    "invent names, dates, numbers, companies or achievements. If the sender's name or "
    "another required detail is missing, use a short placeholder such as [Your Name]. "
    "Use plain text only (no markdown, no bullet symbols like ** or #) and add no "
    "explanations or comments outside the email.\n\n" + OUTPUT_FORMAT
)


# ------------------------------------------------------------------ AI call
def call_ai(messages, temperature=0.7):
    """Send chat messages to the configured OpenAI-compatible API, return the text."""
    api_key = (settings.AI_API_KEY or "").strip()
    if not api_key or api_key == "your_api_key_here":
        logger.error("AI_API_KEY is missing. Set it in backend/.env")
        raise AIServiceError("The AI service is not configured yet. Please contact the administrator.")

    try:
        response = requests.post(
            settings.AI_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": settings.AI_MODEL, "messages": messages, "temperature": temperature},
            timeout=settings.AI_TIMEOUT,
        )
    except requests.Timeout as exc:
        logger.warning("AI API timed out")
        raise AIServiceError("The AI service took too long to respond. Please try again.") from exc
    except requests.RequestException as exc:
        logger.exception("Could not reach the AI API")
        raise AIServiceError("Could not reach the AI service. Check your internet connection and try again.") from exc

    if response.status_code != 200:
        # Details go to the server log only, never to the user.
        logger.error("AI API returned %s: %s", response.status_code, response.text[:500])
        if response.status_code in (401, 403):
            raise AIServiceError("The AI service rejected the request. Please contact the administrator.")
        if response.status_code == 429:
            raise AIServiceError("The AI service is busy or its usage limit was reached. Please try again shortly.")
        raise AIServiceError("The AI service returned an error. Please try again later.")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected AI response: %s", response.text[:500])
        raise AIServiceError("The AI service returned an unexpected response. Please try again.") from exc

    if not content or not content.strip():
        raise AIServiceError("The AI service returned an empty response. Please try again.")
    return content


# ------------------------------------------------------------------ parsing
_SUBJECT_RE = re.compile(r"^[ \t*#>_-]*subject[ \t*_]*:[ \t*_]*(.+)$", re.IGNORECASE | re.MULTILINE)
_BODY_LABEL_RE = re.compile(r"^[ \t*#>_-]*body[ \t*_]*:[ \t*_]*", re.IGNORECASE)


def parse_email(text):
    """Split the AI reply ("SUBJECT: ...\\nBODY:\\n...") into (subject, body)."""
    text = re.sub(r"```[a-zA-Z]*", "", text).strip()  # remove code fences if the model added them
    match = _SUBJECT_RE.search(text)
    if not match:
        raise AIServiceError("Could not read the email from the AI response. Please try again.")

    subject = match.group(1).strip(" *_\t")[:255]
    body = text[match.end():].strip()
    body = _BODY_LABEL_RE.sub("", body).replace("**", "").strip()

    if not subject or not body:
        raise AIServiceError("The AI response was incomplete. Please try again.")
    return subject, body


# ------------------------------------------------------------------ public API
def generate_email(purpose, recipient_type, tone, language, important_points,
                   additional_instructions="", variation=False):
    """Generate a new email from the user's details. Returns (subject, body)."""
    user_prompt = (
        "Write an email with these details.\n"
        f"Purpose: {purpose}\n"
        f"Recipient: {recipient_type}\n"
        f"Tone: {tone}\n"
        f"Language: {LANGUAGE_NOTES.get(language, language)}\n"
        f"Important points to include:\n{important_points}\n"
        f"Additional instructions: {additional_instructions or 'None'}"
    )
    if variation:
        user_prompt += "\n\nWrite a fresh version with different wording and structure from a typical first draft."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    return parse_email(call_ai(messages, temperature=0.9 if variation else 0.7))


def modify_email(subject, body, action, language="English"):
    """Rewrite an existing email (improve / shorter / formal / friendly)."""
    if action not in MODIFY_INSTRUCTIONS:
        raise AIServiceError("Unknown action requested.")

    user_prompt = (
        f"{MODIFY_INSTRUCTIONS[action]}\n"
        f"Keep the email in {LANGUAGE_NOTES.get(language, language)}.\n\n"
        f"Current email:\nSUBJECT: {subject}\nBODY:\n{body}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    return parse_email(call_ai(messages, temperature=0.5))
