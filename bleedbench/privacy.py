"""Hashed identifiers and the aggregate export allowlist (SPEC §3.3 export contract)."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from pathlib import Path
from typing import Any

from .config import SALT_PATH

K_ANON_FAMILIES = 5


class MissingSalt(RuntimeError):
    pass


def init_salt(path: Path = SALT_PATH) -> Path:
    """Create the per-installation salt once. It lives outside the repo and is never exported."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32))
    return path


def _salt(path: Path = SALT_PATH) -> bytes:
    if not path.exists():
        raise MissingSalt(f"salt not found at {path}; run `bleedbench init-salt` first")
    return bytes.fromhex(path.read_text().strip())


def hid(kind: str, value: str, n: int = 16, salt_path: Path = SALT_PATH) -> str:
    """HMAC-SHA256 id, e.g. hid('family', 'client-x') -> 'fam_3f2a...'."""
    mac = hmac.new(_salt(salt_path), f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()
    prefix = {"family": "fam", "case": "case", "page": "pg", "file": "f"}.get(kind, kind[:4])
    return f"{prefix}_{mac[:n]}"


# --- export validation -------------------------------------------------------------------------

_FORBIDDEN_KEY = re.compile(r"(^|_)(path|file|filename|name|client|text|url|caption|title|email|phone)(_|$)", re.I)
_PATHLIKE = re.compile(r"([A-Za-z]:\\|/|\\|\.pdf|\.png|\.jpe?g|\.zip)", re.I)
# No whitespace: a free-text name ("John Smith") must not survive the allowlist.
_ALLOWED_STR = re.compile(r"^[A-Za-z0-9_.:+\-%<>=≥≤()/]*$")


class ExportViolation(ValueError):
    pass


def validate_export(obj: Any, where: str = "$") -> None:
    """Reject anything that is not a plain aggregate.

    Rules: no key that suggests a path/name/free text; keys and values must pass the same
    string allowlist; a suppressed cell holds exactly {"suppressed": true}; every dict that
    carries `n_families` must have it >= K_ANON_FAMILIES.
    """
    if isinstance(obj, dict):
        if obj.get("suppressed") is True:
            if set(obj) != {"suppressed"}:
                raise ExportViolation(f"{where}: suppressed cell carries extra fields {sorted(obj)}")
        elif "suppressed" in obj:
            raise ExportViolation(f"{where}: suppressed must be exactly True")
        if "n_families" in obj and not obj.get("suppressed"):
            nf = obj["n_families"]
            if not isinstance(nf, int) or nf < K_ANON_FAMILIES:
                raise ExportViolation(f"{where}: n_families={nf} < {K_ANON_FAMILIES} and not suppressed")
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ExportViolation(f"{where}: non-string key")
            if _FORBIDDEN_KEY.search(k) and k not in _KEY_ALLOW:
                raise ExportViolation(f"{where}.{k}: forbidden key")
            _check_string(k, f"{where}.<key>")
            validate_export(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            validate_export(v, f"{where}[{i}]")
    elif isinstance(obj, str):
        _check_string(obj, where)
    elif obj is None or isinstance(obj, (int, float, bool)):
        return
    else:
        raise ExportViolation(f"{where}: unsupported type {type(obj).__name__}")


def _check_string(s: str, where: str) -> None:
    if len(s) > 80 or _PATHLIKE.search(s.replace("n/a", "")) or not _ALLOWED_STR.match(s):
        raise ExportViolation(f"{where}: string not allowed in export: {s[:30]!r}")


# Keys that look sensitive by regex but are fixed vocabulary in our schema.
_KEY_ALLOW = {"filetype", "profile_name"}


def suppress(cell: dict, n_families: int) -> dict:
    """Return the cell, or a suppressed marker when it covers fewer than K families."""
    if n_families < K_ANON_FAMILIES:
        return {"suppressed": True}
    return {**cell, "n_families": n_families}


def write_export(obj: Any, path: Path) -> None:
    validate_export(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
