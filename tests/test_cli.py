import pytest

from piiscout.cli import main


def make_csv(tmp_path, body="email,note\nravi@example.com,hello\n"):
    p = tmp_path / "in.csv"
    p.write_text(body, encoding="utf-8")
    return p


def test_scan_reports_without_values(tmp_path, capsys):
    assert main(["scan", str(make_csv(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "EMAIL" in out and "ravi" not in out


def test_scan_fail_on_pii(tmp_path):
    assert main(["scan", str(make_csv(tmp_path)), "--fail-on-pii"]) == 1
    clean = make_csv(tmp_path, "a\nnothing here\n")
    assert main(["scan", str(clean), "--fail-on-pii"]) == 0


def test_redact_writes_file(tmp_path, capsys):
    src, out = make_csv(tmp_path), tmp_path / "out.csv"
    assert main(["redact", str(src), "-o", str(out), "--mode", "mask"]) == 0
    assert "ravi" not in out.read_text(encoding="utf-8")
    assert "Redacted copy written" in capsys.readouterr().out


def test_redact_refuses_overwrite_and_same_file(tmp_path):
    src, out = make_csv(tmp_path), tmp_path / "out.csv"
    out.write_text("keep me")
    with pytest.raises(SystemExit) as e:
        main(["redact", str(src), "-o", str(out)])
    assert e.value.code == 2 and out.read_text() == "keep me"
    assert main(["redact", str(src), "-o", str(out), "--force"]) == 0
    with pytest.raises(SystemExit):
        main(["redact", str(src), "-o", str(src), "--force"])


def test_hash_mode_needs_salt_from_flag_or_env(tmp_path, monkeypatch):
    src, out = make_csv(tmp_path), tmp_path / "out.csv"
    monkeypatch.delenv("PIISCOUT_SALT", raising=False)
    with pytest.raises(SystemExit) as e:
        main(["redact", str(src), "-o", str(out), "--mode", "hash"])
    assert e.value.code == 2
    assert main(["redact", str(src), "-o", str(out), "--mode", "hash", "--salt", "k"]) == 0
    out.unlink()
    monkeypatch.setenv("PIISCOUT_SALT", "from-env")
    assert main(["redact", str(src), "-o", str(out), "--mode", "hash"]) == 0
    assert "<EMAIL_" in out.read_text(encoding="utf-8")


def test_missing_file_and_unsupported_type(tmp_path):
    with pytest.raises(SystemExit):
        main(["scan", str(tmp_path / "nope.csv")])
    bad = tmp_path / "x.xlsx"
    bad.write_text("x")
    assert main(["scan", str(bad)]) == 2


def test_rule_method_warns_that_names_are_not_detected(tmp_path, capsys):
    main(["scan", str(make_csv(tmp_path))])
    assert "cannot find person names" in capsys.readouterr().out
