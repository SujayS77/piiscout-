import pytest

from piiscout import verhoeff


def test_known_vector():
    # Standard published Verhoeff example: "236" -> check digit 3.
    assert verhoeff.check_digit("236") == 3
    assert verhoeff.is_valid("2363")


def test_detects_single_digit_error():
    assert not verhoeff.is_valid("2364")


def test_detects_adjacent_transposition():
    assert verhoeff.is_valid("2363")
    assert not verhoeff.is_valid("2336")


def test_rejects_non_digits():
    assert not verhoeff.is_valid("23a3")
    with pytest.raises(ValueError):
        verhoeff.check_digit("23a")
