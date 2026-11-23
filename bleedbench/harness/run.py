"""Tile runner: cut tiles for a set of pages, run methods in all four orientations, score.

Inference sees only the input canvas (InputStore). GT is loaded afterwards for scoring, in the
same process for every method; each call is wrapped in learned.sealed(), which sets
BLEEDBENCH_INFERENCE=1 so a learned method cannot open the LabelStore (see harness/learned.py).
Rows go to _private/runs/<run_id>/tiles.csv.
"""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Callable

import numpy as np

from .. import features as FT
from ..config import bleed_px, private_dir
from ..geometry import Geometry, canvas_masks, cut_tile, place_tiles, rot, unrot
from ..store import InputStore, LabelStore
from . import metrics as M
from .learned import sealed

ORIENTS = (0, 90, 180, 270)
Method = Callable[[np.ndarray, np.ndarray], np.ndarray]


def page_tiles(page_key: str, ins: InputStore, lab: LabelStore, tile: int = 512):
    """Yield (spec, inp_tile, gt_tile, unknown, scored, edge_class, invalid_reason) in base orientation."""
    inp, meta = ins.get(page_key)
    gt = lab.gt(page_key)
    L = lab.labels(page_key)
    W, H, B = meta["W"], meta["H"], meta["B"]
    edges = {e["edge"]: e for e in L["edges"]}
    b, a = _band(meta)
    g = Geometry(dpi=meta["dpi"], b=b, a=a, tile=tile)
    # V12 is per edge: each edge (and each arm of a corner) is scored at its own width, so one
    # edge without bleed (e.g. a spine) does not unscore the rest of the page.
    unk_c, sc_c = canvas_masks(W, H, g, sides=L["scored_px"])
    corner_edges = {"tl": ("top", "left"), "tr": ("top", "right"), "br": ("bottom", "right"), "bl": ("bottom", "left")}
    for t in place_tiles(page_key, W, H, g):
        if not t.valid:
            yield t, None, None, None, None, None, "V7_small_page"
            continue
        eds = (t.where,) if t.kind == "edge" else corner_edges[t.where]
        bad = [i for e in eds for i in edges[e]["invalid"]]
        classes = {edges[e]["class"] for e in eds}
        ecls = classes.pop() if len(classes) == 1 else "MIXED"
        yield (t, cut_tile(inp, W, H, g, t), cut_tile(gt, W, H, g, t), cut_tile(unk_c, W, H, g, t),
               cut_tile(sc_c, W, H, g, t), ecls, "+".join(sorted(set(bad))))


def _band(meta: dict) -> tuple[int, int]:
    """(b, a) for a page, from the stored values or derived from B and the DPI.

    Older input stores predate the stored b/a and only have B and dpi, so derive them: B is
    band_px(b), hence b = bleed_px(dpi) and a = B - b. No DPI table to rot.
    """
    B = meta["B"]
    b = meta.get("b")
    if b is None:
        b = bleed_px(meta["dpi"])
    a = meta.get("a")
    return b, (B - b if a is None else a)


def _complete_rows(path: Path):
    """Rows of a run CSV, skipping torn rows (a hard kill can leave a row with no last field).

    A torn row is not a page boundary: its page is redone on resume. Both the resume scan and
    the rewrite below must agree on that, so they share this one reader.
    """
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get(_FIELDS[-1]) is None:      # torn row from a hard kill
                continue
            yield row


