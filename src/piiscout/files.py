"""Scan and redact whole files: CSV/TSV, JSON, JSONL and plain text.

Design choices worth knowing:
  * Standard library only (csv, json). No pandas needed, so the tool installs
    anywhere and streams CSV/JSONL row by row instead of loading everything.
  * Only string values are scanned; JSON keys and CSV headers are left alone.
  * The summary records WHERE PII was found (column / JSON path) and how many,
    never the values themselves, so the report is safe to share.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from .redact import apply_redaction
from .scanner import scan_text

FORMATS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".json": "json",
    ".jsonl": "jsonl",
    ".txt": "text",
    ".log": "text",
    ".md": "text",
}


@dataclass
class ScanSummary:
    file_format: str = ""
    cells_scanned: int = 0
    cells_with_pii: int = 0
    by_type: Counter = field(default_factory=Counter)
    by_location: dict = field(default_factory=lambda: defaultdict(Counter))

    @property
    def total_findings(self) -> int:
        return sum(self.by_type.values())


class _Processor:
    """Scans (and optionally redacts) strings, recording results in a summary."""

    def __init__(self, method, types, mode, salt):
        self.method, self.types, self.mode, self.salt = method, types, mode, salt
        self.redact = mode is not None
        self.summary = ScanSummary()

    def text(self, value: str, location: str) -> str:
        s = self.summary
        s.cells_scanned += 1
        findings = scan_text(value, types=self.types, method=self.method)
        if not findings:
            return value
        s.cells_with_pii += 1
        for f in findings:
            s.by_type[f.pii_type] += 1
            s.by_location[location][f.pii_type] += 1
        return apply_redaction(value, findings, self.mode, self.salt) if self.redact else value

    def obj(self, node: Any, path: str = "$") -> Any:
        """Walk any JSON structure; scan every string value."""
        if isinstance(node, str):
            return self.text(node, path)
        if isinstance(node, list):
            return [self.obj(item, path + "[]") for item in node]
        if isinstance(node, dict):
            return {k: self.obj(v, f"{path}.{k}") for k, v in node.items()}
        return node  # numbers, booleans, null


def detect_format(path: Path) -> str:
    fmt = FORMATS.get(path.suffix.lower())
    if fmt is None:
        raise ValueError(
            f"Unsupported file type '{path.suffix}'. Supported: {', '.join(sorted(FORMATS))}"
        )
    return fmt


def process_file(
    src: str | Path,
    dst: Optional[str | Path] = None,
    *,
    mode: Optional[str] = None,
    salt: str = "",
    method: str = "rule",
    types: Optional[Iterable[str]] = None,
) -> ScanSummary:
    """Scan `src`. If `dst` and `mode` are given, also write a redacted copy to `dst`."""
    src = Path(src)
    fmt = detect_format(src)
    if (dst is None) != (mode is None):
        raise ValueError("give both dst and mode to redact, or neither to only scan")
    types = list(types) if types else None
    proc = _Processor(method, types, mode, salt)
    proc.summary.file_format = fmt
    out = open(dst, "w", encoding="utf-8", newline="") if dst else None
    try:
        if fmt in ("csv", "tsv"):
            _csv(src, out, proc, "\t" if fmt == "tsv" else ",")
        elif fmt == "json":
            data = proc.obj(json.loads(src.read_text(encoding="utf-8-sig")))
            if out:
                json.dump(data, out, ensure_ascii=False, indent=2)
                out.write("\n")
        elif fmt == "jsonl":
            with src.open(encoding="utf-8-sig") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    data = proc.obj(json.loads(line))
                    if out:
                        out.write(json.dumps(data, ensure_ascii=False) + "\n")
        else:  # plain text
            result = proc.text(src.read_text(encoding="utf-8-sig"), "text")
            if out:
                out.write(result)
    finally:
        if out:
            out.close()
    return proc.summary


def _csv(src: Path, out, proc: _Processor, delimiter: str) -> None:
    # utf-8-sig strips the BOM that Excel adds to CSV files.
    with src.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        writer = csv.writer(out, delimiter=delimiter) if out else None
        header = next(reader, None)
        if header is None:
            return
        if writer:
            writer.writerow(header)
        for row in reader:
            new_row = [
                proc.text(cell, header[i] if i < len(header) else f"column_{i + 1}")
                for i, cell in enumerate(row)
            ]
            if writer:
                writer.writerow(new_row)


def format_summary(summary: ScanSummary, filename: str, redacted_to: Optional[str] = None) -> str:
    lines = [
        f"File: {filename} ({summary.file_format})",
        f"Values scanned: {summary.cells_scanned}   Values containing PII: {summary.cells_with_pii}",
    ]
    if not summary.total_findings:
        lines.append("No PII found.")
    else:
        lines.append(f"PII items found: {summary.total_findings}")
        lines.append("By type:")
        for t, n in summary.by_type.most_common():
            lines.append(f"  {t:<8} {n}")
        lines.append("By location:")
        for loc, counts in summary.by_location.items():
            detail = ", ".join(f"{t} x{n}" for t, n in counts.most_common())
            lines.append(f"  {loc:<20} {detail}")
    if redacted_to:
        lines.append(f"Redacted copy written to: {redacted_to}")
    return "\n".join(lines)
