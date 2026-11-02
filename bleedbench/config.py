"""Paths and geometry constants. Private locations come from env vars with repo-local defaults."""
from __future__ import annotations

import math
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CORPUS = Path(os.environ.get("BLEEDBENCH_CORPUS", REPO / "_corpus" / "_corpus"))
PRIVATE = Path(os.environ.get("BLEEDBENCH_PRIVATE", REPO / "_private"))
# Salt defaults to the gitignored private dir; set BLEEDBENCH_SALT to keep it elsewhere.
SALT_PATH = Path(os.environ.get("BLEEDBENCH_SALT", PRIVATE / "salt"))
AGGREGATES = REPO / "aggregates"

DPI = 300
BLEED_IN = 0.125
LATENT_GRID = 16


def bleed_px(dpi: int = DPI, bleed_in: float = BLEED_IN) -> int:
    """b: rounded up so the strip is never narrower than the physical bleed (SPEC §2.1)."""
    return math.ceil(round(bleed_in * dpi, 9))


def apron_px(b: int) -> int:
    """a = (-b) mod 16 (SPEC §2.3)."""
    return (-b) % LATENT_GRID


def band_px(b: int) -> int:
    """B = b + a, the unknown band width."""
    return b + apron_px(b)


def ring_scored_px(bleed_pt: float, dpi: int = DPI, b: int | None = None) -> int:
    """V12 (v2.1): only pixels whose footprint is wholly inside the BleedBox are scored."""
    b = bleed_px(dpi) if b is None else b
    return min(b, math.floor(round(bleed_pt * dpi / 72.0, 9)))


def private_dir(*parts: str) -> Path:
    p = PRIVATE.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p
