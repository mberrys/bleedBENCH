"""Exclusion rules. Generic rules live here; file-specific entries (which may contain personal or
client names) live only in the private file _private/exclusions.json:

    {"globs": [{"pattern": "*some name*", "reason": "personal_name"}, ...]}

A file is excluded if any rule fires. Reasons are recorded, never silently dropped.
"""
from __future__ import annotations

import fnmatch
import json
import re

from ..config import private_dir
from .inventory import PRINT_EXT

GENERIC_RULES: list[tuple[str, re.Pattern]] = [
    ("unrelated_dataset", re.compile(r"(^|/)(connections_|build_connections)", re.I)),
    ("phone_photo", re.compile(r"(^|/)IMG_\d+", re.I)),
    ("ai_generated", re.compile(r"chatgpt image|dall[-·]?e|midjourney", re.I)),
    ("sensitive_form", re.compile(
        r"auth(ori[sz]ation)?[ _-]*form|fd-?258|fingerprint|agreement|benefit[ _-]*guide|"
        r"name[ _-]*badge|birthday|binder|invoice|\bw-?9\b|contract|consent|waiver|payroll|"
        r"resume|application[ _-]*form", re.I)),
    ("notion_export_meta", re.compile(r"(^|/)(Print Jobs|Printing Order Tracker)[^/]*\.(csv|pdf)$", re.I)),
]


def private_globs() -> list[dict]:
    f = private_dir() / "exclusions.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8")).get("globs", [])


def reasons(rec: dict, globs: list[dict] | None = None) -> list[str]:
    globs = private_globs() if globs is None else globs
    rel = rec["relpath"]
    out = []
    if rec["ext"] not in PRINT_EXT:
        out.append("non_print_type")
    if rec.get("dup_of"):
        out.append("exact_duplicate")
    for name, rx in GENERIC_RULES:
        if rx.search(rel):
            out.append(name)
    low = rel.lower()
    for g in globs:
        if fnmatch.fnmatch(low, g["pattern"].lower()):
            out.append(g.get("reason", "private_rule"))
    return sorted(set(out))
