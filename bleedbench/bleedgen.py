"""bleedgen v0: procedural Tier A pages with exact GT, priors fitted to the C0 census (DD76).

A page = canvas of trim + B px per side. The background layer's extent per edge encodes the
class: FULL edges paint to the canvas edge, NO_INK edges keep a paper margin inside the trim.
v2.1 DD84: no STOP targets (art ending exactly at the trim is missing bleed; "paper beyond the
trim" is not a valid training target). Overlays (rules, text, patterns, blobs) are
clipped to the same art rectangle. Every page is reproducible from (template, seed).

Primitives: flat, gradient, photo_proxy (multi-scale colour noise; a stand-in until CC0 photos
are approved), pattern, stroke (rules/frames), typography (Pillow's bundled OFL font).
"""
from __future__ import annotations

import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import AGGREGATES
from .geometry import EDGES
from .seeds import derive

PAPER = np.array([255, 255, 255], np.uint8)

# v2.0 fallbacks where the C0 census cell is suppressed or too wide (DD77)
FALLBACK = {"quiet": 0.5, "p_reach_trim": 0.93, "material": {"image": 0.579, "flat": 0.29, "gradient": 0.0, "stroke": 0.006,
                                        "pattern": 0.025, "clipped": 0.10},
            "p_full": {"image": 0.5, "flat": 0.8, "gradient": 0.8, "stroke": 0.5, "pattern": 0.9, "clipped": 1.0}}


def priors() -> dict:
    """Census-derived generator priors; C0 value when its CI half-width <= 0.10, else fallback."""
    p = json.loads(json.dumps(FALLBACK))
    f = AGGREGATES / "census_c0.json"
    if not f.exists():
        return p
    c = json.loads(f.read_text(encoding="utf-8"))

    def usable(cell):
        return cell and not cell.get("suppressed") and (cell["ci95"][1] - cell["ci95"][0]) / 2 <= 0.10

    q = c["deployment"]["quiet_share"]
    p["quiet"] = q["p"]                      # point estimate; CI recorded in the census file
    p["quiet_ci_ok"] = usable(q)
    share = c["real_gt_non_test"]["material_share_inked"]
    for m, cell in share.items():
        if not cell.get("suppressed"):
            p["material"][m] = cell["p"]
    tot = sum(p["material"].values())
    p["material"] = {k: v / tot for k, v in p["material"].items()}
    for m, cell in c["real_gt_non_test"]["p_full_given_material"].items():
        if usable(cell):
            p["p_full"][m] = cell["p"]
        elif cell and not cell.get("suppressed"):
            p["p_full"][m] = 0.5 * (cell["p"] + FALLBACK["p_full"].get(m, 0.5))   # shrink to prior
    cc = c["real_gt_non_test"]["edge_class_counts"]
    n = sum(cc.values())
    p["p_reach_trim"] = (cc.get("FULL", 0) + cc.get("STOP", 0)) / n if n else 0.93
    p["source"] = "census_c0"
    return p


def _rng(*parts) -> np.random.Generator:
    return np.random.default_rng(derive("bleedgen", *parts))


def _colour(rng, kind="any") -> np.ndarray:
    r = rng.random()
    if kind == "tint" or r < 0.10:
        return np.clip(255 - rng.integers(8, 50, 3), 0, 255).astype(np.uint8)        # pale tint
    if r < 0.15:
        return np.array([rng.integers(0, 25)] * 3, np.uint8)                          # near/rich black
    return rng.integers(0, 256, 3).astype(np.uint8)


