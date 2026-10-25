"""Generate a labelled synthetic test set for evaluating the detectors.

Why synthetic: real personal data cannot be shared or published, and an
evaluation needs ground truth (exact positions of every PII item). Generating
the text ourselves gives us both, safely and reproducibly (fixed random seed).

Why not trivially easy: a test set made only of clean examples would give the
rule-based approach a perfect score and prove nothing. So the generator also
produces
  * "hard" variants: real-world formats the rules do not handle (for example
    "(+91) 98765 43210", lowercase PAN, UPI handles outside our list, names in
    capitals or first-name-only), and
  * "hard negatives": text that looks like PII but is not (random 12-digit
    order IDs, invalid PAN-like part codes, company and city names).

All numbers are randomly generated and are not real people's identifiers.

Usage:
    python -m piiscout.synthetic --n 600 --seed 42 --out data/synthetic_test.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from . import verhoeff

FIRST_NAMES = [
    "Priya", "Rahul", "Anjali", "Amit", "Sneha", "Vikram", "Pooja", "Rohan",
    "Neha", "Arjun", "Kavya", "Siddharth", "Meera", "Karthik", "Divya",
    "Aditya", "Ritu", "Manish", "Shreya", "Nikhil", "Lakshmi", "Faizan",
    "Aisha", "Gurpreet", "Harpreet", "Tanvi", "Omkar", "Swati", "Yash", "Ishita",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Iyer", "Nair", "Reddy", "Shetty", "Kulkarni",
    "Deshmukh", "Khan", "Singh", "Gupta", "Mehta", "Joshi", "Chatterjee",
    "Banerjee", "Das", "Pillai", "Menon", "Kapoor", "Malhotra", "Bhatia",
    "Shaikh", "Fernandes", "D'Souza", "Gill", "Yadav", "Pawar", "Jadhav", "Rao",
]
EMAIL_DOMAINS = ["gmail.com", "yahoo.co.in", "outlook.com", "example.org", "mail.in", "rediffmail.com"]
UPI_HANDLES_COMMON = ["ybl", "okaxis", "oksbi", "okhdfcbank", "okicici", "paytm", "ibl", "axl"]
# Real UPI handles that the rule-based detector's built-in list does NOT contain.
UPI_HANDLES_RARE = ["kotak", "indus", "yesbank", "idfcbank", "rbl"]

ENTITY_TYPES = ("NAME", "AADHAAR", "PAN", "PHONE", "EMAIL", "UPI")
HARD_PROB = 0.15  # chance that any one entity uses a "hard" variant

POSITIVE_TEMPLATES = [
    "Customer {NAME} has registered with mobile {PHONE} and email {EMAIL}.",
    "Name: {NAME}, Aadhaar: {AADHAAR}",
    "KYC verified for {NAME}. PAN {PAN}, Aadhaar {AADHAAR}.",
    "Please send Rs 500 to {UPI} and share the screenshot.",
    "{NAME} can be contacted on {PHONE}.",
    "Refund for {NAME} will be sent to {UPI}.",
    "Applicant: {NAME} | PAN: {PAN} | Phone: {PHONE} | Email: {EMAIL}",
    "Mail the invoice to {EMAIL} and call {PHONE} if there is any issue.",
    "Dear {NAME}, your order has shipped.",
    "Employee record: {NAME}, {EMAIL}, {PHONE}",
    "Aadhaar number {AADHAAR} was submitted by {NAME} on 12 March 2026.",
    "Loan file {PAN} belongs to {NAME}; payment ID {UPI}.",
]
NEGATIVE_TEMPLATES = [
    "The quarterly report was sent to the Mumbai office.",
    "Order ID {NEGNUM12} was dispatched from the Pune warehouse.",
    "Reference number {NEGNUM10} is valid for 30 days.",
    "Part code {FAKEPAN} is out of stock.",
    "Tata Motors and Infosys announced new hiring plans.",
    "The Python script processed 4500 rows in 12 seconds.",
    "Ticket {NEGNUM12} was raised by the support team in Bengaluru.",
    "Delhi recorded a high of 34 degrees on Monday.",
]

_PLACEHOLDER = re.compile(r"(\{[A-Z0-9]+\})")


def _digits(rng: random.Random, n: int, first: str = "0123456789") -> str:
    return rng.choice(first) + "".join(rng.choice("0123456789") for _ in range(n - 1))


def make_name(rng: random.Random, hard: bool) -> str:
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    if not hard:
        return f"{first} {last}"
    return rng.choice([first, f"{first} {last}".upper(), f"{first} {last}".lower()])


def make_aadhaar(rng: random.Random, hard: bool) -> str:
    body = _digits(rng, 11, first="23456789")
    num = body + str(verhoeff.check_digit(body))
    a, b, c = num[:4], num[4:8], num[8:]
    if hard:
        return rng.choice([f"{a}.{b}.{c}", f"{a}  {b}  {c}", f"{a} {b}-{c}"])
    return rng.choice([num, f"{a} {b} {c}", f"{a}-{b}-{c}"])


def make_pan(rng: random.Random, hard: bool) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    holder = rng.choices("PCHFATBLJG", weights=[10, 2, 1, 1, 1, 1, 1, 1, 1, 1])[0]
    pan = (
        "".join(rng.choice(letters) for _ in range(3))
        + holder
        + rng.choice(letters)
        + _digits(rng, 4)
        + rng.choice(letters)
    )
    return pan.lower() if hard else pan


def make_phone(rng: random.Random, hard: bool) -> str:
    n = _digits(rng, 10, first="6789")
    a, b = n[:5], n[5:]
    if hard:
        return rng.choice([f"(+91) {a} {b}", f"{n[:3]} {n[3:6]} {n[6:]}"])
    return rng.choice([n, f"{a} {b}", f"{a}-{b}", f"+91 {a} {b}", f"+91-{a}-{b}", f"+91{n}", f"0{n}"])


def make_email(rng: random.Random, person: tuple[str, str]) -> str:
    first, last = (re.sub(r"[^a-z]", "", p.lower()) for p in person)
    local = rng.choice([f"{first}.{last}", f"{first}{last}{rng.randint(1, 99)}", f"{first[0]}{last}"])
    return f"{local}@{rng.choice(EMAIL_DOMAINS)}"


def make_upi(rng: random.Random, person: tuple[str, str], hard: bool) -> str:
    first, last = (re.sub(r"[^a-z]", "", p.lower()) for p in person)
    handle = rng.choice(UPI_HANDLES_RARE if hard else UPI_HANDLES_COMMON)
    local = rng.choice([_digits(rng, 10, first="6789"), f"{first}.{last}", f"{first}{rng.randint(1, 99)}"])
    return f"{local}@{handle}"


def make_fake_pan(rng: random.Random) -> str:
    """PAN-shaped, but the 4th letter is not a valid holder type, so not a PAN."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    bad = rng.choice("DEKMNOQRSUVWXYZ")
    return "".join(rng.choice(letters) for _ in range(3)) + bad + rng.choice(letters) + _digits(rng, 4) + rng.choice(letters)


