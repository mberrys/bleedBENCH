"""Pre-commit guard: refuse to commit corpus-derived material.

Checks the staged file list (or paths given on the command line) for:
  - anything under _corpus/ or _private/ or runs/
  - images, PDFs, archives, model weights
  - files over 2 MB
  - private tokens (client names etc.) listed in _private/tokens.txt, one per line, if present

Usage:  python tools/check_no_private.py            # staged files
        python tools/check_no_private.py PATH...    # explicit files
Exit 1 on any violation. Stdlib only.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BAD_PREFIX = ("_corpus/", "_private/", "runs/", ".venv/")
BAD_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".pdf", ".zip", ".pptx",
           ".ckpt", ".pt", ".pth", ".safetensors", ".onnx", ".npy", ".npz"}
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
            if len(t.strip()) >= 4 and not t.startswith("#")]


def check(paths: list[str]) -> list[str]:
    errs, toks = [], tokens()
    for rel in paths:
        norm = rel.replace("\\", "/")
        p = REPO / norm
        if norm.startswith(BAD_PREFIX):
            errs.append(f"{rel}: private directory")
            continue
        if p.suffix.lower() in BAD_EXT:
            errs.append(f"{rel}: binary/image/document type {p.suffix}")
        if p.exists() and p.stat().st_size > MAX_BYTES:
            errs.append(f"{rel}: larger than 2 MB")
        if toks and p.exists() and p.suffix.lower() in {".md", ".json", ".csv", ".py", ".txt", ".toml"}:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            hit = [t for t in toks if t in text or t in norm.lower()]
            if hit:
                errs.append(f"{rel}: contains {len(hit)} private token(s)")
    return errs


def main(argv: list[str]) -> int:
    paths = argv or staged()
    errs = check(paths)
    for e in errs:
        print("BLOCK", e)
    print(f"checked {len(paths)} file(s): {'FAIL' if errs else 'ok'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
