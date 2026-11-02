import pytest

from bleedbench.privacy import ExportViolation, hid, init_salt, validate_export


def test_export_rejects_small_cells_paths_and_names():
    validate_export({"p": 0.5, "n_families": 5, "ci95": [0.1, 0.9]})
    validate_export({"suppressed": True})
    validate_export({"texture": {"p": 0.1}, "typography": 1})          # whole-word key match only
    for bad in ({"n_families": 4, "p": 0.1}, {"x": "C:\\corpus\\a.pdf"}, {"client": "x"},
                {"x": "free text, with punctuation!"}, {"filename": "a"}, {"client_name": "a"}):
        with pytest.raises(ExportViolation):
            validate_export(bad)


def test_hid_stable_and_salted(tmp_path):
    s = init_salt(tmp_path / "salt")
    a = hid("family", "x", salt_path=s)
    assert a == hid("family", "x", salt_path=s) and a.startswith("fam_")
    s2 = init_salt(tmp_path / "salt2")
    assert hid("family", "x", salt_path=s2) != a


def test_check_no_private_blocks(tmp_path):
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("cnp", pathlib.Path(__file__).parent.parent / "tools" / "check_no_private.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    errs = m.check(["_corpus/x.pdf", "_private/labels.jsonl", "bleedbench/a.png", "README.md"])
    assert len(errs) == 3
