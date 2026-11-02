"""Family-disjoint splits (SPEC §3.5 + v2.1 DD69–DD71).

Real-GT families  -> cal_sel 25% / cal_cert 25% / val 25% / test 25% (by real-GT pages)
Other families    -> train_fit 70% / train_dev 10% / gate_fit 20% (by usable pages)
A family never spans two partitions. Only pages whose file has a human review decision of
include / include_no_export enter any split. Greedy, seeded, stratified on (pages, STOP edges,
FULL edges); no family may exceed CAP of a real-GT split unless it cannot fit anywhere, in
which case it goes to calibration (cal_sel) and is reported.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from . import families as F
from .config import private_dir
from .ingest import review
from .label import pipeline as LP
from .seeds import unit

REAL = {"cal_sel": 0.25, "cal_cert": 0.25, "val": 0.25, "test": 0.25}
TRAIN = {"train_fit": 0.70, "train_dev": 0.10, "gate_fit": 0.20}
CAP = 0.20
SEED = "bleedbench-c0-splits-v2.1"


def _verified_inferred() -> set[str]:
    f = private_dir("review") / "inferred_verified.txt"
    return {l.strip() for l in f.read_text().splitlines() if l.strip()} if f.exists() else set()


def usable_pages() -> list[dict]:
    dec = review.decisions()
    ok_inferred = _verified_inferred()
    fam = F.load()
    out = []
    for r in LP.load():
        if "edges" not in r or dec.get(r["sha256"]) not in ("include", "include_no_export"):
            continue
        src = r["gt_source"]
        if src == "inferred_trim" and r["page_key"] not in ok_inferred:
            src = "pseudo_unverified"            # not scored as real until a human verifies it
        out.append({"page_key": r["page_key"], "sha256": r["sha256"], "family": fam.get(r["sha256"]),
                    "gt_source": src,
                    "stop": sum(e["class"] == "STOP" and not e["invalid"] for e in r["edges"]),
                    "full": sum(e["class"] == "FULL" and not e["invalid"] for e in r["edges"])})
    return out


def _assign(fams: dict[str, dict], targets: dict[str, float],
            allowed: dict[str, tuple[str, ...]] | None = None) -> dict[str, str]:
    """Greedy, largest family first: put each family where the squared deviation of
    (pages, STOP edges, FULL edges) from the target shares is smallest."""
    keys = ("pages", "stop", "full")
    tot = {k: sum(f[k] for f in fams.values()) for k in keys}
    cur = {s: dict.fromkeys(keys, 0) for s in targets}

    def cost() -> float:
        c = 0.0
        for s, share in targets.items():
            for k in keys:
                if tot[k]:
                    c += (cur[s][k] / (share * tot[k]) - 1) ** 2 * (2.0 if k == "pages" else 1.0)
        return c

    out = {}
    for f in sorted(fams, key=lambda f: (-fams[f]["pages"], unit(SEED, f))):
        best = None
        for s in (allowed or {}).get(f, tuple(targets)):
            for k in keys:
                cur[s][k] += fams[f][k]
            c = cost() + 1e-9 * unit(SEED, f, s)
            for k in keys:
                cur[s][k] -= fams[f][k]
            if best is None or c < best[0]:
                best = (c, s)
        out[f] = best[1]
        for k in keys:
            cur[best[1]][k] += fams[f][k]
    return out


def build() -> dict:
    pages = usable_pages()
    by_fam: dict[str, dict] = defaultdict(lambda: {"pages": 0, "stop": 0, "full": 0, "real": 0})
    for p in pages:
        f = by_fam[p["family"]]
        f["pages"] += 1
        if p["gt_source"] in ("real_bleedbox", "inferred_trim"):
            f["real"] += 1
    real_f = {k: {"pages": v["real"], "stop": 0, "full": 0} for k, v in by_fam.items() if v["real"]}
    for p in pages:
        if p["family"] in real_f and p["gt_source"] in ("real_bleedbox", "inferred_trim"):
            real_f[p["family"]]["stop"] += p["stop"]
            real_f[p["family"]]["full"] += p["full"]
    other_f = {k: {"pages": v["pages"], "stop": 0, "full": 0} for k, v in by_fam.items() if not v["real"]}
    # A family larger than CAP of one real split cannot sit in val/test without dominating it;
    # it is restricted to the two calibration halves (reported, SPEC §3.5 / DD69).
    tot_real = sum(v["pages"] for v in real_f.values())
    forced = {f for f, v in real_f.items() if v["pages"] > CAP * 0.25 * tot_real}
    a_real = _assign(real_f, REAL, {f: ("cal_sel", "cal_cert") for f in forced})
    # Same idea on the training side: a family bigger than CAP of the small partitions would make
    # train_dev / gate_fit a single-family set, so it may only go to train_fit.
    tot_other = sum(v["pages"] for v in other_f.values())
    big_other = {f for f, v in other_f.items() if v["pages"] > CAP * TRAIN["gate_fit"] * tot_other}
    a_other = _assign(other_f, TRAIN, {f: ("train_fit",) for f in big_other})
    fam_split = {**a_real, **a_other}
    rows = [{"page_key": p["page_key"], "family": p["family"], "split": fam_split[p["family"]],
             "gt_source": p["gt_source"]} for p in pages]
    blob = json.dumps({"seed": SEED, "pages": rows}, sort_keys=True).encode()
    sha = hashlib.sha256(blob).hexdigest()
    (private_dir() / "splits.json").write_bytes(blob)
    summary = defaultdict(lambda: {"pages": 0, "real_pages": 0, "families": set()})
    for r in rows:
        s = summary[r["split"]]
        s["pages"] += 1
        s["real_pages"] += r["gt_source"] in ("real_bleedbox", "inferred_trim")
        s["families"].add(r["family"])
    return {"sha256": sha, "forced_to_cal_sel": len(forced),
            "splits": {k: {"pages": v["pages"], "real_pages": v["real_pages"], "families": len(v["families"])}
                       for k, v in sorted(summary.items())}}


def load() -> dict[str, dict]:
    d = json.loads((private_dir() / "splits.json").read_text())
    return {r["page_key"]: r for r in d["pages"]}


def sha() -> str:
    return hashlib.sha256((private_dir() / "splits.json").read_bytes()).hexdigest()
