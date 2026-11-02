"""Deterministic seed derivation (SPEC §11.1): every seed is a SHA-256 of named parts."""
from __future__ import annotations

import hashlib


def derive(*parts: object, bits: int = 63) -> int:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(h[:8], "big") & ((1 << bits) - 1)


def unit(*parts: object) -> float:
    """Uniform in [0, 1) from parts."""
    return derive(*parts, bits=53) / float(1 << 53)
