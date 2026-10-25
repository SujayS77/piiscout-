"""NER-based detector (Solution 2 in the project comparison).

Rules cannot recognise person names: "Priya Sharma" has no fixed format. A
Named Entity Recognition model learns from context (capitalisation, the words
around it) and tags spans as PERSON, ORG, GPE and so on. We keep only PERSON.

spaCy is an optional dependency so the rule-based part works without it:
    pip install -e ".[ner]"
    python -m spacy download en_core_web_sm
"""

from __future__ import annotations

from typing import Iterator

from .detectors import Finding

MODEL_NAME = "en_core_web_sm"
_nlp = None


def _load():
    """Load the spaCy model once and reuse it (loading takes about a second)."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
        except ImportError as exc:
            raise ImportError(
                "NER detection needs spaCy. Install it with: pip install -e \".[ner]\""
            ) from exc
        try:
            # Only the tok2vec + ner components are needed to find names;
            # switching off the rest makes it faster.
            _nlp = spacy.load(
                MODEL_NAME,
                disable=["parser", "tagger", "attribute_ruler", "lemmatizer"],
            )
        except OSError as exc:
            raise OSError(
                f"spaCy model '{MODEL_NAME}' not found. Run: "
                f"python -m spacy download {MODEL_NAME}"
            ) from exc
    return _nlp


def detect_names(text: str) -> Iterator[Finding]:
    doc = _load()(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            yield Finding("NAME", ent.text, ent.start_char, ent.end_char, detector="ner")
