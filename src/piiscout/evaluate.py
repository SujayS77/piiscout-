"""Measure how well each detection method finds the labelled PII.

Scoring is strict: a prediction counts as correct only if its type AND exact
start/end position match a labelled item.
  precision = correct / everything the method reported   (how clean are alerts)
  recall    = correct / everything that was really there (how much was caught)
  F1        = harmonic mean of the two (one number that punishes either being low)

Usage:
    python -m piiscout.evaluate data/synthetic_test.jsonl
    python -m piiscout.evaluate data/synthetic_test.jsonl --methods rule hybrid
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict

from .scanner import METHODS, scan_text
from .synthetic import ENTITY_TYPES, read_jsonl


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def evaluate_method(records: list[dict], method: str) -> dict:
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    hard_total = hard_found = 0
    start = time.perf_counter()
    for rec in records:
        gold = {(e["type"], e["start"], e["end"]): e for e in rec["entities"]}
        pred = {(f.pii_type, f.start, f.end) for f in scan_text(rec["text"], method=method)}
        for key in pred - gold.keys():
            counts[key[0]]["fp"] += 1
        for key, ent in gold.items():
            if key in pred:
                counts[key[0]]["tp"] += 1
            else:
                counts[key[0]]["fn"] += 1
            if ent["hard"]:
                hard_total += 1
                hard_found += key in pred
    seconds = time.perf_counter() - start

    per_type = {t: prf(**counts[t]) for t in ENTITY_TYPES}
    total = {k: sum(counts[t][k] for t in ENTITY_TYPES) for k in ("tp", "fp", "fn")}
    return {
        "method": method,
        "per_type": per_type,
        "counts": {t: dict(counts[t]) for t in ENTITY_TYPES},
        "overall": prf(**total),
        "hard_recall": hard_found / hard_total if hard_total else 0.0,
        "ms_per_sample": 1000 * seconds / len(records),
    }


def format_report(results: list[dict], n_samples: int, n_entities: int) -> str:
    out = [f"Evaluation on {n_samples} samples containing {n_entities} labelled PII items.", ""]
    out.append("Overall (micro-averaged over every PII item)")
    out.append("")
    out.append("| Method | Precision | Recall | F1 | Recall on hard variants | ms / sample |")
    out.append("|---|---|---|---|---|---|")
    for r in results:
        p, rc, f1 = r["overall"]
        out.append(f"| {r['method']} | {p:.3f} | {rc:.3f} | {f1:.3f} | {r['hard_recall']:.3f} | {r['ms_per_sample']:.2f} |")
    out += ["", "Per type (precision / recall / F1)", ""]
    out.append("| Type | " + " | ".join(r["method"] for r in results) + " |")
    out.append("|---|" + "---|" * len(results))
    for t in ENTITY_TYPES:
        cells = []
        for r in results:
            p, rc, f1 = r["per_type"][t]
            cells.append(f"{p:.2f} / {rc:.2f} / {f1:.2f}")
        out.append(f"| {t} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate PII detection methods.")
    ap.add_argument("dataset", help="path to a .jsonl file from piiscout.synthetic")
    ap.add_argument("--methods", nargs="+", default=list(METHODS), choices=METHODS)
    ap.add_argument("--out", help="optional path to save the report as Markdown")
    args = ap.parse_args()

    records = read_jsonl(args.dataset)
    n_entities = sum(len(r["entities"]) for r in records)
    results = [evaluate_method(records, m) for m in args.methods]
    report = format_report(results, len(records), n_entities)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
