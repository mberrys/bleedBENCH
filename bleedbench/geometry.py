"""Geometry (SPEC §2): seam-anchored tiles, whole-page canvas, masks, orientation, legacy v1 mode.

Conventions: arrays are [H, W, C], origin top-left; trim rect is (x0, y0, x1, y1) half-open.
Base canonical tile: unknown band on top (edge) or top-left L (corner).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import LATENT_GRID, apron_px, band_px, bleed_px
from .seeds import unit

EDGES = ("top", "right", "bottom", "left")
CORNERS = ("tl", "tr", "br", "bl")


@dataclass(frozen=True)
class Geometry:
    dpi: int = 300
    b: int = 38            # requested ring
    a: int = 10            # apron
    tile: int = 512
    scored: int | None = None   # V12: scored ring width (<= b); None = b

    @property
    def B(self) -> int:
        return self.b + self.a

    @property
    def s(self) -> int:
        return self.b if self.scored is None else self.scored

    @classmethod
    def at(cls, dpi: int = 300, bleed_in: float = 0.125, tile: int = 512, scored: int | None = None,
           legacy_v1: bool = False) -> "Geometry":
        b = bleed_px(dpi, bleed_in)
        a = 0 if legacy_v1 else apron_px(b)
        return cls(dpi=dpi, b=b, a=a, tile=tile, scored=scored)

    def known_band(self) -> int:
        return self.tile - self.B


def whole_page_margins(W: int, H: int, B: int) -> dict:
    """Left/top margins B; right/bottom B+δ so the canvas is 16-aligned (SPEC §2.3)."""
    dx, dy = (-W) % LATENT_GRID, (-H) % LATENT_GRID
    return {"left": B, "top": B, "right": B + dx, "bottom": B + dy,
            "canvas": (H + 2 * B + dy, W + 2 * B + dx), "r_x": W % LATENT_GRID, "r_y": H % LATENT_GRID,
            "delta": (dx, dy)}


# --- masks ------------------------------------------------------------------------------------
def canvas_masks(W: int, H: int, g: Geometry) -> tuple[np.ndarray, np.ndarray]:
    """(unknown, scored) for a page canvas of trim + B on every side.

    unknown = everything outside the trim; scored = trim dilated by s (Chebyshev) minus trim,
    i.e. the ring including the corner squares. The apron (outer B - s) is unknown, unscored.
    """
    B, s_ = g.B, g.s
    unk = np.ones((H + 2 * B, W + 2 * B), bool)
    unk[B:B + H, B:B + W] = False
    sc = np.zeros_like(unk)
    sc[B - s_:B + H + s_, B - s_:B + W + s_] = True
    sc &= unk
    return unk, sc


def rot(arr: np.ndarray, r: int) -> np.ndarray:
    """Rotate counter-clockwise by r degrees (multiple of 90); content and mask together."""
    return np.ascontiguousarray(np.rot90(arr, k=(r // 90) % 4, axes=(0, 1)))


def unrot(arr: np.ndarray, r: int) -> np.ndarray:
    return rot(arr, (360 - r) % 360)


# --- placing tiles on a page canvas ------------------------------------------------------------
# A page canvas is the render of trim + B on every side (whole-page left/top geometry); the trim
# rect inside it is (B, B, B+W, B+H). Tiles are seam-anchored crops, rotated to base orientation.

_EDGE_ROT = {"top": 0, "left": 270, "bottom": 180, "right": 90}  # rotation that brings edge to top
_CORNER_ROT = {"tl": 0, "bl": 270, "br": 180, "tr": 90}


@dataclass(frozen=True)
class TileSpec:
    kind: str          # edge | corner
    where: str         # edge name or corner name
    index: int
    pos: int           # for edges: start coordinate along the edge, in canvas px
    valid: bool = True


def place_tiles(case_id: str, W: int, H: int, g: Geometry, per_edge: int | None = None) -> list[TileSpec]:
    """Hash-seeded placement (K4): E tiles per edge, centres evenly spaced, jittered ≤25% spacing."""
    E = per_edge if per_edge is not None else (6 if g.tile <= 512 else 4)
    specs: list[TileSpec] = []
    for edge in EDGES:
        L = W if edge in ("top", "bottom") else H
        usable = L - g.tile           # keep the tile's lateral extent inside the trim: one seam
        if usable < 0:
            specs += [TileSpec("edge", edge, i, 0, False) for i in range(E)]   # V7
            continue
        spacing = L / E
        for i in range(E):
            c = (i + 0.5) * spacing + (unit(case_id, edge, i) * 2 - 1) * 0.25 * spacing
            start = int(round(min(max(c - g.tile / 2, 0), usable)))
            specs.append(TileSpec("edge", edge, i, g.B + start))
    for k, c in enumerate(CORNERS):
        ok = W + g.B >= g.tile and H + g.B >= g.tile
        specs.append(TileSpec("corner", c, k, 0, ok))
    return specs


def cut_tile(canvas: np.ndarray, W: int, H: int, g: Geometry, t: TileSpec) -> np.ndarray:
    """Crop a seam-anchored tile from the canvas and rotate it so the unknown band is on top."""
    B, T = g.B, g.tile
    Hc, Wc = canvas.shape[:2]
    assert Hc == H + 2 * B and Wc == W + 2 * B, "canvas must be trim + B on every side"
    if t.kind == "edge":
        if t.where == "top":
            crop = canvas[0:T, t.pos:t.pos + T]
        elif t.where == "bottom":
            crop = canvas[Hc - T:Hc, t.pos:t.pos + T]
        elif t.where == "left":
            crop = canvas[t.pos:t.pos + T, 0:T]
        else:
            crop = canvas[t.pos:t.pos + T, Wc - T:Wc]
        return rot(crop, _EDGE_ROT[t.where])
    ys = slice(0, T) if t.where in ("tl", "tr") else slice(Hc - T, Hc)
    xs = slice(0, T) if t.where in ("tl", "bl") else slice(Wc - T, Wc)
    return rot(canvas[ys, xs], _CORNER_ROT[t.where])


def cut_all(canvas: np.ndarray, W: int, H: int, g: Geometry, t: TileSpec):
    """(tile, unknown, scored) for one spec, all in base orientation."""
    unk, sc = canvas_masks(W, H, g)
    return cut_tile(canvas, W, H, g, t), cut_tile(unk, W, H, g, t), cut_tile(sc, W, H, g, t)


def latent_regen(unknown: np.ndarray, L: int) -> np.ndarray:
    """M_L: OR over each L×L block of the unknown mask, upsampled back to pixels (SPEC §2.5)."""
    H, W = unknown.shape
    hb, wb = -(-H // L), -(-W // L)
    pad = np.zeros((hb * L, wb * L), bool)
    pad[:H, :W] = unknown
    blk = pad.reshape(hb, L, wb, L).any(axis=(1, 3))
    return np.repeat(np.repeat(blk, L, 0), L, 1)[:H, :W]
