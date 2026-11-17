"""C0 census (v2.1): measured priors that replace v2.0's assumed marginals (O1 / ASM-A1).

Two populations, never pooled:
  deployment  every included page (what production sees; mostly no-bleed exports). Quiet share
              is measured at the page's real trim = the media edge, from the outer 2 px.
  real_gt     pages with a real BleedBox, NON-TEST families only (DD76): hidden-bleed class by
              material, depth histogram.
Every proportion carries a family-cluster bootstrap 95% CI and n_families; cells with fewer
than 5 families are suppressed. Output: aggregates/census_c0.json (committable).
"""
from __future__ import annotations

import collections

import numpy as np

from . import families as F
from . import splits as S
from .config import AGGREGATES
from .geometry import EDGES
from .ingest import probe
from .label import edges as E
from .label import pipeline as LP
from .privacy import K_ANON_FAMILIES, write_export
from .seeds import derive
from .store import LabelStore

N_BOOT = 2000
MATERIAL_NAMES = {"image": "image", "flat": "flat", "gradient": "gradient", "stroke": "stroke",
                  "text": "typography", "raster": "raster", "paper": "paper"}


def _boot_prop(fam_num: dict, fam_den: dict, seed: int = 0) -> dict:
    fams = sorted(fam_den)
    num = np.array([fam_num.get(f, 0) for f in fams], float)
    den = np.array([fam_den[f] for f in fams], float)
    n_f = int((den > 0).sum())
    if den.sum() == 0:
        return {"n": 0, "n_families": n_f, "suppressed": True}
    p = float(num.sum() / den.sum())
    if n_f < K_ANON_FAMILIES:
        return {"suppressed": True}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(fams), (N_BOOT, len(fams)))
    with np.errstate(invalid="ignore", divide="ignore"):
        bs = num[idx].sum(1) / den[idx].sum(1)
    bs = bs[np.isfinite(bs)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"p": round(p, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n": int(den.sum()), "n_families": n_f}


def _outer_no_ink(lab: LabelStore, page_key: str) -> list[bool]:
    """Deployment trim = media edge: NO_INK if <2% of positions have ink in the outer 2 px."""
    g = lab.gt(page_key)
    out = []
    for e in EDGES:
        v = E.edge_view(g, e)
        band = v[:2, 2:-2]
        ink = E.ink_mask(band).any(axis=0)
        out.append(float(ink.mean()) < 0.02)
    return out


def build() -> dict:
    split = S.load()
    fam = F.load()
    probes = {p["page_key"]: p for p in probe.load()}
    labels = {r["page_key"]: r for r in LP.load() if "edges" in r}
    lab = LabelStore()
    pages = [k for k in split if k in labels]
    test_fams = {split[k]["family"] for k in pages if split[k]["split"] == "test"}

    # ---------------- deployment population (all included pages) ----------------
    quiet_num, quiet_den = collections.Counter(), collections.Counter()
    size_b, cs_b, rot_b, orient_b = (collections.defaultdict(collections.Counter) for _ in range(4))
    for k in pages:
        f = split[k]["family"]
        L = labels[k]
        if L["gt_source"] == "real_bleedbox":
            no_ink = [e["class"] == "NO_INK" for e in L["edges"]]
        else:
            no_ink = _outer_no_ink(lab, k)
        quiet_den[f] += 1
        quiet_num[f] += all(no_ink)
        p = probes[k]
        w, h = p["trim_in"]
        bucket = "<=4x6" if max(w, h) <= 6.01 else "<=8.5x11" if max(w, h) <= 11.01 else \
                 "<=11x17" if max(w, h) <= 17.01 else ">11x17"
        size_b[bucket][f] += 1
        orient_b["landscape" if w > h else "portrait_or_square"][f] += 1
        rot_b[f"rot{p.get('rotation', 0)}"][f] += 1
        cs = set(p.get("img_colorspaces", []))
        tag = "raster" if p["kind"] == "raster" else \
              "has_cmyk" if "DeviceCMYK" in cs else "has_spot" if p.get("has_separation") else \
              "has_icc" if "ICCBased" in cs else "rgb_or_vector"
        cs_b[tag][f] += 1
    dep = {"pages": len(pages), "families": len({split[k]["family"] for k in pages}),
           "quiet_share": _boot_prop(quiet_num, quiet_den)}
    for name, b in (("size", size_b), ("colour", cs_b), ("rotation", rot_b), ("orientation", orient_b)):
        dep[name] = {key: _boot_prop(cnt, quiet_den, seed=derive("census", name, key) % 1000) for key, cnt in sorted(b.items())}

    # ---------------- real-GT, non-test families ----------------
    cls_num = collections.defaultdict(collections.Counter)
    cls_den = collections.defaultdict(collections.Counter)
    class_counts = collections.Counter()
    depth_hist = collections.Counter()
    full_num, full_den = collections.Counter(), collections.Counter()
    fams_real = set()
    for k in pages:
        L = labels[k]
        f = split[k]["family"]
        if L["gt_source"] != "real_bleedbox" or f in test_fams:
            continue
        fams_real.add(f)
        for e in L["edges"]:
            if e["invalid"]:
                continue
            class_counts[e["class"]] += 1
            d = e["depth_q90"]
            depth_hist["0-1" if d <= 1 else "2-29" if d < 30 else ">=30"] += 1
            if e["class"] in ("FULL", "STOP"):
                mat = MATERIAL_NAMES.get(e["material"], "other")
                cls_den[mat][f] += 1
                cls_num[mat][f] += e["class"] == "FULL"
                full_den[f] += 1
                full_num[f] += e["class"] == "FULL"
    real = {
        "families": len(fams_real),
        "edge_class_counts": dict(class_counts),
        "depth_q90_hist": dict(depth_hist),
        "p_full_given_inked": _boot_prop(full_num, full_den),
        "p_full_given_material": {m: _boot_prop(cls_num[m], cls_den[m], seed=i)
                                  for i, m in enumerate(sorted(cls_den))},
        "material_share_inked": {m: _boot_prop({f: v for f, v in cls_den[m].items()}, full_den, seed=50 + i)
                                 for i, m in enumerate(sorted(cls_den))},
    }
    out = {"protocol": "bleedbench-v2.1", "tier": "C0", "splits_sha256": S.sha(),
           "deployment": dep, "real_gt_non_test": real,
           "method": {"bootstrap": "family_cluster_percentile", "bootstrap_draws": N_BOOT,
                      "k_anonymity_families": K_ANON_FAMILIES,
                      "material": "pdf_bboxlog_topmost_at_trim"}}
    write_export(out, AGGREGATES / "census_c0.json")
    return out
