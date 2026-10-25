from helpers import make_aadhaar

from piiscout.detectors import (
    detect_aadhaar,
    detect_email,
    detect_pan,
    detect_phone,
    detect_upi,
)


def values(detector, text):
    return [f.value for f in detector(text)]


# --- Aadhaar ---
def test_aadhaar_valid_plain_and_grouped():
    a = make_aadhaar("23456789012")
    grouped_space = f"{a[:4]} {a[4:8]} {a[8:]}"
    grouped_dash = f"{a[:4]}-{a[4:8]}-{a[8:]}"
    assert values(detect_aadhaar, f"id {a}") == [a]
    assert values(detect_aadhaar, f"id {grouped_space}") == [grouped_space]
    assert values(detect_aadhaar, f"id {grouped_dash}") == [grouped_dash]


def test_aadhaar_rejects_bad_checksum():
    a = make_aadhaar("23456789012")
    bad = a[:-1] + str((int(a[-1]) + 1) % 10)
    assert values(detect_aadhaar, bad) == []


def test_aadhaar_rejects_leading_0_or_1():
    # Real Aadhaar numbers never start with 0 or 1.
    assert values(detect_aadhaar, "012345678901") == []
    assert values(detect_aadhaar, "123456789012") == []


def test_aadhaar_ignores_longer_digit_strings():
    a = make_aadhaar("23456789012")
    assert values(detect_aadhaar, a + "5") == []


# --- PAN ---
def test_pan_valid():
    assert values(detect_pan, "PAN: ABCPE1234F.") == ["ABCPE1234F"]


def test_pan_rejects_bad_holder_type():
    assert values(detect_pan, "ABCZE1234F") == []


def test_pan_rejects_wrong_shape():
    assert values(detect_pan, "ABCPE12345") == []
    assert values(detect_pan, "XABCPE1234F") == []


# --- Email ---
def test_email_basic():
    assert values(detect_email, "write to ravi.k+test@mail.example.co.in now") == [
        "ravi.k+test@mail.example.co.in"
    ]


def test_email_sentence_end_period_excluded():
    assert values(detect_email, "mail a@b.com.") == ["a@b.com"]


def test_email_requires_domain_dot():
    assert values(detect_email, "name@okaxis") == []


# --- UPI ---
def test_upi_known_handle():
    assert values(detect_upi, "pay ravi@okaxis please") == ["ravi@okaxis"]
    assert values(detect_upi, "9876543210@ybl") == ["9876543210@ybl"]


def test_upi_ignores_unknown_handle_and_email_domains():
    assert values(detect_upi, "ravi@randomhandle") == []
    assert values(detect_upi, "ravi@example.com") == []


# --- Phone ---
def test_phone_formats():
    for text in [
        "9876543210",
        "98765 43210",
        "98765-43210",
        "+91 98765 43210",
        "+919876543210",
        "919876543210",
        "09876543210",
    ]:
        assert values(detect_phone, f"call {text} now") == [text], text


def test_phone_rejects_wrong_start_and_length():
    assert values(detect_phone, "5876543210") == []  # must start 6-9
    assert values(detect_phone, "987654321") == []  # 9 digits
    assert values(detect_phone, "98765432101") == []  # 11 digits
