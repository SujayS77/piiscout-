from piiscout import verhoeff


def make_aadhaar(first_11: str) -> str:
    """Build a checksum-valid 12-digit test number (not a real person's)."""
    assert len(first_11) == 11 and first_11[0] in "23456789"
    return first_11 + str(verhoeff.check_digit(first_11))
