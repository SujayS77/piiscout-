"""piiscout: detect and redact personal data (PII) in text and datasets."""

from .detectors import Finding
from .scanner import scan_text

__all__ = ["Finding", "scan_text"]
__version__ = "0.1.0"
