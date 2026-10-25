# piiscout

An open source Python tool that finds personal data (PII) in text and datasets so it can be masked before the data is shared. Built for Indian identifiers: Aadhaar, PAN, mobile numbers, UPI IDs, and email addresses.

> **Status:** early development (v0.1). The rule-based detector is working. The NER detector, CLI and redaction are in progress.

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
git clone https://github.com/<your-username>/piiscout.git
cd piiscout
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

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

## Known limitations

- PAN detection is uppercase only.
- UPI detection depends on a built-in list of handles; unknown handles are missed.
- Person names are not detected by the rule-based approach (planned: NER detector).

## Roadmap

- [x] Rule-based detectors with validation
- [ ] NER-based detector (spaCy) for names
- [ ] Evaluation on a labelled synthetic dataset (precision / recall / F1)
- [ ] CSV and JSON scanning
- [ ] Redaction modes: mask, hash, remove
- [ ] Command-line interface
- [ ] Scan report

## License

MIT. See [LICENSE](LICENSE).
