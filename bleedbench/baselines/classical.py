"""Classical baselines BL0–BL7 (SPEC §9.1). Contract: known pixels are never changed.

Every fill works on a base-orientation tile (unknown band on top; corner tiles have the L at
top-left) or on any array whose known region is the axis-aligned rectangle bounding ~unknown.
Corner L's are filled in two passes: the top band over known columns, then (transposed) the
left band over every row.
"""
from __future__ import annotations

import cv2
import numpy as np

K_ROWS = 8          # rows used by stretch / linear extrapolation


def _known_rect(unknown: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(~unknown)
    return int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1


def _fill_top(img: np.ndarray, B: int, kind: str) -> None:
    """Fill rows [0, B) of img (float, [h, w, c]) from rows [B, ...) in place."""
    if B <= 0:
        return
    d = np.arange(B, 0, -1)                      # row y has distance d = B - y from the seam
    known = img[B:]
    n = known.shape[0]
    if kind == "edge_repeat":
        img[:B] = known[0]
    elif kind == "mirror":
        img[:B] = known[np.minimum(d - 1, n - 1)]
    elif kind == "stretch":
        k = min(K_ROWS, n)
        src = np.minimum(np.ceil(d * k / B).astype(int) - 1, k - 1)
        img[:B] = known[src]
    elif kind == "linear_extrapolation":
        k = min(K_ROWS, n)
        x = np.arange(k, dtype=np.float64)       # 0 = seam row, inward
        ys = known[:k]                           # [k, w, c]
        xm = x.mean()
        slope = ((x - xm)[:, None, None] * (ys - ys.mean(0))).sum(0) / ((x - xm) ** 2).sum()
        icpt = ys.mean(0) - slope * xm
        img[:B] = icpt[None] + slope[None] * (-d.astype(np.float64))[:, None, None]
    else:
        raise ValueError(kind)


def _directional(tile: np.ndarray, unknown: np.ndarray, kind: str) -> np.ndarray:
    """Rotate so the known rect touches bottom/right, fill, rotate back (any orientation)."""
    for k in range(4):
        u = np.rot90(unknown, k)
        y0, x0, y1, x1 = _known_rect(u)
        if y1 == u.shape[0] and x1 == u.shape[1]:
            out = _directional_base(np.ascontiguousarray(np.rot90(tile, k)), np.ascontiguousarray(u), kind)
            return np.ascontiguousarray(np.rot90(out, -k))
    raise ValueError("unknown region is not a band/L along the tile border")


def _directional_base(tile: np.ndarray, unknown: np.ndarray, kind: str) -> np.ndarray:
    """Only rows [0, 2*y0+K) and columns [0, 2*x0+K) can be read by any fill, so work there."""
    y0, x0, _, _ = _known_rect(unknown)
    hy = min(tile.shape[0], 2 * y0 + K_ROWS)
    hx = min(tile.shape[1], 2 * x0 + K_ROWS)
    out = tile.copy()
    if y0:
        f = tile[:hy, x0:].astype(np.float64)
        _fill_top(f, y0, kind)                   # top band over known columns
        out[:y0, x0:] = np.clip(np.rint(f[:y0]), 0, 255).astype(np.uint8)
    if x0:
        ft = np.ascontiguousarray(np.swapaxes(out[:, :hx], 0, 1)).astype(np.float64)
        _fill_top(ft, x0, kind)                  # left band (corner L) over every row
        out[:, :x0] = np.clip(np.rint(np.swapaxes(ft, 0, 1)[:, :x0]), 0, 255).astype(np.uint8)
    out[~unknown] = tile[~unknown]
    return out


def gt_copy(tile, unknown, gt):
    out = tile.copy()
    out[unknown] = gt[unknown]
    return out


def paper_fill(tile, unknown, paper=(255, 255, 255)):
    out = tile.copy()
    out[unknown] = paper
    return out


def edge_repeat(tile, unknown):
    return _directional(tile, unknown, "edge_repeat")


def stretch(tile, unknown):
    return _directional(tile, unknown, "stretch")


def mirror(tile, unknown):
    return _directional(tile, unknown, "mirror")


def linear_extrapolation(tile, unknown):
    return _directional(tile, unknown, "linear_extrapolation")


def _cv_inpaint(tile, unknown, flag, margin: int = 16):
    """OpenCV inpaint, radius 3. Only pixels within `radius` of the fill front matter, so the
    call is cropped to the unknown region dilated by `margin` (identical result, much faster)."""
    ys, xs = np.where(unknown)
    y0, y1 = max(0, ys.min() - margin), min(tile.shape[0], ys.max() + 1 + margin)
    x0, x1 = max(0, xs.min() - margin), min(tile.shape[1], xs.max() + 1 + margin)
    sub, m = tile[y0:y1, x0:x1], unknown[y0:y1, x0:x1]
    bgr = cv2.cvtColor(np.ascontiguousarray(sub), cv2.COLOR_RGB2BGR)
    filled = cv2.cvtColor(cv2.inpaint(bgr, m.astype(np.uint8) * 255, 3, flag), cv2.COLOR_BGR2RGB)
    out = tile.copy()
    out[y0:y1, x0:x1][m] = filled[m]
    return out


def telea(tile, unknown):
    return _cv_inpaint(tile, unknown, cv2.INPAINT_TELEA)


def ns(tile, unknown):
    return _cv_inpaint(tile, unknown, cv2.INPAINT_NS)


CLASSICAL = {
    "paper_fill": paper_fill,
    "edge_repeat": edge_repeat,
    "stretch": stretch,
    "mirror": mirror,
    "telea": telea,
    "ns": ns,
    "linear_extrapolation": linear_extrapolation,
}
