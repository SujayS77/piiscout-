"""piiscout: detect and redact personal data (PII) in text and datasets."""

from .detectors import Finding
from .redact import redact_text
from .scanner import scan_text

__all__ = ["Finding", "scan_text", "redact_text"]
__version__ = "0.3.0"
