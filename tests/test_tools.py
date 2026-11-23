"""check_no_private: path normalisation and the widened extension set."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("check_no_private", ROOT / "tools" / "check_no_private.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_private_paths_cover_case_absolute_and_nested():
    m = _load()
    for p in ["_private/x.png", "./_private/x", "_Private/x", "C:/repo/_private/x", "a/runs/b.csv"]:
        assert m._private_path(p), p


def test_private_paths_leave_normal_files_alone():
    m = _load()
    for p in ["bleedbench/core.py", "docs/runs.md", "tools/check_no_private.py"]:
        assert not m._private_path(p), p


def test_binary_types_include_the_extended_set():
    m = _load()
    for ext in [".webp", ".gif", ".psd", ".svg", ".pkl"]:
        assert ext in m.BAD_EXT, ext


def test_text_extensions_cover_more_than_six():
    m = _load()
    for ext in [".yaml", ".yml", ".ini", ".ipynb", ".sql"]:
        assert ext in m.TEXT_EXT, ext
