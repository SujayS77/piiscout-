import pytest

from helpers import make_aadhaar

from piiscout import redact_text
from piiscout.redact import apply_redaction, hash_value, mask_value
from piiscout.scanner import scan_text
from piiscout.synthetic import generate_dataset


def test_mask_keeps_last_4_and_separators_for_aadhaar_and_phone():
    assert mask_value("2345 6789 0123", "AADHAAR") == "**** **** 0123"
    assert mask_value("+91 98765 43210", "PHONE") == "+** ***** *3210"


def test_mask_hides_everything_for_other_types():
    assert mask_value("ravi@example.com", "EMAIL") == "****@*******.***"
    assert mask_value("ABCPE1234F", "PAN") == "**********"


def test_remove_mode_deletes_value():
    assert redact_text("mail ravi@example.com now", mode="remove") == "mail  now"


def test_multiple_findings_keep_offsets_correct():
    a = make_aadhaar("23456789012")
    text = f"A {a} B ravi@example.com C 98765 43210 D"
    out = redact_text(text, mode="mask")
    assert out == f"A ********{a[-4:]} B ****@*******.*** C ***** *3210 D"
    assert "ravi" not in out and "98765" not in out
    assert out.count(" ") == text.count(" ")  # structure preserved


def test_hash_is_stable_and_normalised():
    t1 = hash_value("98765 43210", "PHONE", "key")
    assert t1 == hash_value("+919876543210", "PHONE", "key")
    assert t1 == hash_value("09876543210", "PHONE", "key")
    assert hash_value("Ravi@Example.com", "EMAIL", "key") == hash_value("ravi@example.com", "EMAIL", "key")
    assert t1.startswith("<PHONE_") and t1.endswith(">")


def test_hash_depends_on_salt_and_type():
    assert hash_value("9876543210", "PHONE", "key1") != hash_value("9876543210", "PHONE", "key2")
    assert hash_value("abc", "NAME", "k") != hash_value("abc", "EMAIL", "k")


def test_hash_mode_requires_salt():
    with pytest.raises(ValueError):
        redact_text("ravi@example.com", mode="hash")


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        apply_redaction("x", [], mode="shred")


def test_text_without_pii_unchanged():
    assert redact_text("Nothing personal here.") == "Nothing personal here."


@pytest.mark.parametrize("mode", ["mask", "hash", "remove"])
def test_redacted_text_has_no_detectable_pii_left(mode):
    """Everything the rules detect is gone; scanning the output finds nothing."""
    for rec in generate_dataset(n=300, seed=11):
        out = redact_text(rec["text"], mode=mode, salt="test-key")
        assert scan_text(out) == [], (mode, rec["text"], out)
