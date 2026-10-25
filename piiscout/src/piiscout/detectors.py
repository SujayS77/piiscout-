"""Rule-based PII detectors (Solution 1 in the project comparison).

Each detector takes a string and yields `Finding` objects. A detector is a
regular expression to find candidates, plus a validation step to throw away
candidates that only look like the real thing. Regex finds, validation decides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from . import verhoeff


@dataclass(frozen=True)
class Finding:
    """One piece of PII found in a text."""

    pii_type: str  # e.g. "AADHAAR"
    value: str  # the exact text matched
    start: int  # start offset in the scanned text
    end: int  # end offset (exclusive)
    detector: str = "rule"  # which approach found it ("rule" or "ner")


# --- Aadhaar -----------------------------------------------------------------
# 12 digits, first digit 2-9, optionally grouped 4-4-4 with the same separator
# (space or hyphen) used both times. Candidates must pass the Verhoeff check.
_AADHAAR_RE = re.compile(r"(?<!\d)[2-9]\d{3}([ -]?)\d{4}\1\d{4}(?!\d)")


def detect_aadhaar(text: str) -> Iterator[Finding]:
    for m in _AADHAAR_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if verhoeff.is_valid(digits):
            yield Finding("AADHAAR", m.group(), m.start(), m.end())


# --- PAN ---------------------------------------------------------------------
# Format: 5 letters, 4 digits, 1 letter. The 4th letter encodes the holder type
# (P person, C company, H HUF, F firm, A association, T trust, B body of
# individuals, L local authority, J artificial juridical person, G government).
_PAN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Za-z0-9])")
_PAN_HOLDER_TYPES = set("PCHFATBLJG")


def detect_pan(text: str) -> Iterator[Finding]:
    for m in _PAN_RE.finditer(text):
        if m.group()[3] in _PAN_HOLDER_TYPES:
            yield Finding("PAN", m.group(), m.start(), m.end())


# --- Email -------------------------------------------------------------------
_EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])"
)


def detect_email(text: str) -> Iterator[Finding]:
    for m in _EMAIL_RE.finditer(text):
        yield Finding("EMAIL", m.group(), m.start(), m.end())


# --- UPI ID ------------------------------------------------------------------
# Looks like an email without a dot after the "@" (name@okaxis). Because many
# strings look like that, we only accept handles from a known list of UPI
# providers. Trade-off: fewer false positives, but a new or rare handle is
# missed until it is added to the list.
_UPI_HANDLES = {
    "ybl", "ibl", "axl", "okaxis", "oksbi", "okhdfcbank", "okicici",
    "paytm", "upi", "apl", "sbi", "hdfcbank", "icici", "axisbank",
    "pnb", "fbl", "waicici", "wahdfcbank", "waaxis", "wasbi", "ikwik",
    "freecharge", "jupiteraxis", "airtel", "postbank", "barodampay",
}
_UPI_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._-]{2,256}@([A-Za-z][A-Za-z0-9]{1,63})(?!\w|\.\w)"
)


def detect_upi(text: str) -> Iterator[Finding]:
    for m in _UPI_RE.finditer(text):
        if m.group(1).lower() in _UPI_HANDLES:
            yield Finding("UPI", m.group(), m.start(), m.end())


# --- Indian mobile phone -----------------------------------------------------
# 10 digits starting with 6-9, optionally written as 5+5, with an optional
# +91 / 91 / 0 prefix.
_PHONE_RE = re.compile(
    r"(?<![\w+])(?:(?:\+91|91|0)[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)"
)


def detect_phone(text: str) -> Iterator[Finding]:
    for m in _PHONE_RE.finditer(text):
        yield Finding("PHONE", m.group(), m.start(), m.end())
