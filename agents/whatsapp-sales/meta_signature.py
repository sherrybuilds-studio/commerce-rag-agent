"""
Check Meta's X-Hub-Signature-256 header on webhook POSTs.

Meta signs each webhook request body with the app secret. The header is "sha256=" followed by the hex
HMAC-SHA256 of the raw body. A POST that fails the check did not come from Meta.
"""

import hashlib
import hmac

SIGNATURE_HEADER = "X-Hub-Signature-256"


def signature_is_valid(app_secret: str, body: bytes, header_value: str | None) -> bool:
    """Constant-time comparison of the header against the HMAC of the exact bytes received."""
    if not header_value or not header_value.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    received = header_value.removeprefix("sha256=")
    return hmac.compare_digest(expected.encode(), received.encode())
