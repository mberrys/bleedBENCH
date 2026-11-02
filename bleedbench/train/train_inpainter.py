"""Train strip_unet (from scratch) or fine-tune big-LaMa on synthetic + pseudo train tiles.

Loss (on the composited output): L1 over the scored ring (weight 1), L1 over the apron
(weight 0.25), and a seam term: L1 between predicted and GT vertical/horizontal finite
differences on ring pixels that touch the known region (weight 2). No adversarial or
perceptual term (declared; keeps the run deterministic and download-free).

Model selection uses ONLY train_dev (pseudo) + Tier A validation templates — never real-GT
calibration data (DD70). The training manifest (sources, page keys, template ranges, seeds)
is written next to the weights so the harness can audit it against eval families (DD75).
"""
from __future__ import annotations

import hashlib
import json
import time

import numpy as np
import torch
import torch.nn.functional as Fn
from safetensors.torch import save_file
from torch.utils.data import DataLoader

from ..config import private_dir
from .. import splits as S
from . import data as D
from .models import StripUNet


def seam_loss(pred, gt, unk, sc):
    known = 1 - unk
    loss = 0.0
    for dim in (2, 3):
        dp = pred.diff(dim=dim)
        dg = gt.diff(dim=dim)
        k1 = known.narrow(dim, 1, known.shape[dim] - 1)
        k0 = known.narrow(dim, 0, known.shape[dim] - 1)
        s1 = sc.narrow(dim, 1, sc.shape[dim] - 1)
        s0 = sc.narrow(dim, 0, sc.shape[dim] - 1)
        w = s0 * k1 + s1 * k0                    # pairs straddling the seam
        loss = loss + (w * (dp - dg).abs()).sum() / (3 * w.sum().clamp(min=1))
    return loss


def objective(out, img, unk, sc):
    comp = img * (1 - unk) + out * unk
    apron = unk - sc
    n = (3 * sc.sum()).clamp(min=1)
    l_ring = ((comp - img).abs() * sc).sum() / n
    rms_ring = (((comp - img) ** 2 * sc).sum() / n + 1e-8).sqrt()      # rewards removing systematic drift
    l_apron = ((comp - img).abs() * apron).sum() / (3 * apron.sum().clamp(min=1))
    return l_ring + rms_ring + 0.25 * l_apron + 2.0 * seam_loss(comp, img, unk, sc), l_ring


def _mix(a, b):
    ia, ib = iter(a), iter(b)
    while True:
        xa, xb = next(ia), next(ib)
        yield tuple(torch.cat([u, v]) for u, v in zip(xa, xb))


@torch.no_grad()
def evaluate(net, loader, n_batches, device):
    net.eval()
    tot, n = 0.0, 0
    it = iter(loader)
    for _ in range(n_batches):
        img, unk, sc = (t.to(device) for t in next(it))
        out = net(img, unk)
        _, l = objective(out, img, unk, sc)
        tot += float(l) * img.shape[0]
        n += img.shape[0]
    net.train()
    if getattr(net, "_frozen_bn", False):
        _freeze_bn(net)
    return tot / n * 255                         # ring MAE in levels


def _freeze_bn(net) -> None:
    for mod in net.modules():
        if isinstance(mod, torch.nn.BatchNorm2d):
            mod.eval()
            for p in mod.parameters():
                p.requires_grad_(False)


def train(name: str, model: str = "strip_unet", sources=("synthetic", "pseudo"), steps: int = 20000,
          batch: int = 8, lr: float = 5e-4, eval_every: int = 1000, seed: int = 0, device: str = "cuda") -> dict:
    torch.manual_seed(seed)
    sp = S.load()
    fit = sorted(k for k, r in sp.items() if r["split"] == "train_fit")
    dev = sorted(k for k, r in sp.items() if r["split"] == "train_dev")
    assert not any(sp[k]["split"] not in ("train_fit",) for k in fit)
    if model == "strip_unet":
        net = StripUNet().to(device)
    else:
        from ..baselines.lama import load as load_lama
        net = load_lama(device=device)
        net._frozen_bn = True                    # fine-tune with frozen BN statistics
        lr = min(lr, 2e-5)
    net.train()
    if getattr(net, "_frozen_bn", False):
        _freeze_bn(net)
    decay, no_decay = [], []
    for n_, p in net.named_parameters():
        if p.requires_grad:
            (no_decay if (p.ndim == 1 or n_.startswith("out.")) else decay).append(p)
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": 1e-4}, {"params": no_decay, "weight_decay": 0.0}], lr=lr)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.05)
    half = batch // 2 if len(sources) == 2 else batch
    loaders = []
    if "synthetic" in sources:
        loaders.append(DataLoader(D.SyntheticTiles(seed=seed), batch_size=half, num_workers=6, persistent_workers=True))
    if "pseudo" in sources:
        loaders.append(DataLoader(D.PseudoTiles(fit, n=steps * half, seed=seed), batch_size=half, shuffle=False,
                                  num_workers=4, persistent_workers=True))
    stream = _mix(*loaders) if len(loaders) == 2 else iter(loaders[0])
    val_pseudo = DataLoader(D.PseudoTiles(dev, n=256, seed=999, hard=False), batch_size=8, num_workers=2)
    val_syn = DataLoader(D.SyntheticTiles(D.SYN_VAL_TEMPLATES, seed=999, hard=False), batch_size=8, num_workers=2)
    out_dir = private_dir("weights", name)
    best, log, t0 = None, [], time.time()
    scaler = torch.amp.GradScaler()
    for step in range(1, steps + 1):
        img, unk, sc = (t.to(device, non_blocking=True) for t in next(stream))
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=(model == "strip_unet")):
            out = net(img, unk)
        loss, _ = objective(out.float(), img, unk, sc)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        sched.step()
        if step % eval_every == 0 or step == steps:
            vp = evaluate(net, val_pseudo, 32, device)
            vs = evaluate(net, val_syn, 32, device)
            score = (vp + vs) / 2
            log.append({"step": step, "loss": float(loss.detach()), "val_pseudo_mae": vp, "val_syn_mae": vs,
                        "secs": round(time.time() - t0)})
            print(json.dumps(log[-1]), flush=True)
            if best is None or score < best[0]:
                best = (score, step)
                save_file({k: v.detach().float().cpu().contiguous() for k, v in net.state_dict().items()},
                          str(out_dir / "best.safetensors"))
    sha = hashlib.sha256((out_dir / "best.safetensors").read_bytes()).hexdigest()
    manifest = {"name": name, "model": model, "sources": list(sources), "steps": steps, "batch": batch,
                "lr": lr, "seed": seed, "best_step": best[1], "weights_sha256": sha,
                "train_fit_pages": fit, "train_dev_pages": dev,
                "synthetic_train_templates": [D.SYN_TRAIN_TEMPLATES.start, D.SYN_TRAIN_TEMPLATES.stop],
                "synthetic_val_templates": [D.SYN_VAL_TEMPLATES.start, D.SYN_VAL_TEMPLATES.stop],
                "splits_sha256": S.sha(), "log": log}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest
