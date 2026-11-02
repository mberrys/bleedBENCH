"""Run-time features (SPEC Appendix B.4): computed ONLY from the input tile and the unknown mask.

The closed list is FEATURES. Nothing here may take GT, labels, ids or another method's output.
Also: content class from the known band (feature) and from full GT (label; separate function).
"""
from __future__ import annotations

import cv2
import numpy as np

from .colour import de2000, srgb_to_lab
from .harness.metrics import dilate

FEATURES = ("feat_grad_mean", "feat_color_var", "feat_edge_density", "feat_near_white",
            "feat_mirror_disagree", "feat_paper_score", "feat_local_entropy", "feat_local_contrast",
            "feat_mask_edge_dist")
BAND = 64

# Provisional content-class thresholds; refit on the calibration selection half (C16).
CLASS_T = {"flat_std": 3.0, "flat_edge": 0.005, "grad_edge": 0.02, "texture_edge": 0.12}


def _known_band(tile: np.ndarray, unknown: np.ndarray, width: int = BAND) -> np.ndarray:
    """Known pixels within `width` px of the unknown region."""
    near = dilate(unknown, width) & ~unknown
    return near


def _stats(rgb: np.ndarray, region: np.ndarray) -> dict:
    ys, xs = np.where(region)
    if ys.size:                                   # work on the region's bounding box only
        box = (slice(max(0, ys.min() - 1), ys.max() + 2), slice(max(0, xs.min() - 1), xs.max() + 2))
        rgb, region = rgb[box], region[box]
    lab = srgb_to_lab(rgb)
    L = lab[..., 0]
    gx = cv2.Sobel(L, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(L, cv2.CV_64F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy) / 8.0
    edges = cv2.Canny(np.clip(L * 2.55, 0, 255).astype(np.uint8), 40, 120) > 0
    px = rgb[region].astype(np.float64)
    hist = np.histogram(L[region], bins=32, range=(0, 100))[0].astype(np.float64)
    p = hist / max(1.0, hist.sum())
    ent = float(-(p[p > 0] * np.log2(p[p > 0])).sum())
    return {
        "grad_mean": float(grad[region].mean()) if region.any() else 0.0,
        "color_var": float(px.std(0).max()) if len(px) else 0.0,
        "edge_density": float(edges[region].mean()) if region.any() else 0.0,
        "near_white": float((L[region] > 95).mean()) if region.any() else 0.0,
        "local_entropy": ent,
        "local_contrast": float(np.percentile(L[region], 95) - np.percentile(L[region], 5)) if region.any() else 0.0,
    }


def classify(st: dict, t: dict = CLASS_T) -> str:
    if st["color_var"] < t["flat_std"] and st["edge_density"] < t["flat_edge"]:
        return "flat"
    if st["edge_density"] >= t["texture_edge"]:
        return "texture"
    if st["edge_density"] < t["grad_edge"]:
        return "gradient"
    return "structure"


def tile_features(inp: np.ndarray, unknown: np.ndarray) -> dict:
    """feat_* from the input tile and mask only."""
    region = _known_band(inp, unknown)
    st = _stats(inp, region)
    # mirror disagreement: known rows just inside the seam vs rows further in (input-only proxy)
    near1 = dilate(unknown, 8) & ~unknown
    near2 = dilate(unknown, 16) & ~unknown & ~near1
    a, b = inp[near1].astype(np.float64), inp[near2].astype(np.float64)
    mirror = float(np.abs(a.mean(0) - b.mean(0)).mean()) if len(a) and len(b) else 0.0
    seam = dilate(unknown, 1) & ~unknown
    lab = srgb_to_lab(inp[seam])
    white = srgb_to_lab(np.array([255.0, 255.0, 255.0]))
    paper = float((de2000(lab, np.broadcast_to(white, lab.shape)) <= 2).mean()) if len(lab) else 0.0
    return {
        "feat_grad_mean": st["grad_mean"], "feat_color_var": st["color_var"],
        "feat_edge_density": st["edge_density"], "feat_near_white": st["near_white"],
        "feat_mirror_disagree": mirror, "feat_paper_score": paper,
        "feat_local_entropy": st["local_entropy"], "feat_local_contrast": st["local_contrast"],
        "feat_mask_edge_dist": float(BAND),
        "feat_content_class": classify(st),
    }


def label_content_class(gt: np.ndarray, unknown: np.ndarray, scored: np.ndarray) -> str:
    """label_*: class from GT (known band + GT ring). Label store only; never a gate input."""
    region = _known_band(gt, unknown) | scored
    return classify(_stats(gt, region))
