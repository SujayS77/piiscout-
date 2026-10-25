"""Turn findings into redacted text.

Three modes, because different jobs need different trade-offs:

  mask   "*" over every letter/digit, separators kept; last 4 digits of Aadhaar
         and phone numbers stay visible (the usual masked-ID style). Good for
         human-readable output. Format and length stay recognisable.
  hash   replace with a keyed hash token like <EMAIL_3f9a1c07be>. The same
         value always gives the same token, so duplicates and joins still work
         in analysis (pseudonymisation), but the value cannot be read back.
  remove delete the value completely. Strongest, but loses all structure.

Why a *keyed* hash (HMAC with a secret salt) and not a plain SHA-256: a mobile
number has only about 4 billion possibilities, so an attacker could hash all of
them and look the token up. Without the secret key that attack does not work.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Iterable, Optional

from .detectors import Finding
from .scanner import scan_text

MODES = ("mask", "hash", "remove")
_KEEP_LAST_4 = {"AADHAAR", "PHONE"}


def mask_value(value: str, pii_type: str) -> str:
    keep = 4 if pii_type in _KEEP_LAST_4 else 0
    positions = [i for i, ch in enumerate(value) if ch.isalnum()]
    visible = set(positions[-keep:]) if keep else set()
    return "".join(
        ch if (not ch.isalnum() or i in visible) else "*" for i, ch in enumerate(value)
    )


def _normalise(value: str, pii_type: str) -> str:
    """Canonical form, so '98765 43210' and '+919876543210' hash identically."""
    if pii_type == "AADHAAR":
        return re.sub(r"\D", "", value)
    if pii_type == "PHONE":
        return re.sub(r"\D", "", value)[-10:]  # drop +91 / 91 / 0 prefix
    if pii_type == "PAN":
        return value.upper()
    if pii_type in ("EMAIL", "UPI"):
        return value.lower()
    return " ".join(value.casefold().split())  # NAME


def hash_value(value: str, pii_type: str, salt: str) -> str:
    key = salt.encode("utf-8")
    msg = f"{pii_type}:{_normalise(value, pii_type)}".encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).hexdigest()[:10]
    return f"<{pii_type}_{digest}>"


def replacement_for(finding: Finding, mode: str, salt: str = "") -> str:
    if mode == "mask":
        return mask_value(finding.value, finding.pii_type)
    if mode == "hash":
        return hash_value(finding.value, finding.pii_type, salt)
    return ""  # remove


def apply_redaction(text: str, findings: Iterable[Finding], mode: str = "mask", salt: str = "") -> str:
    """Replace each finding in `text`. Findings must not overlap (scan_text guarantees it)."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    if mode == "hash" and not salt:
        raise ValueError("hash mode needs a non-empty secret salt")
    # Work from the end of the text so earlier offsets stay valid after each edit.
    for f in sorted(findings, key=lambda f: f.start, reverse=True):
        text = text[: f.start] + replacement_for(f, mode, salt) + text[f.end :]
    return text


def redact_text(
    text: str,
    mode: str = "mask",
    salt: str = "",
    method: str = "rule",
    types: Optional[Iterable[str]] = None,
) -> str:
    """Scan `text` and return it with all PII redacted."""
    return apply_redaction(text, scan_text(text, types=types, method=method), mode, salt)
