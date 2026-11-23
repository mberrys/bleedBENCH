"""Pre-commit guard: refuse to commit corpus-derived material.

Checks the staged file list (or paths given on the command line) for:
  - anything inside _corpus/, _private/, runs/ or .venv/, including nested and absolute paths
  - images, PDFs, archives, model weights, design files
  - files over 2 MB
  - private tokens (client names etc.) listed in _private/tokens.txt, one per line, if present

Staged mode reads the bytes from the git index, not the working tree, so a post-stage edit
cannot hide a violation. Explicit paths are read from disk.
Exit 1 on any violation. Stdlib only.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BAD_DIRS = {"_corpus", "_private", "runs", ".venv"}
BAD_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".webp", ".gif", ".psd", ".svg",
           ".pdf", ".zip", ".pptx", ".ckpt", ".pt", ".pth", ".safetensors", ".onnx",
           ".npy", ".npz", ".pkl"}
TEXT_EXT = {".md", ".json", ".csv", ".py", ".txt", ".toml", ".yaml", ".yml", ".cfg", ".ini",
            ".ipynb", ".rst", ".html", ".js", ".ts", ".sql", ".tex", ".log", ".sh"}
MAX_BYTES = 2 * 1024 * 1024


def staged() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def tokens() -> list[str]:
    f = REPO / "_private" / "tokens.txt"
    if not f.exists():
        return []
    return [t.strip().lower() for t in f.read_text(encoding="utf-8").splitlines()
            if t.strip() and not t.startswith("#")]


def _private_path(rel: str) -> bool:
    """True when any parent directory (or the path itself) is a private directory."""
    parts = [p for p in rel.replace("\\", "/").lower().split("/") if p not in ("", ".")]
    if parts and len(parts[0]) == 2 and parts[0][1] == ":":     # C:/... absolute path
        parts = parts[1:]
    return any(p in BAD_DIRS for p in parts[:-1]) or (bool(parts) and parts[-1] in BAD_DIRS)


def _content(rel: str, from_index: bool) -> bytes | None:
    if from_index:
        r = subprocess.run(["git", "show", f":{rel}"], cwd=REPO, capture_output=True)
        return r.stdout if r.returncode == 0 else None
    p = REPO / rel
    return p.read_bytes() if p.exists() else None


def check(paths: list[str], from_index: bool = False) -> list[str]:
    errs, toks = [], tokens()
    for rel in paths:
        norm = rel.replace("\\", "/")
        if _private_path(rel):
            errs.append(f"{rel}: private directory")
            continue
        suffix = Path(norm).suffix.lower()
        if suffix in BAD_EXT:
            errs.append(f"{rel}: binary/image/document type {suffix}")
        data = _content(rel, from_index)
        if data is None:
            continue
        if len(data) > MAX_BYTES:
            errs.append(f"{rel}: larger than 2 MB")
        if toks and suffix in TEXT_EXT:
            text = data.decode("utf-8", errors="ignore").lower()
            hit = [t for t in toks if t in text or t in norm.lower()]
            if hit:
                errs.append(f"{rel}: contains {len(hit)} private token(s)")
    return errs


def main(argv: list[str]) -> int:
    paths = argv or staged()
    errs = check(paths, from_index=not argv)
    for e in errs:
        print("BLOCK", e)
    print(f"checked {len(paths)} file(s): {'FAIL' if errs else 'ok'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
