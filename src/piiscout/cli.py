"""Command-line interface:  piiscout scan FILE   |   piiscout redact FILE -o OUT"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .files import format_summary, process_file
from .redact import MODES
from .scanner import METHODS


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="piiscout",
        description="Find and redact personal data (Aadhaar, PAN, phone, email, UPI, names) in files.",
    )
    ap.add_argument("--version", action="version", version=f"piiscout {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("file", help="input file (.csv .tsv .json .jsonl .txt .log .md)")
        p.add_argument("--method", choices=METHODS, default="rule",
                       help="rule (default, fast), ner (names only), hybrid (both)")
        p.add_argument("--types", nargs="+", metavar="TYPE",
                       help="only these types, e.g. AADHAAR PAN PHONE EMAIL UPI NAME")

    scan = sub.add_parser("scan", help="report where PII is, without changing anything")
    common(scan)
    scan.add_argument("--fail-on-pii", action="store_true",
                      help="exit with code 1 if any PII is found (useful in CI checks)")

    red = sub.add_parser("redact", help="write a redacted copy of the file")
    common(red)
    red.add_argument("-o", "--output", required=True, help="where to write the redacted copy")
    red.add_argument("--mode", choices=MODES, default="mask")
    red.add_argument("--salt", help="secret key for hash mode (or set env var PIISCOUT_SALT)")
    red.add_argument("--force", action="store_true", help="overwrite the output file if it exists")
    return ap


_RULE_NOTE = (
    "Note: the default 'rule' method cannot find person names. "
    "Use --method hybrid to include them (needs: pip install \"piiscout[ner]\")."
)


def _print_summary(summary, src: Path, method: str, redacted_to: Optional[str] = None) -> None:
    print(format_summary(summary, src.name, redacted_to=redacted_to))
    if method == "rule":
        print(_RULE_NOTE)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    src = Path(args.file)
    if not src.is_file():
        ap.error(f"file not found: {src}")

    try:
        if args.command == "scan":
            summary = process_file(src, method=args.method, types=args.types)
            _print_summary(summary, src, args.method)
            return 1 if (args.fail_on_pii and summary.total_findings) else 0

        out = Path(args.output)
        if out.resolve() == src.resolve():
            ap.error("output must be a different file from the input")
        if out.exists() and not args.force:
            ap.error(f"{out} already exists (use --force to overwrite)")
        salt = args.salt or os.environ.get("PIISCOUT_SALT", "")
        if args.mode == "hash" and not salt:
            ap.error("hash mode needs --salt (or the PIISCOUT_SALT environment variable)")
        summary = process_file(src, out, mode=args.mode, salt=salt, method=args.method, types=args.types)
        _print_summary(summary, src, args.method, redacted_to=str(out))
        return 0
    except (ValueError, ImportError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
