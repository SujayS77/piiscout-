from helpers import make_aadhaar

from piiscout import scan_text


def pairs(text, **kw):
    return [(f.pii_type, f.value) for f in scan_text(text, **kw)]


def test_scan_finds_all_types_in_order():
    a = make_aadhaar("23456789012")
    text = f"Ravi: {a}, ABCPE1234F, ravi@example.com, +91 98765 43210, ravi@okaxis"
    assert pairs(text) == [
        ("AADHAAR", a),
        ("PAN", "ABCPE1234F"),
        ("EMAIL", "ravi@example.com"),
        ("PHONE", "+91 98765 43210"),
        ("UPI", "ravi@okaxis"),
    ]


def test_upi_wins_over_phone_inside_it():
    assert pairs("pay 9876543210@ybl") == [("UPI", "9876543210@ybl")]


def test_types_filter():
    text = "ABCPE1234F ravi@example.com"
    assert pairs(text, types=["pan"]) == [("PAN", "ABCPE1234F")]


def test_no_pii_returns_empty():
    assert scan_text("Quarterly revenue grew 12% in 2026.") == []


def test_offsets_match_text():
    text = "mail ravi@example.com today"
    (f,) = scan_text(text)
    assert text[f.start : f.end] == f.value
