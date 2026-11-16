"""Per-tile metrics (SPEC §4): A1–A4, B1/B2/B7/B8, C1–C3, D1–D4/D6, A6 absolute rules, severe.

Inputs are arrays in one common orientation: raw (method output, pre-clamp), inp (input), gt,
unknown (bool), scored (bool, U). K = ~unknown. GT-only work is done once per tile in
`GTContext`; `score()` then does the method-dependent part. All metrics are rotation-invariant,
so the runner scores every orientation in the tile's base orientation.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy import ndimage
from skimage.metrics import structural_similarity

from ..colour import de2000, srgb_to_lab

_DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
A6_RULES = {                                   # provisional; frozen after calibration (§4.1)
    "flat": {"mae": 2.0, "de": 1.5},
    "gradient": {"mae": 5.0, "de": 3.0},
    "structure": {"mae": 25.0, "de": 6.0},
    "texture": {"de": 8.0},
}
C1_FAIL = 2.0
C1_CLASSES = ("flat", "gradient")   # v2.1 DD86: a seam step is a defect on smooth content only
PAPER = (255, 255, 255)


def dilate(mask: np.ndarray, r: int) -> np.ndarray:
    """Chebyshev dilation by r px (square kernel), fast."""
    k = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
    return cv2.dilate(mask.astype(np.uint8), k) > 0


def _shift(a: np.ndarray, dy: int, dx: int, fill) -> np.ndarray:
    out = np.full_like(a, fill)
    H, W = a.shape[:2]
    ys, yd = (slice(dy, H), slice(0, H - dy)) if dy >= 0 else (slice(0, H + dy), slice(-dy, H))
    xs, xd = (slice(dx, W), slice(0, W - dx)) if dx >= 0 else (slice(0, W + dx), slice(-dx, W))
    out[yd, xd] = a[ys, xs]
    return out


def clamp(raw: np.ndarray, inp: np.ndarray, unknown: np.ndarray) -> np.ndarray:
    out = raw.copy()
    out[~unknown] = inp[~unknown]
    return out


@dataclass
class GTContext:
    box: tuple
    gt: np.ndarray            # cropped
    unknown: np.ndarray
    U: np.ndarray
    nU: int
    labG: np.ndarray
    flatG: np.ndarray          # local std(L*, 7x7) < 2
    p_idx: np.ndarray          # seam pair p (flat index into crop)
    q_idx: np.ndarray
    p_count: np.ndarray        # per-pair weight 1/(#pairs of its p) for BGE
    deG_pairs: np.ndarray
    seam2: int
    content_class: str
    edge_class: str | None


def prepare(gt, unknown, scored, content_class="structure", edge_class=None) -> GTContext:
    U = scored
    ys, xs = np.where(dilate(U, 8)) if U.any() else (np.array([0]), np.array([0]))
    box = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    g, unk, u = gt[box], unknown[box], U[box]
    known = ~unk
    labG = srgb_to_lab(g)
    Lg = labG[..., 0]
    mu = ndimage.uniform_filter(Lg, 7)
    sd = np.sqrt(np.maximum(ndimage.uniform_filter(Lg ** 2, 7) - mu ** 2, 0))
    H, W = u.shape
    idx = np.arange(H * W).reshape(H, W)
    P, Q = [], []
    for dy, dx in _DIRS:
        qk = _shift(known, dy, dx, False)
        qi = _shift(idx, dy, dx, -1)
        m = u & qk
        P.append(idx[m])
        Q.append(qi[m])
    p_idx, q_idx = np.concatenate(P), np.concatenate(Q)
    cnt = np.bincount(p_idx, minlength=H * W)[p_idx] if p_idx.size else p_idx
    lg = labG.reshape(-1, 3)
    deG = de2000(lg[p_idx], lg[q_idx]) if p_idx.size else np.zeros(0)
    seam2 = int((~unknown & dilate(unknown, 2)).sum())
    return GTContext(box, g, unk, u, int(U.sum()), labG, sd < 2, p_idx, q_idx, cnt, deG, seam2,
                     content_class, edge_class)


def score(raw, inp, unknown, ctx: GTContext, net_raw=None) -> dict:
    """raw: what the submission returned. net_raw: the network's pre-composite output, when the
    submission exposes it (v2.1 DD83: D1 on the returned output, D2–D4/D6 on net_raw)."""
    known_full = ~unknown
    m: dict = {}
    m["trim_violations"] = int(((raw != inp).any(-1) & known_full).sum())          # D1 (DQ)
    pre = raw if net_raw is None else net_raw
    changed_full = (pre != inp).any(-1) & known_full
    m["preclamp_changed"] = int(changed_full.sum())                                 # D2
    m["preclamp_changed_frac"] = min(1.0, m["preclamp_changed"] / max(1, ctx.seam2))
    m["preclamp_changed_max"] = int(np.abs(pre.astype(np.int16) - inp.astype(np.int16))[known_full].max(initial=0))
    R_full = clamp(raw, inp, unknown)
    m["final_trim_identity"] = bool((R_full[known_full] == inp[known_full]).all())
    if ctx.nU == 0:
        return m
    R = R_full[ctx.box]
    changed = changed_full[ctx.box]
    U = ctx.U
    Rf, Gf = R.astype(np.float64), ctx.gt.astype(np.float64)
    # --- A
    diff = (Rf - Gf)[U]
    m["mae"] = float(np.abs(diff).mean())
    m["mse"] = float((diff ** 2).mean())
    m["psnr"] = float("inf") if m["mse"] == 0 else float(10 * np.log10(255 ** 2 / m["mse"]))
    labR = srgb_to_lab(R)
    dE = de2000(labR, ctx.labG)
    m["delta_e"] = float(dE[U].mean())
    _, smap = structural_similarity(labR[..., 0], ctx.labG[..., 0], data_range=100.0, gaussian_weights=True,
                                    sigma=1.5, use_sample_covariance=False, full=True)
    m["ssim"] = float(smap[U].mean())
    # --- C
    p, q = ctx.p_idx, ctx.q_idx
    if p.size:
        Rr, Gr = Rf.reshape(-1, 3), Gf.reshape(-1, 3)
        step = np.abs((Rr[p] - Rr[q]) - (Gr[p] - Gr[q])).mean(-1)
        lR = labR.reshape(-1, 3)
        e = np.abs(de2000(lR[p], lR[q]) - ctx.deG_pairs)
        m["seam_step"] = float(step.mean())
        m["seam_dE"] = float(e.mean())
        n_p = np.unique(p).size
        m["boundary_gradient_error"] = float((step / ctx.p_count).sum() / n_p)
        sel = changed.ravel()[q]
        m["clamp_seam_dE"] = float(e[sel].mean()) if sel.any() else 0.0
    else:
        m["seam_step"] = m["seam_dE"] = m["boundary_gradient_error"] = None
        m["clamp_seam_dE"] = 0.0
    # --- B
    if ctx.edge_class in ("STOP", "NO_INK"):          # GT ring is paper: count invented ink
        plab = srgb_to_lab(np.array(PAPER, np.float64))
        ink = (de2000(labR, np.broadcast_to(plab, labR.shape)) > 2) & U
        m["stop_false_ink"] = float(ink.sum() / ctx.nU)
        lbl, n = ndimage.label(ink, structure=np.ones((3, 3)))
        m["stop_blob_px"] = int(np.bincount(lbl.ravel())[1:].max(initial=0)) if n else 0
        m["stop_accept"] = int(m["stop_blob_px"] == 0)
    cand = (dE > 4) & ctx.flatG & U
    if cand.any():
        lbl, n = ndimage.label(cand, structure=np.ones((3, 3)))
        keep = np.bincount(lbl.ravel()) >= 50
        keep[0] = False
        m["invented_area"] = float(keep[lbl].sum() / ctx.nU)
    else:
        m["invented_area"] = 0.0
    if ctx.content_class == "flat" and ctx.edge_class in (None, "FULL"):
        m["solid_drift"] = float(np.abs(diff.mean(0)).max())
    m["abs_fail"], m["abs_fail_reason"] = a6(ctx.content_class, ctx.edge_class, m)
    return m


def a6(content_class: str, edge_class: str | None, m: dict) -> tuple[int, str]:
    """Recompute the A6 absolute-fail flag from stored per-tile metrics (same rules as score())."""
    reasons = []
    rule = A6_RULES.get(content_class, {})
    if "mae" in rule and m["mae"] > rule["mae"]:
        reasons.append(f"{content_class}_mae")
    if "de" in rule and m["delta_e"] > rule["de"]:
        reasons.append(f"{content_class}_de")
    if content_class in C1_CLASSES and m.get("seam_step") is not None and m["seam_step"] > C1_FAIL:
        reasons.append("c1")
    if edge_class == "NO_INK" and (m.get("stop_blob_px") or 0) > 0:
        reasons.append("no_ink_ink")
    if (m.get("trim_violations") or 0) > 0:
        reasons.append("trim")
    return int(bool(reasons)), "+".join(reasons)


def tile_metrics(raw, inp, gt, unknown, scored, *, content_class: str = "structure",
                 edge_class: str | None = None, net_raw=None) -> dict:
    return score(raw, inp, unknown, prepare(gt, unknown, scored, content_class, edge_class), net_raw)


def severe(mae: float, oracle_mae: float) -> int:
    """v1 rule retained: MAE > 2·oracle + 2 (SPEC §4.0)."""
    return int(mae > 2 * oracle_mae + 2)
