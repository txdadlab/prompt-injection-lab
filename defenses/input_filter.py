"""Input filter defense — blocks messages containing suspicious keywords.

Intentionally bypassable: only checks case-insensitive substring match with
basic normalization. Misses unicode homoglyphs, base64, leetspeak, other
languages, and indirect phrasing.
"""

import re
import unicodedata


def normalize(text: str) -> str:
    """Basic normalization: lowercase, collapse whitespace, strip accents."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    # Strip accents (e.g. é → e) but keep the base characters
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def check_input(message: str, blocked_keywords: list[str]) -> tuple[bool, str | None]:
    """Check user input against blocked keywords.

    Returns:
        (passed, reason) — passed=True if message is allowed,
        otherwise reason explains why it was blocked.
    """
    normalized = normalize(message)

    for keyword in blocked_keywords:
        if keyword.lower() in normalized:
            return False, f"Blocked: message contains forbidden keyword '{keyword}'"

    return True, None