def run(run_id: str, page_keys: list[str], methods: dict[str, Method], split_of: dict[str, str],
        family_of: dict[str, str], track: str = "C0-T1", orients=ORIENTS) -> Path:
    out_dir = private_dir("runs", run_id)
    path = out_dir / "tiles.csv"
    ins, lab = InputStore(), LabelStore()
    # Resume: keep rows of pages that completed (a page is written in one block, then flushed);
    # the last page in the file may be partial and is redone.
    done: list[str] = []
    if path.exists():
        for row in _complete_rows(path):
            if not done or done[-1] != row["page_id"]:
                done.append(row["page_id"])
        keep = set(done[:-1])
        if keep:
            rows_keep = [r for r in _complete_rows(path) if r["page_id"] in keep]
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=_FIELDS, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows_keep)
        page_keys = [k for k in page_keys if k not in keep]
        resume = bool(keep)
    else:
        resume = False
    writer, fh = None, open(path, "a" if resume else "w", newline="", encoding="utf-8")
    if resume:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS, extrasaction="ignore")
    try:
        for pk in page_keys:
            page_rows = []
            for t, inp, gt, unk, sc, ecls, bad in page_tiles(pk, ins, lab):
                base = {"track": track, "split": split_of[pk], "page_id": pk, "family_id": family_of[pk],
                        "tile_id": f"{t.kind}:{t.where}:{t.index}", "edge": t.where, "tile_kind": t.kind,
                        "label_bleed_class": ecls, "invalid": bad}
                if bad:
                    rows = [{**base, "method": m, "orientation": 0} for m in methods]
                else:
                    feats_cls = FT.label_content_class(gt, unk, sc)
                    ctx = M.prepare(gt, unk, sc, feats_cls, ecls if ecls in ("STOP", "FULL", "NO_INK") else None)
                    feats = FT.tile_features(inp, unk)        # rotation-invariant statistics
                    rows = []
                    batched = {}
                    for name, fn in methods.items():
                        if hasattr(fn, "batch"):
                            t0 = time.perf_counter()
                            with sealed():
                                outs = fn.batch([rot(inp, r) for r in orients], [rot(unk, r) for r in orients])
                            ms = (time.perf_counter() - t0) * 1000 / len(orients)
                            batched[name] = (outs, list(fn.last_raws), ms)
                    for oi, r in enumerate(orients):
                        ri, ru = rot(inp, r), rot(unk, r)
                        for name, fn in methods.items():
                            if name in batched:
                                outs, raws, ms = batched[name]
                                m = M.score(unrot(outs[oi], r), inp, unk, ctx, unrot(raws[oi], r))
                                rows.append({**base, "method": name, "orientation": r, "runtime_ms": round(ms, 3),
                                             "label_content_class": feats_cls, **feats, **m})
                                continue
                            t0 = time.perf_counter()
                            with sealed():
                                raw = fn(ri, ru)
                            ms = (time.perf_counter() - t0) * 1000
                            nr = getattr(fn, "last_raw", None)
                            m = M.score(unrot(raw, r), inp, unk, ctx,
                                        None if nr is None else unrot(nr, r))
                            rows.append({**base, "method": name, "orientation": r, "runtime_ms": round(ms, 3),
                                         "label_content_class": feats_cls, **feats, **m})
                page_rows.extend(rows)
            for row in page_rows:
                if writer is None:
                    writer = csv.DictWriter(fh, fieldnames=_FIELDS, extrasaction="ignore")
                    writer.writeheader()
                writer.writerow(row)
            fh.flush()
    finally:
        fh.close()
    return path


_FIELDS = ["track", "split", "page_id", "family_id", "tile_id", "tile_kind", "edge", "orientation", "method",
           "invalid", "label_bleed_class", "label_content_class", "feat_content_class",
           "mae", "mse", "psnr", "delta_e", "ssim", "seam_step", "seam_dE", "boundary_gradient_error",
           "clamp_seam_dE", "preclamp_changed", "preclamp_changed_frac", "preclamp_changed_max",
           "trim_violations", "final_trim_identity", "stop_false_ink", "stop_blob_px", "stop_accept",
           "invented_area", "solid_drift", "abs_fail", "abs_fail_reason", "runtime_ms", *FT.FEATURES]


def _worker(args):
    import os
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    import cv2
    cv2.setNumThreads(1)
    run_id, part, pks, methods_name, split_of, family_of, track, orients = args
    from ..baselines.classical import CLASSICAL
    methods = {m: CLASSICAL[m] for m in methods_name}
    return str(run(f"{run_id}/part{part:03d}", pks, methods, split_of, family_of, track, orients))


def run_parallel(run_id: str, page_keys: list[str], method_names: list[str], split_of: dict, family_of: dict,
                 track: str = "C0-T1", orients=ORIENTS, workers: int = 18) -> Path:
    """Classical methods only (picklable); pages are spread over processes, parts merged."""
    from multiprocessing import get_context
    chunks = [page_keys[i::workers] for i in range(workers)]
    jobs = [(run_id, i, c, method_names, {k: split_of[k] for k in c}, {k: family_of[k] for k in c}, track, orients)
            for i, c in enumerate(chunks) if c]
    with get_context("spawn").Pool(len(jobs)) as pool:
        parts = pool.map(_worker, jobs)
    out = private_dir("runs", run_id) / "tiles.csv"
    _merge_parts(parts, out)
    return out


def _merge_parts(parts: list[str], out: Path) -> None:
    """Merge part CSVs, keeping one block per page.

    Resume with a different worker count or page list can leave the same page in two part
    files; writing blocks in order and skipping an already-seen page_id prevents duplicate
    rows in the merged run.
    """
    pid_col = _FIELDS.index("page_id")
    seen: set[str] = set()
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header_done = False
        for p in parts:
            rows = list(csv.reader(Path(p).read_text(encoding="utf-8").splitlines()))
            if not rows:
                continue
            if not header_done:
                writer.writerow(rows[0])
                header_done = True
            current, block = None, []
            for row in rows[1:]:
                pid = row[pid_col]
                if pid != current:
                    if current is not None and current not in seen:
                        seen.add(current)
                        writer.writerows(block)
                    current, block = pid, [row]
                else:
                    block.append(row)
            if current is not None and current not in seen:
                seen.add(current)
                writer.writerows(block)
