"""Pseudo tiles must score the page's per-edge widths (V12), not the nominal ring."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from bleedbench.geometry import EDGES, Geometry


def _stores(canvas, W, H, scored_px):
    """Stand-ins for LabelStore/InputStore: labels carry scored_px, meta carries the trim size."""
    g = Geometry.at(300)

    class Lab:
        def labels(self, k):
            return {"scored_px": scored_px,
                    "edges": [{"edge": e, "class": "FULL", "invalid": []} for e in EDGES]}

        def gt(self, k):
            return canvas

    class Ins:
        def meta(self, k):
            return {"W": W, "H": H, "B": g.B, "dpi": 300}

    return Lab(), Ins()


def test_pseudo_tile_ring_follows_the_page_scored_widths(monkeypatch):
    """A page with no scored bleed at all must yield tiles with an empty scored ring: cutting
    the nominal ring instead (g.s x 512 px per edge tile) would score paper with no bleed."""
    from bleedbench.train import data as D
    g = Geometry.at(300)
    W, H = 1200, 1000
    canvas = np.random.default_rng(0).integers(0, 256, (H + 2 * g.B, W + 2 * g.B, 3), dtype=np.uint8)
    lab, ins = _stores(canvas, W, H, {e: 0 for e in EDGES})
    monkeypatch.setattr(D, "LabelStore", lambda: lab)
    monkeypatch.setattr(D, "InputStore", lambda: ins)
    _, unk, sc = D.PseudoTiles(["k0"], n=1, seed=0, hard=False)[0]
    assert unk.sum() > 0                        # the band is still unknown...
    assert sc.sum() == 0                        # ...but none of it is scored


def test_pseudo_tile_top_edge_takes_only_its_own_width(monkeypatch):
    """Only the top edge carries a scored width, so a top-edge tile must get exactly that band
    (37 px, rotation-invariant count) and nothing from the other three edges."""
    from bleedbench.geometry import TileSpec
    from bleedbench.train import data as D
    g = Geometry.at(300)
    W, H = 1200, 1000
    canvas = np.random.default_rng(1).integers(0, 256, (H + 2 * g.B, W + 2 * g.B, 3), dtype=np.uint8)
    lab, ins = _stores(canvas, W, H, {"top": 37, "left": 0, "right": 0, "bottom": 0})
    monkeypatch.setattr(D, "LabelStore", lambda: lab)
    monkeypatch.setattr(D, "InputStore", lambda: ins)
    monkeypatch.setattr(D, "_random_spec", lambda rng, W, H, g: TileSpec("edge", "top", 0, g.B))
    _, unk, sc = D.PseudoTiles(["k0"], n=1, seed=0, hard=False)[0]
    assert sc.sum() == 37 * 512
    assert unk.sum() == g.B * 512
