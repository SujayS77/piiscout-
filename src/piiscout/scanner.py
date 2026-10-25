"""Run all detectors on a text and resolve overlapping matches."""

from __future__ import annotations

from typing import Callable, Iterable, Iterator, Optional

from .detectors import (
    Finding,
    detect_aadhaar,
    detect_email,
    detect_pan,
    detect_phone,
    detect_upi,
)

# Order matters: earlier = higher priority when two matches overlap.
# Strict, validated formats come first, loose ones last. Example: in
# "9876543210@ybl" the UPI match must win over the phone number inside it.
DETECTORS: list[tuple[str, Callable[[str], Iterator[Finding]]]] = [
    ("AADHAAR", detect_aadhaar),
    ("PAN", detect_pan),
    ("UPI", detect_upi),
    ("EMAIL", detect_email),
    ("PHONE", detect_phone),
]


METHODS = ("rule", "ner", "hybrid")


def _detectors_for(method: str) -> list[tuple[str, Callable[[str], Iterator[Finding]]]]:
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    if method == "rule":
        return DETECTORS
    from .ner import detect_names  # imported lazily: spaCy is optional

    if method == "ner":
        return [("NAME", detect_names)]
    # hybrid: rules first, names last, so a strict rule match wins any overlap.
    return DETECTORS + [("NAME", detect_names)]


def scan_text(
    text: str,
    types: Optional[Iterable[str]] = None,
    method: str = "rule",
) -> list[Finding]:
    """Return non-overlapping findings in `text`, sorted by position.

    `types` optionally restricts the scan, e.g. ["AADHAAR", "PAN"].
    `method` is "rule" (default), "ner" (names only) or "hybrid" (both).
    """
    wanted = {t.upper() for t in types} if types else None
    candidates: list[tuple[int, Finding]] = []
    for priority, (name, detector) in enumerate(_detectors_for(method)):
        if wanted is not None and name not in wanted:
            continue
        for finding in detector(text):
            candidates.append((priority, finding))

    # Highest priority first, then longest match, then earliest.
    candidates.sort(key=lambda pf: (pf[0], -(pf[1].end - pf[1].start), pf[1].start))

    kept: list[Finding] = []
    for _, f in candidates:
        if all(f.end <= k.start or f.start >= k.end for k in kept):
            kept.append(f)
    return sorted(kept, key=lambda f: f.start)