def _noise(rng, h, w, scales=(8, 32, 128, 512)) -> np.ndarray:
    out = np.zeros((h, w, 3), np.float32)
    for s in scales:
        small = rng.normal(0, 1, (max(2, h // s), max(2, w // s), 3)).astype(np.float32)
        out += cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC) * (s / 128.0) ** 0.8
    return out


def background(rng, kind: str, h: int, w: int) -> np.ndarray:
    if kind == "flat":
        return np.broadcast_to(_colour(rng), (h, w, 3)).copy()
    if kind == "gradient":
        a, b = _colour(rng).astype(np.float32), _colour(rng).astype(np.float32)
        ang = rng.uniform(0, np.pi)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        t = (xx * np.cos(ang) + yy * np.sin(ang))
        t = (t - t.min()) / max(1e-6, np.ptp(t))
        return (a + (b - a) * t[..., None]).astype(np.uint8)
    if kind == "pattern":
        base, ink = _colour(rng), _colour(rng)
        period = int(rng.integers(4, 60))
        ang = rng.uniform(0, np.pi)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        u = xx * np.cos(ang) + yy * np.sin(ang)
        on = (np.floor(u / period) % 2 == 0) if rng.random() < 0.6 else \
             ((np.floor(xx / period) + np.floor(yy / period)) % 2 == 0)
        out = np.empty((h, w, 3), np.uint8)
        out[:] = base
        out[on] = ink
        return out
    # image / clipped / default: photo proxy
    base = rng.uniform(40, 220, 3).astype(np.float32)
    img = base + _noise(rng, h, w) * rng.uniform(8, 40)
    return np.clip(img, 0, 255).astype(np.uint8)


def overlays(rng, img: np.ndarray, art: tuple, n: int) -> None:
    """Rules, frames, text, blobs inside the art rectangle (y0, x0, y1, x1)."""
    y0, x0, y1, x1 = art
    pil = Image.fromarray(img)
    d = ImageDraw.Draw(pil)
    for _ in range(n):
        k = rng.random()
        col = tuple(int(c) for c in _colour(rng))
        if k < 0.35:                                            # rule crossing a trim line
            wdt = int(rng.integers(1, 25))
            if rng.random() < 0.5:
                x = int(rng.integers(x0, x1))
                d.line([(x, y0), (x + int(rng.integers(-200, 200)), y1)], fill=col, width=wdt)
            else:
                y = int(rng.integers(y0, y1))
                d.line([(x0, y), (x1, y + int(rng.integers(-200, 200)))], fill=col, width=wdt)
        elif k < 0.6:                                           # text line, may cross the edge
            size = int(rng.integers(18, 160))
            font = ImageFont.load_default(size=size)
            txt = "".join(chr(int(c)) for c in rng.integers(65, 91, int(rng.integers(4, 14))))
            d.text((int(rng.integers(x0 - size, x1)), int(rng.integers(y0 - size, y1))), txt, fill=col, font=font)
        elif k < 0.8:                                           # frame
            m = int(rng.integers(20, 200))
            m = min(m, (x1 - x0) // 2 - 1, (y1 - y0) // 2 - 1)
            if m > 0:
                d.rectangle([x0 + m, y0 + m, x1 - m, y1 - m], outline=col, width=int(rng.integers(2, 20)))
        else:                                                   # blob
            cx, cy, r = int(rng.integers(x0, x1)), int(rng.integers(y0, y1)), int(rng.integers(20, 300))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    img[:] = np.asarray(pil)


def make_page(template: int, seed: int, pri: dict, B: int = 48, small: bool = False) -> dict:
    """Returns {'rgb': canvas, 'W','H','B','edges': {edge: class}, 'material', 'template'}."""
    t = _rng("template", template)
    r = _rng("page", template, seed)
    W = int(t.integers(1200, 2700)) + int(r.integers(-100, 100))
    H = int(t.integers(1200, 3400)) + int(r.integers(-100, 100))
    if small:                       # training-tile mode: same grammar, smaller canvas (speed)
        W, H = 560 + W % 400, 560 + H % 400
    mats = list(pri["material"])
    material = mats[int(t.choice(len(mats), p=[pri["material"][m] for m in mats]))]
    quiet = r.random() < pri["quiet"]
    edges = {}
    for e in EDGES:
        if quiet:
            edges[e] = "NO_INK"
        else:
            edges[e] = "FULL" if r.random() < pri["p_reach_trim"] else "NO_INK"
    Hc, Wc = H + 2 * B, W + 2 * B
    canvas = np.empty((Hc, Wc, 3), np.uint8)
    canvas[:] = PAPER
    inset = int(r.integers(40, 160))
    lim = {"FULL": 0, "STOP": B, "NO_INK": B + inset}
    y0, x0 = lim[edges["top"]], lim[edges["left"]]
    y1, x1 = Hc - lim[edges["bottom"]], Wc - lim[edges["right"]]
    bg = background(r, material if material != "stroke" else "flat", Hc, Wc)
    canvas[y0:y1, x0:x1] = bg[y0:y1, x0:x1]
    layer = canvas.copy()
    overlays(r, layer, (y0, x0, y1, x1), int(r.integers(0, 4)) + (2 if material == "stroke" else 0))
    canvas[y0:y1, x0:x1] = layer[y0:y1, x0:x1]
    return {"rgb": canvas, "W": W, "H": H, "B": B, "edges": edges, "material": material, "template": template}


def generate(n_templates: int, pages_per_template: int, split: str, store_in, store_lab, start: int = 0) -> list[dict]:
    """Write pages to the stores as gen:<template>:<seed>; returns split rows."""
    from .config import ring_scored_px
    pri = priors()
    rows = []
    for tpl in range(start, start + n_templates):
        for sd in range(pages_per_template):
            pg = make_page(tpl, sd, pri)
            key = f"gen{tpl:05d}:{sd}"
            edges = [{"edge": e, "class": c, "depth_q90": 38.0 if c == "FULL" else 0.0, "material": pg["material"],
                      "invalid": []} for e, c in pg["edges"].items()]
            store_in.put(key, pg["rgb"], pg["W"], pg["H"], pg["B"], {"dpi": 300, "gt_source": "synthetic"})
            store_lab.put(key, pg["rgb"], np.zeros(pg["rgb"].shape[:2], bool),
                          {"scored_px": {e: 38 for e in EDGES}, "edges": edges, "gt_source": "synthetic"})
            rows.append({"page_key": key, "family": f"tpl{tpl:05d}", "split": split, "gt_source": "synthetic",
                         "material": pg["material"], "edges": pg["edges"]})
    _ = ring_scored_px
    return rows