def generate_record(rng: random.Random, idx: int) -> dict:
    negative = rng.random() < 0.2
    template = rng.choice(NEGATIVE_TEMPLATES if negative else POSITIVE_TEMPLATES)
    person = (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES))

    def hard() -> bool:
        return rng.random() < HARD_PROB

    makers = {
        "NAME": lambda h: make_name(rng, h),
        "AADHAAR": lambda h: make_aadhaar(rng, h),
        "PAN": lambda h: make_pan(rng, h),
        "PHONE": lambda h: make_phone(rng, h),
        "EMAIL": lambda h: make_email(rng, person),
        "UPI": lambda h: make_upi(rng, person, h),
    }

    text, entities = "", []
    for part in _PLACEHOLDER.split(template):
        key = part[1:-1] if _PLACEHOLDER.fullmatch(part) else None
        if key in makers:
            is_hard = False if key == "EMAIL" else hard()
            value = makers[key](is_hard)
            entities.append(
                {"type": key, "start": len(text), "end": len(text) + len(value), "value": value, "hard": is_hard}
            )
            text += value
        elif key == "NEGNUM12":
            text += _digits(rng, 12, first="23456789")  # random: ~1 in 10 passes the checksum by chance
        elif key == "NEGNUM10":
            text += _digits(rng, 10)  # may start 6-9 and so look like a phone number
        elif key == "FAKEPAN":
            text += make_fake_pan(rng)
        else:
            text += part
    return {"id": idx, "text": text, "entities": entities}


def generate_dataset(n: int = 600, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    return [generate_record(rng, i) for i in range(n)]


def write_jsonl(records: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a synthetic labelled PII test set.")
    ap.add_argument("--n", type=int, default=600, help="number of text samples")
    ap.add_argument("--seed", type=int, default=42, help="random seed (same seed = same data)")
    ap.add_argument("--out", default="data/synthetic_test.jsonl")
    args = ap.parse_args()
    records = generate_dataset(args.n, args.seed)
    write_jsonl(records, args.out)
    total = sum(len(r["entities"]) for r in records)
    print(f"Wrote {len(records)} samples ({total} labelled PII items) to {args.out}")


if __name__ == "__main__":
    main()
