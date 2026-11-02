"""BL9 big-LaMa (pinned weights, safetensors), batch 1, fp32, deterministic.

Inputs whose sides are not multiples of 8 are reflect-padded and cropped back.
Returns the composited fill (known pixels copied from the input, as production does), and
exposes the network's raw output as `last_raw` so the harness can score D2–D4 (v2.1 DD83).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as Fn
from safetensors.torch import load_file

from ..config import private_dir
from ..train.ffc import LamaGenerator

WEIGHTS_SHA256 = "abfef2e8f56de9df75d21c20664edb53cf662024636ec78ccaa73cc1e861e610"


def weights_path() -> Path:
    return private_dir("weights", "lama") / "big_lama_generator.safetensors"


def load(path: Path | None = None, device: str = "cuda", verify: bool = True) -> LamaGenerator:
    path = path or weights_path()
    if verify:
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if path == weights_path() and sha != WEIGHTS_SHA256:
            raise RuntimeError("big-LaMa weights hash mismatch")
    net = LamaGenerator()
    net.load_state_dict(load_file(str(path)), strict=True)
    return net.eval().to(device)


class Lama:
    name = "lama"
    latent_stride = 8
    mask_policy = "pixel"

    def __init__(self, net: LamaGenerator | None = None, device: str = "cuda", amp: bool = False):
        self.amp = amp                      # bf16 autocast for batched fidelity runs (declared)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        self.device = device
        self.net = net if net is not None else load(device=device)

    @torch.no_grad()
    def __call__(self, tile: np.ndarray, unknown: np.ndarray) -> np.ndarray:
        H, W = unknown.shape
        img = torch.from_numpy(tile).to(self.device).permute(2, 0, 1)[None].float() / 255
        m = torch.from_numpy(unknown.astype(np.float32)).to(self.device)[None, None]
        ph, pw = (-H) % 8, (-W) % 8
        if ph or pw:
            img = Fn.pad(img, (0, pw, 0, ph), mode="reflect")
            m = Fn.pad(m, (0, pw, 0, ph), mode="reflect")
        out = self.net(img, m)[0, :, :H, :W]
        raw = (out.clamp(0, 1) * 255).round().byte().permute(1, 2, 0).cpu().numpy()
        self.last_raw = raw
        comp = tile.copy()
        comp[unknown] = raw[unknown]
        return comp

    @torch.no_grad()
    def batch(self, tiles: list, unknowns: list) -> list:
        """Same contract as __call__ for several equal-size tiles in one forward pass.
        Sets `last_raws`. Used for fidelity runs; cost (H1) is always measured at batch 1."""
        img = torch.from_numpy(np.stack(tiles)).to(self.device).permute(0, 3, 1, 2).float() / 255
        m = torch.from_numpy(np.stack(unknowns).astype(np.float32)).to(self.device)[:, None]
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=self.amp):
            out = self.net(img, m).float()
        raws = (out.clamp(0, 1) * 255).round().byte().permute(0, 2, 3, 1).cpu().numpy()
        self.last_raws = list(raws)
        res = []
        for t, u, r in zip(tiles, unknowns, raws):
            c = t.copy()
            c[u] = r[u]
            res.append(c)
        return res
