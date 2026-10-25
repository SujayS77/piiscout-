import pytest

from piiscout.evaluate import evaluate_method, prf


def test_prf_math():
    p, r, f1 = prf(tp=8, fp=2, fn=2)
    assert p == pytest.approx(0.8)
    assert r == pytest.approx(0.8)
    assert f1 == pytest.approx(0.8)


def test_prf_handles_zero_division():
    assert prf(0, 0, 0) == (0.0, 0.0, 0.0)
    assert prf(0, 3, 0) == (0.0, 0.0, 0.0)


def _record(text, entities):
    return {"id": 0, "text": text, "entities": entities}


def test_evaluate_method_perfect_and_miss():
    text = "mail ravi@example.com or call 98765 43210"
    email = {"type": "EMAIL", "start": 5, "end": 21, "value": "ravi@example.com", "hard": False}
    phone = {"type": "PHONE", "start": 30, "end": 41, "value": "98765 43210", "hard": False}
    perfect = evaluate_method([_record(text, [email, phone])], "rule")
    assert perfect["overall"] == (1.0, 1.0, 1.0)

    # A labelled name the rules cannot find lowers recall but not precision.
    name = {"type": "NAME", "start": 0, "end": 4, "value": "mail", "hard": True}
    missed = evaluate_method([_record(text, [email, phone, name])], "rule")
    p, r, _ = missed["overall"]
    assert p == 1.0 and r == pytest.approx(2 / 3)
    assert missed["hard_recall"] == 0.0


def test_exact_span_required():
    # Prediction overlaps the label but not exactly -> counts as FP and FN.
    text = "(+91) 98765 43210"
    phone = {"type": "PHONE", "start": 0, "end": 17, "value": text, "hard": True}
    res = evaluate_method([_record(text, [phone])], "rule")
    assert res["counts"]["PHONE"] == {"tp": 0, "fp": 1, "fn": 1}
