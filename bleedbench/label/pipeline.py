"""Render + label every non-excluded page into the input/label stores.

gt_source:
  real_bleedbox  trim = TrimBox, GT = real art inside the BleedBox (scored ring per V12)
  inferred_trim  no TrimBox; media = standard size + 0.25 in; trim = media inset 0.125 in.
                 Needs manual verification before it may be scored (DD79).
  pseudo         trim = media (or raster) inset by B; ring = the page's own outer pixels.
                 Training and transfer diagnostics only (DD68); V13 rejects edges.
Output: _private/labels.jsonl
"""
from __future__ import annotations

import json
import math
import traceback

import numpy as np
import pymupdf
from PIL import Image, ImageCms

from ..config import band_px, bleed_px, private_dir
from ..geometry import EDGES
from ..ingest import inventory, probe
from ..render import pdf_render as R
from ..store import InputStore, LabelStore
from . import edges as E
from . import vector as V

Image.MAX_IMAGE_PIXELS = None
FRAME_DE = 10.0
FRAME_FRAC = 0.6


def frame_line(canvas_rgb: np.ndarray, B: int, edge: str) -> bool:
    """V13 pixel test: a straight line parallel to the edge inside the outer band + 8 px."""
    v = E.edge_view(canvas_rgb, edge)
    W = v.shape[1] - 2 * B
    band = v[: B + 8, B:B + W].astype(np.float64)
    if band.shape[0] < 8 or W < 32:
        return False
    from ..colour import srgb_to_lab, de2000
    lab = srgb_to_lab(band)
    for r in range(3, band.shape[0] - 3):
        d_up = de2000(lab[r], lab[r - 3])
        d_dn = de2000(lab[r], lab[r + 3])
        if ((d_up > FRAME_DE) & (d_dn > FRAME_DE)).mean() >= FRAME_FRAC:
            return True
    return False


def _load_raster_rgb(path: str) -> np.ndarray:
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            im = Image.alpha_composite(bg, im)
        if im.mode == "CMYK" and im.info.get("icc_profile"):
            src = ImageCms.ImageCmsProfile(__import__("io").BytesIO(im.info["icc_profile"]))
            im = ImageCms.profileToProfile(im, src, ImageCms.createProfile("sRGB"), outputMode="RGB")
        return np.asarray(im.convert("RGB")).copy()


def _canvas_from_raster(path: str, B: int) -> R.Canvas:
    """Pseudo/legacy raster: the image is already the canvas, trim = image inset by B."""
    rgb = _load_raster_rgb(path)
    H, W = rgb.shape[:2]
    b = bleed_px(300)
    return R.Canvas(rgb, W - 2 * B, H - 2 * B, B, 300, np.zeros((H, W), bool), {e: b for e in EDGES},
                    {"fractional_trim": False})


def _inferred_raster_canvas(path: str, B: int, b: int, dpi: int) -> R.Canvas:
    """inferred_trim raster: the image is the media, trim = media inset by b, padded out to B.

    The raster branch used to inset the trim by the full band B, so the ring was 10 px too deep
    and the page was scored against media outside the inferred trim. Pad the media to the
    canvas band and score exactly the b px between the inferred trim and the media edge.
    """
    rgb = _load_raster_rgb(path)
    Hm, Wm = rgb.shape[:2]
    pad = B - b
    if pad < 0:
        raise ValueError(f"band B={B} is narrower than the bleed b={b}")
    canvas = np.full((Hm + 2 * pad, Wm + 2 * pad, 3), 255, np.uint8)
    canvas[pad:pad + Hm, pad:pad + Wm] = rgb
    padded = np.ones(canvas.shape[:2], bool)
    padded[pad:pad + Hm, pad:pad + Wm] = False
    return R.Canvas(canvas, Wm - 2 * b, Hm - 2 * b, B, dpi, padded, {e: b for e in EDGES},
                    {"fractional_trim": False})


def _inferred_canvas(path: str, idx: int, B: int) -> tuple[R.Canvas, pymupdf.Rect, pymupdf.Rect]:
    doc = pymupdf.open(path)
    page = R._prepare(doc, idx)
    mb = page.rect                                  # MediaBox in render space
    tb = pymupdf.Rect(mb.x0 + 9, mb.y0 + 9, mb.x1 - 9, mb.y1 - 9)
    z = 300 / 72
    W, H = round(tb.width * z), round(tb.height * z)
    rgb, inside = R._render_device(page, z, tb.x0 * z - B, tb.y0 * z - B, W + 2 * B, H + 2 * B)
    doc.close()
    s = {e: 37 for e in EDGES}
    return R.Canvas(rgb, W, H, B, 300, ~inside, s, {"fractional_trim": False}), tb, mb


