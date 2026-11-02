"""Render a page canvas = trim + B on every side, with the trim landing on integer pixels.

Real pages (Tier C0, real_bleedbox): trim from TrimBox; pixels outside the MediaBox are padded
with paper and counted (V11); the scored ring width comes from the BleedBox (V12).
Pseudo pages: pseudo-trim = MediaBox inset by B px; the canvas is the media itself.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pymupdf

from ..config import ring_scored_px

pymupdf.TOOLS.set_icc(True)          # colour-managed render (ICC / OutputIntent aware)
PAPER_RGB = (255, 255, 255)          # MuPDF renders unpainted page as white (V2 source: renderer)
MAX_SIDE_IN_300 = 36.0               # larger pages render at 150 DPI to bound memory


@dataclass
class Canvas:
    rgb: np.ndarray                  # uint8 [H+2B, W+2B, 3]
    W: int
    H: int
    B: int
    dpi: int
    padded: np.ndarray               # bool, pixels outside the MediaBox (no GT)
    scored_px: dict                  # per edge: V12 scored ring width
    flags: dict = field(default_factory=dict)


def choose_dpi(trim_w_pt: float, trim_h_pt: float) -> int:
    return 300 if max(trim_w_pt, trim_h_pt) / 72 <= MAX_SIDE_IN_300 else 150


def _render_device(page: pymupdf.Page, zoom: float, ox: float, oy: float, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Render device rect [0,w)x[0,h) where device = page_pt * zoom - (ox, oy).

    Returns (rgb, inside_media) where inside_media marks pixels covered by the page.
    """
    M = pymupdf.Matrix(zoom, 0, 0, zoom, -ox, -oy)
    page_dev = page.rect * M                       # page (= mediabox after reset) in device px
    ix0 = max(0, math.ceil(page_dev.x0 - 1e-6)); iy0 = max(0, math.ceil(page_dev.y0 - 1e-6))
    ix1 = min(w, math.floor(page_dev.x1 + 1e-6)); iy1 = min(h, math.floor(page_dev.y1 + 1e-6))
    out = np.empty((h, w, 3), np.uint8)
    out[:] = PAPER_RGB
    inside = np.zeros((h, w), bool)
    if ix1 > ix0 and iy1 > iy0:
        clip = pymupdf.Rect(ix0, iy0, ix1, iy1) * ~M
        pm = page.get_pixmap(matrix=M, clip=clip, alpha=False, annots=False,
                             colorspace=pymupdf.csRGB)
        arr = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width, pm.n)[..., :3]
        # PyMuPDF's irect can differ by a pixel from the requested one; place by its origin.
        px0, py0 = pm.x, pm.y
        sx0, sy0 = max(px0, 0), max(py0, 0)
        sx1, sy1 = min(px0 + pm.width, w), min(py0 + pm.height, h)
        out[sy0:sy1, sx0:sx1] = arr[sy0 - py0:sy1 - py0, sx0 - px0:sx1 - px0]
        inside[iy0:iy1, ix0:ix1] = True
    return out, inside


def _prepare(doc: pymupdf.Document, index: int) -> pymupdf.Page:
    page = doc[index]
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    # CropBox := MediaBox (in memory only). Copy the raw MediaBox so offset boxes stay valid.
    mb_raw = doc.xref_get_key(page.xref, "MediaBox")
    if mb_raw[0] == "array":
        if doc.xref_get_key(page.xref, "CropBox") != mb_raw:
            doc.xref_set_key(page.xref, "CropBox", mb_raw[1])
    elif abs(page.cropbox.width - page.mediabox.width) > 0.01 or abs(page.cropbox.height - page.mediabox.height) > 0.01:
        page.set_cropbox(page.mediabox)
    return doc[index]


def render_real(pdf_path: str, index: int, B: int = 48, dpi: int | None = None) -> Canvas:
    doc = pymupdf.open(pdf_path)
    page = _prepare(doc, index)
    tb, bb = page.trimbox, page.bleedbox
    dpi = dpi or choose_dpi(tb.width, tb.height)
    z = dpi / 72.0
    Wf, Hf = tb.width * z, tb.height * z
    W, H = round(Wf), round(Hf)
    flags = {"fractional_trim": abs(Wf - W) > 0.02 or abs(Hf - H) > 0.02}
    ox, oy = tb.x0 * z - B, tb.y0 * z - B
    rgb, inside = _render_device(page, z, ox, oy, W + 2 * B, H + 2 * B)
    bleed_pt = {"left": tb.x0 - bb.x0, "top": tb.y0 - bb.y0, "right": bb.x1 - tb.x1, "bottom": bb.y1 - tb.y1}
    scored = {e: max(0, ring_scored_px(v, dpi, b=math.ceil(round(0.125 * dpi, 9)))) for e, v in bleed_pt.items()}
    flags["bleed_pt"] = {e: round(v, 3) for e, v in bleed_pt.items()}
    doc.close()
    return Canvas(rgb, W, H, B, dpi, ~inside, scored, flags)


def render_pseudo(pdf_path: str, index: int, B: int = 48, dpi: int | None = None) -> Canvas:
    """Canvas = MediaBox; pseudo-trim = media inset by B (V13 is applied in labelling)."""
    doc = pymupdf.open(pdf_path)
    page = _prepare(doc, index)
    mb = page.mediabox
    dpi = dpi or choose_dpi(mb.width, mb.height)
    z = dpi / 72.0
    Wm, Hm = round(mb.width * z), round(mb.height * z)
    rgb, inside = _render_device(page, z, mb.x0 * z, mb.y0 * z, Wm, Hm)
    doc.close()
    W, H = Wm - 2 * B, Hm - 2 * B
    b = math.ceil(round(0.125 * dpi, 9))
    return Canvas(rgb, W, H, B, dpi, ~inside, {e: b for e in ("left", "top", "right", "bottom")},
                  {"fractional_trim": abs(mb.width * z - Wm) > 0.02 or abs(mb.height * z - Hm) > 0.02})


def integrity_ring_diff(pdf_path: str, index: int, canvas: Canvas) -> dict:
    """V1: re-render the canvas frame at 2x and box-downsample; compare inside the ring band.

    Only the outer frame (B + 16 px deep) is rendered at 2x, to bound cost on large pages.
    """
    doc = pymupdf.open(pdf_path)
    page = _prepare(doc, index)
    tb = page.trimbox
    z = canvas.dpi / 72.0
    B, W, H = canvas.B, canvas.W, canvas.H
    depth = B + 16
    diffs = []
    for (x0, y0, w, h) in ((0, 0, W + 2 * B, depth), (0, H + 2 * B - depth, W + 2 * B, depth),
                           (0, 0, depth, H + 2 * B), (W + 2 * B - depth, 0, depth, H + 2 * B)):
        ox, oy = (tb.x0 * z - B + x0) * 2, (tb.y0 * z - B + y0) * 2
        hi, _ = _render_device(page, 2 * z, ox, oy, 2 * w, 2 * h)
        lo = hi.reshape(h, 2, w, 2, 3).astype(np.float32).mean(axis=(1, 3))
        ref = canvas.rgb[y0:y0 + h, x0:x0 + w].astype(np.float32)
        ok = ~canvas.padded[y0:y0 + h, x0:x0 + w]
        diffs.append(np.abs(lo - ref)[ok].ravel())
    doc.close()
    d = np.concatenate(diffs) if diffs else np.zeros(1)
    return {"v1_mean": float(d.mean()), "v1_frac_gt5": float((d > 5).mean())}
