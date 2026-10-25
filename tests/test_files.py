import csv
import json

import pytest

from helpers import make_aadhaar

from piiscout.files import format_summary, process_file

AADHAAR = make_aadhaar("23456789012")


def write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return path


def test_csv_redaction_and_summary(tmp_path):
    src = write(
        tmp_path / "in.csv",
        f"id,email,notes\n1,ravi@example.com,call 98765 43210\n2,none,{AADHAAR}\n",
    )
    out = tmp_path / "out.csv"
    s = process_file(src, out, mode="remove")
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows == [["id", "email", "notes"], ["1", "", "call "], ["2", "none", ""]]
    assert s.by_type == {"EMAIL": 1, "PHONE": 1, "AADHAAR": 1}
    assert s.by_location["email"]["EMAIL"] == 1
    assert s.cells_scanned == 6 and s.cells_with_pii == 3


def test_scan_only_writes_nothing_and_changes_nothing(tmp_path):
    src = write(tmp_path / "in.csv", "email\nravi@example.com\n")
    s = process_file(src)
    assert s.total_findings == 1
    assert list(tmp_path.iterdir()) == [src]
    assert src.read_text() == "email\nravi@example.com\n"


def test_csv_with_excel_bom_and_quoted_commas(tmp_path):
    src = write(tmp_path / "in.csv", '\ufeffname,notes\n"Rao, Priya","mail a@b.com, thanks"\n')
    out = tmp_path / "out.csv"
    process_file(src, out, mode="remove")
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == ["name", "notes"]  # BOM not carried into the header
    assert rows[1] == ["Rao, Priya", "mail , thanks"]


def test_csv_row_longer_than_header_and_empty_file(tmp_path):
    src = write(tmp_path / "in.csv", "a\nx,ravi@example.com\n")
    s = process_file(src)
    assert "column_2" in s.by_location
    empty = write(tmp_path / "empty.csv", "")
    assert process_file(empty).cells_scanned == 0


def test_tsv(tmp_path):
    src = write(tmp_path / "in.tsv", "a\tb\nravi@example.com\t5\n")
    out = tmp_path / "out.tsv"
    process_file(src, out, mode="remove")
    assert out.read_text(encoding="utf-8").splitlines() == ["a\tb", "\t5"]


def test_json_nested_keys_and_non_strings_untouched(tmp_path):
    data = {"users": [{"email": "ravi@example.com", "age": 31, "ok": True, "tags": ["call 98765 43210"]}]}
    src = write(tmp_path / "in.json", json.dumps(data))
    out = tmp_path / "out.json"
    s = process_file(src, out, mode="remove")
    got = json.loads(out.read_text(encoding="utf-8"))
    assert got == {"users": [{"email": "", "age": 31, "ok": True, "tags": ["call "]}]}
    assert set(s.by_location) == {"$.users[].email", "$.users[].tags[]"}


def test_jsonl(tmp_path):
    src = write(tmp_path / "in.jsonl", '{"m": "ravi@example.com"}\n\n{"m": "clean"}\n')
    out = tmp_path / "out.jsonl"
    s = process_file(src, out, mode="remove")
    assert [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()] == [{"m": ""}, {"m": "clean"}]
    assert s.total_findings == 1


def test_plain_text(tmp_path):
    src = write(tmp_path / "in.txt", "line1 ravi@example.com\nline2\n")
    out = tmp_path / "out.txt"
    process_file(src, out, mode="remove")
    assert out.read_text(encoding="utf-8") == "line1 \nline2\n"


def test_unsupported_extension_and_bad_arguments(tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        process_file(write(tmp_path / "in.xlsx", "x"))
    src = write(tmp_path / "in.csv", "a\n1\n")
    with pytest.raises(ValueError):
        process_file(src, tmp_path / "o.csv")  # dst without mode


def test_summary_never_contains_values(tmp_path):
    src = write(tmp_path / "in.csv", "email\nravi@example.com\n")
    text = format_summary(process_file(src), "in.csv")
    assert "ravi" not in text and "EMAIL" in text and "email" in text
