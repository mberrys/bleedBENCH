"""Edge labels (SPEC §3.4 V2–V5, V12, V13): paper, ink, hidden-bleed depth and class.

All functions take a page canvas (trim + B on every side) and work per edge, with the edge
rotated to the top so the ring is rows [B - s, B) and the trim starts at row B.
"""
from __future__ import annotations

import numpy as np

from ..colour import de2000, srgb_to_lab
from ..geometry import EDGES

INK_DE = 1.5
INK_DL = 2.0
_ROT = {"top": 0, "left": 3, "bottom": 2, "right": 1}   # np.rot90 k bringing the edge to top


def edge_view(a: np.ndarray, edge: str) -> np.ndarray:
    return np.rot90(a, k=_ROT[edge], axes=(0, 1))


def ink_mask(rgb: np.ndarray, paper_rgb=(255, 255, 255)) -> np.ndarray:
    """V3: ink if dE00(pixel, paper) > 1.5 or L* < L*_paper − 2."""
    lab = srgb_to_lab(rgb)
    plab = srgb_to_lab(np.array(paper_rgb, np.float64))
    de = de2000(lab, np.broadcast_to(plab, lab.shape))
    return (de > INK_DE) | (lab[..., 0] < plab[0] - INK_DL)


def paper_estimate(canvas_rgb: np.ndarray, padded: np.ndarray, B: int, renderer_white=(255, 255, 255)) -> dict:
    """V2. MuPDF renders unpainted media as white, so 'renderer' is the primary source.

    The GT ring is never used to estimate paper from a full-bleed photo; we only report whether
    the outermost 2 px of the ring are uniform near-paper (diagnostic, not a source).
    """
    return {"paper_rgb": list(renderer_white), "paper_source": "renderer_white", "paper_confidence": "high"}


def classify_edge(canvas_rgb: np.ndarray, padded: np.ndarray, B: int, s: int, edge: str,
                  paper_rgb=(255, 255, 255)) -> dict:
    """V4 class and depth for one edge, measured on the scored ring (width s) of the GT render."""
    v = edge_view(canvas_rgb, edge)
    pv = edge_view(padded, edge)
    W = v.shape[1] - 2 * B
    cols = slice(B, B + W)                          # positions along the edge, inside trim span
    trim2 = v[B:B + 2, cols]                        # first 2 px inside the trim
    ring = v[B - s:B, cols][::-1]                   # row 0 = adjacent to trim, walking outward
    ink_t = ink_mask(trim2, paper_rgb).any(axis=0)
    ink_r = ink_mask(ring, paper_rgb)
    pad_r = pv[B - s:B, cols][::-1]
    # depth d(x): consecutive ink pixels outward before the first paper pixel
    paper_r = ~ink_r
    first_paper = np.where(paper_r.any(axis=0), paper_r.argmax(axis=0), s)
    d = np.where(ink_r[0], first_paper, 0)
    D = float(np.quantile(d, 0.9)) if d.size else 0.0
    no_ink_frac = 1 - float(ink_t.mean()) if ink_t.size else 1.0
    if no_ink_frac >= 0.98:
        cls = "NO_INK"
    elif D <= 1:
        cls = "STOP"
    elif D >= 30:
        cls = "FULL"
    else:
        cls = "AMBIGUOUS"
    return {"edge": edge, "class": cls, "depth_q90": D, "ink_at_trim_frac": float(ink_t.mean()),
            "ring_ink_frac": float(ink_r.mean()), "ring_padded_px": int(pad_r.sum()), "scored_px": s}


def outer_uniformity(canvas_rgb: np.ndarray, B: int, s: int, edge: str) -> float:
    """Fraction of the outermost 2 scored rows within 2 dE00 of their mode colour (diagnostic)."""
    v = edge_view(canvas_rgb, edge)
    W = v.shape[1] - 2 * B
    band = v[B - s:B - s + 2, B:B + W].reshape(-1, 3)
    if band.size == 0:
        return 0.0
    vals, counts = np.unique(band, axis=0, return_counts=True)
    mode = vals[counts.argmax()]
    return float((de2000(srgb_to_lab(band), srgb_to_lab(mode[None].astype(float))) <= 2).mean())


def label_page(canvas, paper_rgb=(255, 255, 255)) -> list[dict]:
    return [classify_edge(canvas.rgb, canvas.padded, canvas.B, canvas.scored_px[e], e, paper_rgb)
            for e in EDGES]
