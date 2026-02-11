"""Output filter defense — detects the secret in LLM responses.

Intentionally bypassable: only checks direct match, whitespace-normalized,
and reversed string. Misses character-by-character spelling, NATO alphabet,
acrostics, math encoding, etc.
"""

import re


def normalize_ws(text: str) -> str:
    """Collapse all whitespace to single spaces, lowercase."""
    return re.sub(r"\s+", " ", text.lower().strip())


def check_output(response: str, secret: str) -> tuple[bool, str | None]:
    """Check if the LLM response contains the secret.

    Returns:
        (passed, reason) — passed=True if response is safe to send,
        otherwise reason explains the block.
    """
    resp_normalized = normalize_ws(response)
    secret_normalized = normalize_ws(secret)

    # Direct match
    if secret_normalized in resp_normalized:
        return False, "Response blocked: secret detected in output."

    # Check without separators (e.g. "4532 7891 2345 6078" → "4532789123456078")
    secret_stripped = re.sub(r"[\s\-_.]", "", secret.lower())
    resp_stripped = re.sub(r"[\s\-_.]", "", response.lower())
    if secret_stripped in resp_stripped:
        return False, "Response blocked: secret detected in output (stripped separators)."

    # Reversed
    if secret_normalized[::-1] in resp_normalized:
        return False, "Response blocked: secret detected in output (reversed)."

    return True, None
