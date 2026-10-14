"""PII protection for comments (pure). We never store commenter names, handles, avatars or profile URLs.

author_hash = HMAC-SHA256(pepper, "youtube:" + authorChannelId) — pseudonymous, not reversible without the pepper.
redact() removes phone numbers (UAE + international), emails, Emirates ID numbers, URLs and @mentions.
"""

from __future__ import annotations

import hashlib
import hmac
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
EMIRATES_ID = re.compile(r"\b784[-\s]?\d{4}[-\s]?\d{7}[-\s]?\d\b")
URL = re.compile(r"(?:https?://|www\.)\S+|\b(?:wa\.me|t\.me|bit\.ly|linktr\.ee)/\S+", re.I)
PHONE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}")
MENTION = re.compile(r"(?<![\w@])@[\w.\-]{2,}")


def author_hash(pepper: bytes, author_channel_id: str | None) -> str | None:
    if not author_channel_id:
        return None
    return hmac.new(pepper, f"youtube:{author_channel_id}".encode(), hashlib.sha256).hexdigest()


def _phone_like(m: re.Match[str]) -> bool:
    digits = re.sub(r"\D", "", m.group(0))
    return 8 <= len(digits) <= 15


def redact(text: str | None) -> tuple[str, int]:
    """Returns (redacted_text, number_of_redactions). Order matters: IDs and emails before phones."""
    s = text or ""
    n = 0
    for pat, token in ((EMIRATES_ID, "[id]"), (EMAIL, "[email]"), (URL, "[url]"), (MENTION, "[handle]")):
        s, k = pat.subn(token, s)
        n += k

    def phone_sub(m: re.Match[str]) -> str:
        nonlocal n
        if _phone_like(m):
            n += 1
            return "[phone]"
        return m.group(0)

    s = PHONE.sub(phone_sub, s)
    return s, n
