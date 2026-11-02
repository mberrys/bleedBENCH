"""Vector census from the PDF display list (PyMuPDF bbox log): material per edge and crop marks.

Bounding boxes are approximate for non-rectangular paths; this is a census instrument, recorded
with its method, not a pixel-exact label.
"""
from __future__ import annotations

import collections

import pymupdf

from ..geometry import EDGES

_MATERIAL = {
    "fill-image": "image", "fill-imgmask": "image",
    "fill-shade": "gradient",
    "fill-path": "flat",
    "stroke-path": "stroke",
    "fill-text": "text", "stroke-text": "text",
}
N_SAMPLES = 24


def _log(page: pymupdf.Page) -> list[tuple[str, pymupdf.Rect]]:
    return [(t, pymupdf.Rect(r)) for t, r in page.get_bboxlog() if t in _MATERIAL]


def _sample_points(trim: pymupdf.Rect, edge: str, inset: float) -> list[pymupdf.Point]:
    pts = []
    for i in range(N_SAMPLES):
        f = (i + 0.5) / N_SAMPLES
        if edge == "top":
            pts.append(pymupdf.Point(trim.x0 + f * trim.width, trim.y0 + inset))
        elif edge == "bottom":
            pts.append(pymupdf.Point(trim.x0 + f * trim.width, trim.y1 - inset))
        elif edge == "left":
            pts.append(pymupdf.Point(trim.x0 + inset, trim.y0 + f * trim.height))
        else:
            pts.append(pymupdf.Point(trim.x1 - inset, trim.y0 + f * trim.height))
    return pts


def edge_material(page: pymupdf.Page, trim: pymupdf.Rect, bleed: pymupdf.Rect, dpi: int) -> dict:
    """Topmost display-list object at the trim line, per edge; plus whether it runs past bleed."""
    log = _log(page)
    inset = 0.5 * 72 / dpi
    out = {}
    for e in EDGES:
        kinds, past = [], 0
        for p in _sample_points(trim, e, inset):
            top = None
            for t, r in log:                       # display order: later paints over earlier
                if r.contains(p):
                    top = (t, r)
            if top is None:
                kinds.append("paper")
                continue
            kinds.append(_MATERIAL[top[0]])
            r = top[1]
            beyond = {"top": r.y0 < bleed.y0 - 1, "bottom": r.y1 > bleed.y1 + 1,
                      "left": r.x0 < bleed.x0 - 1, "right": r.x1 > bleed.x1 + 1}[e]
            past += beyond
        c = collections.Counter(kinds)
        inked = [k for k in kinds if k != "paper"]
        mat = collections.Counter(inked).most_common(1)[0][0] if inked else "paper"
        out[e] = {"material": mat, "mix": dict(c), "clipped_frac": past / N_SAMPLES}
    return out


def cropmarks_in_ring(page: pymupdf.Page, trim: pymupdf.Rect, ring_pt: float) -> dict:
    """V5: thin strokes lying outside the trim that intersect the scored ring, per edge."""
    ring = pymupdf.Rect(trim.x0 - ring_pt, trim.y0 - ring_pt, trim.x1 + ring_pt, trim.y1 + ring_pt)
    hits = {e: 0 for e in EDGES}
    for t, r in page.get_bboxlog():
        if t != "stroke-path":
            continue
        r = pymupdf.Rect(r)
        thin = min(r.width, r.height) < 1.5
        if not thin or r.intersects(trim) and not _outside(r, trim) or not r.intersects(ring):
            continue
        if r.y1 <= trim.y0 + 0.01:
            hits["top"] += 1
        if r.y0 >= trim.y1 - 0.01:
            hits["bottom"] += 1
        if r.x1 <= trim.x0 + 0.01:
            hits["left"] += 1
        if r.x0 >= trim.x1 - 0.01:
            hits["right"] += 1
    return hits


def _outside(r: pymupdf.Rect, trim: pymupdf.Rect) -> bool:
    return r.x1 <= trim.x0 + 0.01 or r.x0 >= trim.x1 - 0.01 or r.y1 <= trim.y0 + 0.01 or r.y0 >= trim.y1 - 0.01


def text_near_edge(page: pymupdf.Page, rect: pymupdf.Rect, band_pt: float) -> dict:
    """V13 helper: text spans whose bbox lies within band_pt of each edge of rect."""
    hits = {e: 0 for e in EDGES}
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        r = pymupdf.Rect(b["bbox"])
        if r.y0 < rect.y0 + band_pt:
            hits["top"] += 1
        if r.y1 > rect.y1 - band_pt:
            hits["bottom"] += 1
        if r.x0 < rect.x0 + band_pt:
            hits["left"] += 1
        if r.x1 > rect.x1 - band_pt:
            hits["right"] += 1
    return hits
