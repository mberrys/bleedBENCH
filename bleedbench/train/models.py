"""BL12r `strip_unet`: a plain convolutional U-Net strip inpainter (~30M params).

Input: RGB * (1 - mask) and the mask (4 channels). Output: sigmoid RGB. The wrapper composites
known pixels from the input and exposes `last_raw` (DD83), like the LaMa wrapper.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


def _block(cin, cout):
    return nn.Sequential(nn.Conv2d(cin, cout, 3, padding=1, padding_mode="reflect"), nn.GroupNorm(8, cout), nn.SiLU(),
                         nn.Conv2d(cout, cout, 3, padding=1, padding_mode="reflect"), nn.GroupNorm(8, cout), nn.SiLU())


def edge_repeat_prefill(img: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Torch edge repeat for a batch: every pixel takes the value of the nearest pixel of the
    known axis-aligned rectangle (works for any band/L orientation). Known pixels unchanged."""
    out = torch.empty_like(img)
    H, W = img.shape[-2:]
    ar_h = torch.arange(H, device=img.device)
    ar_w = torch.arange(W, device=img.device)
    for b in range(img.shape[0]):
        known = mask[b, 0] < 0.5
        rows = known.any(1).nonzero().flatten()
        cols = known.any(0).nonzero().flatten()
        iy = ar_h.clamp(int(rows.min()), int(rows.max()))
        ix = ar_w.clamp(int(cols.min()), int(cols.max()))
        out[b] = img[b][:, iy][:, :, ix]
    return out


class StripUNet(nn.Module):
    """Residual over an edge-repeat prefill: input = masked RGB, mask, prefill (7 ch);
    output = prefill + correction. The last layer starts near zero, so an untrained network is
    (within rounding) edge repeat; training moves it only where the data says it is wrong."""

    def __init__(self, ch=(64, 128, 256, 384, 512)):
        super().__init__()
        self.inc = _block(7, ch[0])
        self.downs = nn.ModuleList(_block(a, b) for a, b in zip(ch[:-1], ch[1:]))
        self.pool = nn.AvgPool2d(2)
        self.ups = nn.ModuleList(nn.ConvTranspose2d(b, a, 2, stride=2) for a, b in zip(ch[:-1], ch[1:]))
        self.dec = nn.ModuleList(_block(2 * a, a) for a in ch[:-1])
        self.out = nn.Conv2d(ch[0], 3, 1)
        nn.init.normal_(self.out.weight, std=1e-2)   # small start so gradients reach earlier layers
        nn.init.zeros_(self.out.bias)

    def forward(self, img, mask):
        pre = edge_repeat_prefill(img * (1 - mask), mask)
        x = self.inc(torch.cat([img * (1 - mask), mask, pre], 1))
        skips = [x]
        for d in self.downs:
            x = d(self.pool(x))
            skips.append(x)
        skips.pop()
        for up, dec in zip(reversed(self.ups), reversed(self.dec)):
            x = dec(torch.cat([up(x), skips.pop()], 1))
        return (pre + self.out(x)).clamp(0, 1)


class TorchFill:
    """Inference wrapper for any (img, mask) -> img network. fp32, batch 1, deterministic."""
    latent_stride = 1
    mask_policy = "pixel"

    def __init__(self, net: nn.Module, name: str, device: str = "cuda", amp: bool = False):
        self.amp = amp
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        self.net, self.name, self.device = net.eval().to(device), name, device

    @torch.no_grad()
    def __call__(self, tile: np.ndarray, unknown: np.ndarray) -> np.ndarray:
        H, W = unknown.shape
        img = torch.from_numpy(tile).to(self.device).permute(2, 0, 1)[None].float() / 255
        m = torch.from_numpy(unknown.astype(np.float32)).to(self.device)[None, None]
        ph, pw = (-H) % 16, (-W) % 16
        if ph or pw:
            img = torch.nn.functional.pad(img, (0, pw, 0, ph), mode="reflect")
            m = torch.nn.functional.pad(m, (0, pw, 0, ph), mode="reflect")
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
