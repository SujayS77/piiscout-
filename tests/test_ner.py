import pytest

from piiscout import scan_text


def test_invalid_method_rejected():
    with pytest.raises(ValueError):
        scan_text("hello", method="magic")


@pytest.fixture(scope="module")
def ner_ready():
    spacy = pytest.importorskip("spacy")
    try:
        spacy.load("en_core_web_sm")
    except OSError:
        pytest.skip("spaCy model en_core_web_sm is not installed")


def test_ner_finds_a_well_known_name(ner_ready):
    found = scan_text("Barack Obama met Angela Merkel in Berlin.", method="ner")
    assert {f.value for f in found} == {"Barack Obama", "Angela Merkel"}
    assert all(f.pii_type == "NAME" and f.detector == "ner" for f in found)


def test_hybrid_combines_rules_and_names(ner_ready):
    text = "Barack Obama wrote from obama@example.com"
    found = {(f.pii_type, f.value) for f in scan_text(text, method="hybrid")}
    assert ("NAME", "Barack Obama") in found
    assert ("EMAIL", "obama@example.com") in found


def test_hybrid_types_filter(ner_ready):
    text = "Barack Obama wrote from obama@example.com"
    found = scan_text(text, types=["email"], method="hybrid")
    assert [f.pii_type for f in found] == ["EMAIL"]