def label_one(rec: dict, inv: dict, ins: InputStore, lab: LabelStore) -> dict:
    src = rec["gt_candidate"]
    path = inv["abspath"]
    out = {"page_key": rec["page_key"], "sha256": rec["sha256"], "gt_source": src, "kind": rec["kind"]}
    if rec["kind"] == "raster":
        dpi = rec.get("dpi") or 300
        b = bleed_px(dpi)
        B = band_px(b)
        cv = _inferred_raster_canvas(path, B, b, dpi) if src == "inferred_trim" else _canvas_from_raster(path, B)
        trim_pt = bleed_pt_rect = None
    elif src == "real_bleedbox":
        dpi = R.choose_dpi(*(np.array(rec["trim_in"]) * 72))
        B = band_px(bleed_px(dpi))
        cv = R.render_real(path, rec["page_index"], B=B, dpi=dpi)
        out["v1"] = R.integrity_ring_diff(path, rec["page_index"], cv)
    elif src == "inferred_trim":
        B = band_px(bleed_px(300))
        cv, _, _ = _inferred_canvas(path, rec["page_index"], B)
    else:
        mb = rec["mediabox"]
        dpi = R.choose_dpi(mb[2] - mb[0], mb[3] - mb[1])
        B = band_px(bleed_px(dpi))
        cv = R.render_pseudo(path, rec["page_index"], B=B, dpi=dpi)
    if cv.W < 64 or cv.H < 64:
        out["skip"] = "too_small"
        return out
    out.update({"W": cv.W, "H": cv.H, "B": B, "dpi": cv.dpi, "flags": {k: v for k, v in cv.flags.items()}})
    edges = E.label_page(cv)
    # vector evidence (PDF only)
    if rec["kind"] == "pdf":
        doc = pymupdf.open(path)
        page = R._prepare(doc, rec["page_index"])
        z = cv.dpi / 72
        mb = page.rect                              # all rects in render/display-list space
        if src == "real_bleedbox":
            trim, bleed = R.render_rect(page, page.trimbox), R.render_rect(page, page.bleedbox)
        elif src == "inferred_trim":
            trim, bleed = pymupdf.Rect(mb.x0 + 9, mb.y0 + 9, mb.x1 - 9, mb.y1 - 9), mb
        else:
            trim = pymupdf.Rect(mb.x0 + B / z, mb.y0 + B / z, mb.x1 - B / z, mb.y1 - B / z)
            bleed = mb
        mats = V.edge_material(page, trim, bleed, cv.dpi)
        marks = V.cropmarks_in_ring(page, trim, max(cv.scored_px.values()) / z)
        texts = V.text_near_edge(page, mb, B / z) if src == "pseudo" else {e: 0 for e in EDGES}
        doc.close()
    else:
        mats = {e: {"material": "raster", "mix": {}, "clipped_frac": 0.0} for e in EDGES}
        marks = {e: 0 for e in EDGES}
        texts = {e: 0 for e in EDGES}
    for ed in edges:
        e = ed["edge"]
        ed.update(mats[e])
        ed["cropmarks_in_ring"] = marks[e]
        invalid = []
        if marks[e]:
            invalid.append("V5_marks_in_ring")
        if ed["ring_padded_px"] and src != "pseudo":
            invalid.append("V11_ring_padded")
        if src == "pseudo" and texts[e]:
            invalid.append("V13_text_in_band")
        # V13 applies to the inferred ring too: a thin rule in the media margin means the
        # inferred trim is wrong. A step boundary (art to paper at the media edge) does not
        # trigger the test because only one side differs, so it is safe for a full-bleed page.
        if src in ("pseudo", "inferred_trim") and frame_line(cv.rgb, B, e):
            invalid.append("V13_frame_line")
        ed["invalid"] = invalid
    out["edges"] = edges
    out["paper"] = E.paper_estimate(cv.rgb, cv.padded, B)
    b = bleed_px(cv.dpi)
    ins.put(rec["page_key"], cv.rgb, cv.W, cv.H, B,
            {"dpi": cv.dpi, "gt_source": src, "b": b, "a": B - b})
    lab.put(rec["page_key"], cv.rgb, cv.padded, {"scored_px": cv.scored_px, "edges": edges, "gt_source": src})
    return out


def run(limit: int | None = None, only: str | None = None) -> list[dict]:
    invs = {r["sha256"]: r for r in inventory.load()}
    ins, lab = InputStore(), LabelStore()
    out_path = private_dir() / "labels.jsonl"
    done = {}
    if out_path.exists():
        for l in out_path.read_text(encoding="utf-8").splitlines():
            if l:
                r = json.loads(l)
                done[r["page_key"]] = r
    pages = [p for p in probe.load() if p.get("gt_candidate") in ("real_bleedbox", "inferred_trim", "pseudo")]
    if only:
        pages = [p for p in pages if p["gt_candidate"] == only]
    if limit:
        pages = pages[:limit]
    with open(out_path, "a", encoding="utf-8") as f:
        for p in pages:
            if p["page_key"] in done:
                continue
            try:
                r = label_one(p, invs[p["sha256"]], ins, lab)
            except Exception as e:
                r = {"page_key": p["page_key"], "sha256": p["sha256"], "gt_source": p["gt_candidate"],
                     "error": type(e).__name__, "trace": traceback.format_exc(limit=2)[-300:]}
            done[p["page_key"]] = r
            f.write(json.dumps(r) + "\n")
            f.flush()
    return list(done.values())


def load() -> list[dict]:
    return [json.loads(l) for l in (private_dir() / "labels.jsonl").read_text(encoding="utf-8").splitlines() if l]
