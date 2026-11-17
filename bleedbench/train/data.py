"""Training tiles. Sources (never real-GT families, never eval splits — DD69/DD70):

  synthetic   bleedgen pages from Tier A *train* templates (generated on the fly)
  pseudo      C0 pages whose split is train_fit (or train_dev for validation), V13-valid edges

Each sample: base-orientation tile, randomly rotated (content + mask together), with
`unknown` (ring + apron), `scored` (ring) and a seam weight map.
"""
from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset, IterableDataset

from .. import bleedgen as G
from ..geometry import Geometry, TileSpec, canvas_masks, cut_tile, rot
from ..store import InputStore, LabelStore

TILE = 512
SYN_TRAIN_TEMPLATES = range(0, 4000)          # Tier A train templates
SYN_VAL_TEMPLATES = range(90000, 90200)       # Tier A validation templates (disjoint)


def _random_spec(rng, W, H, g) -> TileSpec | None:
    if rng.random() < 0.2:
        if W + g.B < TILE or H + g.B < TILE:
            return None
        return TileSpec("corner", ["tl", "tr", "br", "bl"][rng.integers(4)], 0, 0)
    edge = ["top", "right", "bottom", "left"][rng.integers(4)]
    L = W if edge in ("top", "bottom") else H
    if L < TILE:
        return None
    return TileSpec("edge", edge, 0, g.B + int(rng.integers(0, L - TILE + 1)))


def _edges_of(spec: TileSpec) -> tuple[str, ...]:
    if spec.kind == "edge":
        return (spec.where,)
    return {"tl": ("top", "left"), "tr": ("top", "right"), "br": ("bottom", "right"), "bl": ("bottom", "left")}[spec.where]


EASY_MAE = 1.0      # tiles edge repeat already solves (ring MAE < 1) are kept with p = KEEP_EASY
KEEP_EASY = 0.2


def _er_ring_mae(gt, u, s) -> float:
    from ..baselines.classical import edge_repeat
    inp = gt.copy()
    inp[u] = 0
    return float(np.abs(edge_repeat(inp, u)[s].astype(np.int16) - gt[s]).mean())


def _sample(canvas, W, H, g, rng, bad_edges=(), hard=True, sides=None):
    masks = None
    for _ in range(30):
        spec = _random_spec(rng, W, H, g)
        if spec is None or any(e in bad_edges for e in _edges_of(spec)):
            continue
        if masks is None:                       # page-sized; build once per call, not per attempt
            masks = canvas_masks(W, H, g, sides=sides)
        unk, sc = masks
        gt = cut_tile(canvas, W, H, g, spec)
        u = cut_tile(unk, W, H, g, spec)
        s = cut_tile(sc, W, H, g, spec)
        if hard and _er_ring_mae(gt, u, s) < EASY_MAE and rng.random() > KEEP_EASY:
            continue
        r = int(rng.integers(4)) * 90
        return rot(gt, r), rot(u, r), rot(s, r)
    return None


def to_tensor(gt, unk, sc):
    img = torch.from_numpy(np.ascontiguousarray(gt)).permute(2, 0, 1).float() / 255
    return img, torch.from_numpy(unk.astype(np.float32))[None], torch.from_numpy(sc.astype(np.float32))[None]


class SyntheticTiles(IterableDataset):
    def __init__(self, templates=SYN_TRAIN_TEMPLATES, tiles_per_page=6, seed=0, hard=True):
        self.templates, self.k, self.seed, self.hard = list(templates), tiles_per_page, seed, hard
        self.pri = G.priors()

    def __iter__(self):
        info = torch.utils.data.get_worker_info()
        wid = info.id if info else 0
        rng = np.random.default_rng((self.seed, wid))
        g = Geometry.at(300)
        while True:
            tpl = self.templates[int(rng.integers(len(self.templates)))]
            try:
                pg = G.make_page(tpl, int(rng.integers(1_000_000)), self.pri, small=True)
            except ValueError:                  # a degenerate overlay must not kill a long run
                continue
            for _ in range(self.k):
                s = _sample(pg["rgb"], pg["W"], pg["H"], g, rng, hard=self.hard)
                if s is not None:
                    yield to_tensor(*s)


class PseudoTiles(Dataset):
    """Tiles cut from C0 pseudo pages of the given split partitions (train_fit / train_dev)."""

    def __init__(self, page_keys: list[str], n: int, seed: int = 0, hard: bool = True):
        self.hard = hard
        lab = LabelStore()
        self.pages = []
        for k in page_keys:
            L = lab.labels(k)
            bad = tuple(e["edge"] for e in L["edges"] if e["invalid"])
            self.pages.append((k, bad, L["scored_px"]))   # V12: per-edge scored widths
        self.n, self.seed = n, seed
        self._cache: dict = {}

    def __len__(self):
        return self.n

    def _page(self, k):
        if k not in self._cache:
            if len(self._cache) > 24:
                self._cache.pop(next(iter(self._cache)))
            gt = LabelStore().gt(k)
            meta = InputStore().meta(k)        # metadata only; the input PNG is not needed
            self._cache[k] = (gt, meta)
        return self._cache[k]

    def __getitem__(self, i):
        # consecutive indices share a page (64 tiles per page visit) so workers decode each
        # large PNG once per visit instead of once per tile
        rng = np.random.default_rng((self.seed, i))
        perm = np.random.default_rng(self.seed).permutation(len(self.pages))
        first = perm[(i // 64) % len(self.pages)]
        for attempt in range(20):
            k, bad, sides = self.pages[first if attempt == 0 else int(rng.integers(len(self.pages)))]
            gt, meta = self._page(k)
            if meta["B"] != 48:
                continue
            s = _sample(gt, meta["W"], meta["H"], Geometry.at(300), rng, bad, hard=self.hard, sides=sides)
            if s is not None:
                return to_tensor(*s)
        raise RuntimeError("no valid pseudo tile found")
