"""Per-page probe: boxes, colour, text/PII flags, GT source candidacy. No pixels are rendered here.

Output: _private/pages.jsonl (one record per PDF page or raster image) and
        _private/review/pii_queue.csv (manual review queue).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pymupdf
from PIL import Image

from ..config import private_dir
from . import exclusions, inventory

Image.MAX_IMAGE_PIXELS = None
PT = 72.0
BLEED_MIN_PT = 9.0 - 0.05          # 0.125 in, with rounding slack
MIN_RASTER_DPI = 240               # below this a raster cannot supply 300-DPI GT (V14)
STANDARD_IN = [(2, 3.5), (2.5, 2.5), (3, 5), (4, 5), (4, 6), (4, 9), (4.25, 5.5), (5, 7), (5.5, 8.5),
               (6, 9), (8, 10), (8.5, 11), (8.5, 14), (11, 17), (12, 18), (16, 20), (18, 24),
               (22, 28), (24, 36), (27, 40)]
IMPOSED_NAME = re.compile(r"(-|_|\b)imp\b|\bmany\b|n-?up|\d+up\b|gang", re.I)

# --- PII screen -------------------------------------------------------------------------------
PII_RX = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "card": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "phone": re.compile(r"(?:\(\d{3}\)\s?|\b\d{3}[-.\s])\d{3}[-.\s]\d{4}\b"),
    "dob": re.compile(r"date of birth|\bdob\b|birth ?date", re.I),
    "form": re.compile(r"social security|card ?number|expiration date|\bcvv\b|\bcvc\b|"
                       r"driver'?s licen[cs]e|signature:|cardholder|routing number|account number", re.I),
}
HARD_PII = {"ssn", "card", "dob", "form"}


def luhn(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    s = 0
    for i, x in enumerate(reversed(d)):
        if i % 2:
            x *= 2
            x -= 9 if x > 9 else 0
        s += x
    return s % 10 == 0


def pii_hits(text: str) -> dict[str, int]:
    hits = {}
    for k, rx in PII_RX.items():
        m = rx.findall(text)
        if k == "card":
            m = [x for x in m if luhn(x)]
        if m:
            hits[k] = len(m)
    return hits


# --- geometry helpers -------------------------------------------------------------------------
def _rect(r) -> list[float]:
    return [round(r.x0, 3), round(r.y0, 3), round(r.x1, 3), round(r.y1, 3)]


def _inset(outer, inner) -> list[float]:
    """Per-side distance (pt) of inner inside outer: left, top, right, bottom."""
    return [round(inner.x0 - outer.x0, 3), round(inner.y0 - outer.y0, 3),
            round(outer.x1 - inner.x1, 3), round(outer.y1 - inner.y1, 3)]


def _is_standard_plus_bleed(w_in: float, h_in: float, tol: float = 0.01) -> bool:
    for a, b in STANDARD_IN:
        for sw, sh in ((a, b), (b, a)):
            if abs(w_in - sw - 0.25) < tol and abs(h_in - sh - 0.25) < tol:
                return True
    return False


def probe_pdf(rec: dict) -> list[dict]:
    out = []
    doc = pymupdf.open(rec["abspath"])
    try:
        cat = doc.xref_object(doc.pdf_catalog())
    except Exception:
        cat = ""
    has_oi = "OutputIntents" in cat
    for i, pg in enumerate(doc):
        mb, tb, bb, cb = pg.mediabox, pg.trimbox, pg.bleedbox, pg.cropbox
        bleed = _inset(bb, tb)
        trim_eq_media = _inset(mb, tb) == [0, 0, 0, 0]
        w_in, h_in = tb.width / PT, tb.height / PT
        if min(bleed) >= BLEED_MIN_PT:
            gt = "real_bleedbox"
        elif trim_eq_media and _is_standard_plus_bleed(w_in, h_in):
            gt = "inferred_trim"          # must be verified manually before scoring (DD79)
        else:
            gt = "pseudo"
        cs = set()
        for img in pg.get_images(full=True):
            cs.add(img[5] or "?")
        try:
            page_obj = doc.xref_object(pg.xref)
        except Exception:
            page_obj = ""
        text = pg.get_text("text") or ""
        out.append({
            "page_key": f"{rec['sha256'][:16]}:{i}",
            "sha256": rec["sha256"],
            "page_index": i,
            "n_pages": doc.page_count,
            "kind": "pdf",
            "relpath": rec["relpath"],
            "rotation": pg.rotation,
            "mediabox": _rect(mb), "trimbox": _rect(tb), "bleedbox": _rect(bb), "cropbox": _rect(cb),
            "bleed_pt": bleed,
            "media_minus_trim_pt": _inset(mb, tb),
            "trim_in": [round(w_in, 4), round(h_in, 4)],
            "gt_candidate": gt,
            "img_colorspaces": sorted(cs),
            "has_separation": ("Separation" in cs) or ("/Separation" in page_obj) or ("DeviceN" in cs),
            "output_intent": has_oi,
            "text_chars": len(text.strip()),
            "n_images": len(pg.get_images()),
            "creator": (doc.metadata or {}).get("creator", "")[:24],
            "imposed_name": bool(IMPOSED_NAME.search(Path(rec["relpath"]).stem)),
            "pii": pii_hits(text),
        })
    doc.close()
    return out


def probe_raster(rec: dict) -> list[dict]:
    with Image.open(rec["abspath"]) as im:
        w, h = im.size
        dpi = im.info.get("dpi", (0, 0))[0]
        dpi = round(float(dpi)) if dpi else 0
        mode, icc = im.mode, bool(im.info.get("icc_profile"))
    dpi_inferred = False
    if dpi < MIN_RASTER_DPI:
        # Screen-default tags (0/72/96) are common on print-resolution exports: trust pixels
        # only when they match a standard trim (or trim+bleed) exactly at 300 DPI.
        wi, hi = w / 300, h / 300
        if any(abs(wi - a - e) < 0.01 and abs(hi - b - e) < 0.01
               for s in STANDARD_IN for a, b in (s, s[::-1]) for e in (0, 0.25)):
            dpi, dpi_inferred = 300, True
    w_in = w / dpi if dpi else 0.0
    h_in = h / dpi if dpi else 0.0
    low = dpi < MIN_RASTER_DPI
    return [{
        "page_key": f"{rec['sha256'][:16]}:0",
        "sha256": rec["sha256"], "page_index": 0, "n_pages": 1, "kind": "raster",
        "relpath": rec["relpath"], "rotation": 0,
        "px": [w, h], "dpi": dpi, "dpi_inferred": dpi_inferred, "mode": mode, "icc": icc,
        "trim_in": [round(w_in, 4), round(h_in, 4)],
        "gt_candidate": "none" if low else ("inferred_trim" if _is_standard_plus_bleed(w_in, h_in) else "pseudo"),
        "low_dpi": low,
        "text_chars": 0,           # no text layer: PII must be reviewed by eye
        "imposed_name": bool(IMPOSED_NAME.search(Path(rec["relpath"]).stem)),
        "pii": {},
    }]


def run() -> list[dict]:
    globs = exclusions.private_globs()
    pages: list[dict] = []
    for rec in inventory.load():
        why = exclusions.reasons(rec, globs)
        if why:
            continue
        try:
            recs = probe_pdf(rec) if rec["ext"] == ".pdf" else probe_raster(rec)
        except Exception as e:  # corrupt or unreadable: record, do not guess
            recs = [{"page_key": f"{rec['sha256'][:16]}:0", "sha256": rec["sha256"], "kind": "error",
                     "relpath": rec["relpath"], "error": type(e).__name__}]
        pages.extend(recs)
    out = private_dir() / "pages.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in pages:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    _write_review_queue(pages)
    return pages


def suggest(rec: dict) -> tuple[str, str]:
    """Suggested review decision; the human decision in decisions.csv is what counts."""
    if rec.get("kind") == "error":
        return "exclude", "unreadable"
    if rec.get("low_dpi"):
        return "exclude", "low_dpi_raster"
    hard = sorted(set(rec.get("pii", {})) & HARD_PII)
    if hard:
        return "exclude", "pii:" + "+".join(hard)
    if rec.get("kind") == "raster" or rec.get("text_chars", 0) == 0:
        return "include", "no_text_layer_check_by_eye"
    return "include", "auto_clean"


def _write_review_queue(pages: list[dict]) -> None:
    rev = private_dir("review")
    by_file: dict[str, list[dict]] = {}
    for p in pages:
        by_file.setdefault(p["sha256"], []).append(p)
    rows = []
    for sha, ps in by_file.items():
        decs = [suggest(p) for p in ps]
        dec = "exclude" if any(d == "exclude" for d, _ in decs) else "include"
        why = ";".join(sorted({w for _, w in decs}))
        pii = {}
        for p in ps:
            for k, v in p.get("pii", {}).items():
                pii[k] = pii.get(k, 0) + v
        rows.append({"sha256": sha, "relpath": ps[0]["relpath"], "n_pages": len(ps),
                     "suggested": dec, "why": why,
                     "pii": " ".join(f"{k}={v}" for k, v in sorted(pii.items())),
                     "decision": "", "note": ""})
    rows.sort(key=lambda r: (r["suggested"] != "exclude", r["relpath"].lower()))
    q = rev / "pii_queue.csv"
    old = list(csv.DictReader(open(q, encoding="utf-8-sig"))) if q.exists() else []
    with open(q, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    if old:
        from .review import merge_previous
        merge_previous(q, old)


def load() -> list[dict]:
    return [json.loads(l) for l in (private_dir() / "pages.jsonl").read_text(encoding="utf-8").splitlines() if l]
