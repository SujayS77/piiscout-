# piiscout

An open source Python tool that finds personal data (PII) in text and datasets so it can be masked before the data is shared. Built for Indian identifiers: Aadhaar, PAN, mobile numbers, UPI IDs, and email addresses.

> **Status:** early development (v0.3). Detection (rules + NER), file scanning, three redaction modes, a command-line tool and an evaluation harness all work.

## Why

Datasets shared for analytics, ML or testing often contain personal data nobody meant to share. Most existing tools are cloud-based, paid, or built around US/EU identifiers. `piiscout` runs locally, is free, and understands Indian formats.

## How detection works

Each detector uses a regular expression to find candidates, then a validation step to reject lookalikes:

| Type | Candidate rule | Validation |
|---|---|---|
| Aadhaar | 12 digits, first digit 2-9, optional 4-4-4 grouping | Verhoeff checksum |
| PAN | `AAAAA9999A` shape | 4th letter must be a valid holder type |
| Email | standard address pattern | domain needs a dot and TLD |
| UPI ID | `name@handle` | handle must be a known UPI provider |
| Phone | 10-digit mobile starting 6-9, optional `+91`/`91`/`0` | length and start digit |

When two matches overlap, the stricter format wins (Aadhaar > PAN > UPI > Email > Phone).

## Install (development)

```bash
git clone https://github.com/SujayS77/piiscout-.git
cd piiscout-
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev,ner]"
python -m spacy download en_core_web_sm
pytest
```

The rule-based detectors have no dependencies. The `ner` extra installs spaCy for name detection. (The NER tests skip themselves if spaCy or its model is missing.)

## Usage

```python
from piiscout import scan_text

text = "Contact Ravi at ravi@example.com or +91 98765 43210"
for f in scan_text(text):
    print(f.pii_type, f.value, f.start, f.end)
# EMAIL ravi@example.com 16 32
# PHONE +91 98765 43210 36 51
```

Restrict to certain types: `scan_text(text, types=["EMAIL"])`.

Choose a detection method with `method=`:

| method | what runs |
|---|---|
| `"rule"` (default) | regex + validation detectors; fast, no dependencies |
| `"ner"` | spaCy named-entity model, person names only |
| `"hybrid"` | both; when matches overlap the strict rule match wins |

```python
scan_text("Priya Sharma, PAN ABCPE1234F", method="hybrid")
```

## Command line

```bash
piiscout scan examples/sample_customers.csv
piiscout redact examples/sample_customers.csv -o masked.csv --mode mask
piiscout redact examples/sample_customers.csv -o hashed.csv --mode hash --salt "my-secret" --method hybrid
```

Supported files: `.csv`, `.tsv`, `.json`, `.jsonl`, `.txt`, `.log`, `.md`. Only string values are scanned; headers and JSON keys are left alone.

| Command / flag | Meaning |
|---|---|
| `scan FILE` | report PII counts by type and by column / JSON path (never prints the values) |
| `scan --fail-on-pii` | exit code 1 if anything is found, for use in CI checks |
| `redact FILE -o OUT` | write a redacted copy; refuses to overwrite unless `--force` |
| `--mode mask` | `*` over letters and digits, separators kept, last 4 digits of Aadhaar and phone shown |
| `--mode hash` | keyed hash token such as `<EMAIL_3f9a1c07be>`; same value gives the same token, so joins still work |
| `--mode remove` | delete the value |
| `--salt` | secret key for hash mode (or set the `PIISCOUT_SALT` environment variable, which keeps it out of shell history) |
| `--method rule\|ner\|hybrid` | detection method; `hybrid` is needed to find names |
| `--types AADHAAR PAN ...` | only look for these types |

Example output of `piiscout scan examples/sample_customers.csv` (the file contains only randomly generated fake data):

```
File: sample_customers.csv (csv)
Values scanned: 56   Values containing PII: 32
PII items found: 32
By type:
  PHONE    8
  EMAIL    8
  AADHAAR  8
  PAN      8
```

**Why a keyed hash:** a mobile number has only about 4 billion possibilities, so an unkeyed hash could be reversed by hashing every number. Without the secret salt that attack does not work. Keep the salt private, and use the same salt across files if you want tokens to match between them.

**Important:** names are only detected with `--method hybrid`. In the default rule mode a `name` column is left untouched, and the tool prints a reminder.

## Evaluation

Real personal data cannot be published, so the project generates a labelled synthetic test set (fixed seed, so it is reproducible) that includes hard formats and look-alike negatives, then scores each method with exact-match precision, recall and F1.

```bash
python -m piiscout.synthetic --n 600 --seed 42 --out data/synthetic_test.jsonl
python -m piiscout.evaluate data/synthetic_test.jsonl --out results.md
```

Caveats: the test set is synthetic and the share of "hard" variants (15% per item) is a design choice, so treat the numbers as a comparison between methods on this set, not as accuracy on real-world data.

## Known limitations

- PAN detection is uppercase only.
- UPI detection depends on a built-in list of handles; unknown handles are missed.
- Phone and Aadhaar detection only cover common formats (for example `(+91) 98765 43210` is not matched in full).
- Rules cannot detect person names. The small English spaCy model is not trained mainly on Indian names, so name recall is limited and spans can include extra words.
- Files are processed value by value. JSON is loaded fully into memory (CSV and JSONL stream row by row), and `ner`/`hybrid` is much slower than `rule` on large files.
- Redaction removes what the detectors find; anything they miss (see the evaluation recall figures) stays in the output. Check the output before sharing a dataset.
- Random 12-digit numbers pass the Aadhaar checksum about 1 time in 10, so some false positives are unavoidable without more context.

## Roadmap

- [x] Rule-based detectors with validation
- [x] NER-based detector (spaCy) for names
- [x] Evaluation on a labelled synthetic dataset (precision / recall / F1)
- [x] CSV, TSV, JSON, JSONL and text file scanning
- [x] Redaction modes: mask, hash, remove
- [x] Command-line interface
- [x] Scan report (by type and column, no values)
- [ ] Try larger spaCy models for name detection

## License

MIT. See [LICENSE](LICENSE).
