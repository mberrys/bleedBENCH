"""Inventory the raw corpus: hash every file, extract archives safely, mark exact duplicates.

Output: _private/inventory.jsonl, one record per file (including files extracted from zips).
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath

from ..config import CORPUS, private_dir

PRINT_EXT = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_ZIP_DEPTH = 4
MAX_MEMBER_BYTES = 2 * 1024**3


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _safe_member(name: str) -> PurePosixPath | None:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.name:
        return None
    return p


def extract_zip(zpath: Path, out_root: Path, depth: int = 0) -> list[tuple[Path, str]]:
    """Extract one archive (and nested archives) under out_root/<sha12>/. Returns (path, origin)."""
    if depth > MAX_ZIP_DEPTH:
        return []
    zsha = sha256_file(zpath)
    dest = out_root / zsha[:12]
    found: list[tuple[Path, str]] = []
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.file_size > MAX_MEMBER_BYTES:
                continue
            rel = _safe_member(info.filename)
            if rel is None or rel.name.startswith("._") or "__MACOSX" in rel.parts:
                continue
            target = dest.joinpath(*rel.parts)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    for chunk in iter(lambda: src.read(1 << 20), b""):
                        dst.write(chunk)
            origin = f"zip:{zsha[:12]}"
            if target.suffix.lower() == ".zip":
                found.append((target, origin))
                found.extend(extract_zip(target, out_root, depth + 1))
            else:
                found.append((target, origin))
    return found


def build(corpus: Path = CORPUS) -> list[dict]:
    unz = private_dir("unzipped")
    files: list[tuple[Path, str]] = []
    for p in sorted(corpus.rglob("*")):
        if p.is_file():
            files.append((p, "corpus"))
            if p.suffix.lower() == ".zip":
                files.extend(extract_zip(p, unz))
    records, first_by_sha = [], {}
    for p, origin in files:
        base = corpus if origin == "corpus" else unz
        rel = nfc(p.relative_to(base).as_posix())
        sha = sha256_file(p)
        rec = {
            "sha256": sha,
            "relpath": rel,
            "origin": origin,
            "ext": p.suffix.lower(),
            "bytes": p.stat().st_size,
            "abspath": str(p),
            "dup_of": first_by_sha.get(sha),
        }
        first_by_sha.setdefault(sha, rel)
        records.append(rec)
    out = private_dir() / "inventory.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return records


def load() -> list[dict]:
    path = private_dir() / "inventory.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]
