"""Aggregation (SPEC §7) over one or more run CSVs: frozen oracle, severe, page q90, SystemGain,
paired deltas vs edge_repeat, class tables, restraint (B9), ICC/DE and achieved CP bounds.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict

import numpy as np

from ..config import private_dir
from .metrics import a6, severe
from . import stats as ST

ORACLE_METHODS = ("edge_repeat", "stretch", "mirror", "telea", "ns", "linear_extrapolation", "lama")
REF = "edge_repeat"
# v2.1 DD84: STOP (art ends exactly at the trim) is missing bleed; its GT ring (paper) is not the
# desired output, so it has no fidelity GT. Scored classes: FULL (fidelity) and NO_INK (restraint).
SCORED_CLASSES = ("FULL", "NO_INK")


def certification_rows(rows: list[dict]) -> list[dict]:
    """Rows on the certification basis (DD74): orientation 0 and a scored bleed class.

    Every severe bound and gate statistic uses this basis. Keeping the predicate here stops
    each caller from re-deriving it with a slightly different filter.
    """
    return [r for r in rows if r["orientation"] == 0 and r["label_bleed_class"] in SCORED_CLASSES]


NUM = ("mae", "delta_e", "ssim", "seam_step", "seam_dE", "boundary_gradient_error", "clamp_seam_dE",
       "preclamp_changed", "preclamp_changed_max", "trim_violations", "stop_false_ink", "stop_blob_px",
       "stop_accept", "invented_area", "solid_drift", "abs_fail", "runtime_ms")


def load_rows(run_ids: list[str]) -> list[dict]:
    rows = []
    for rid in run_ids:
        with open(private_dir("runs", rid) / "tiles.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["invalid"] or r["mae"] == "":
                    continue
                for k in NUM:
                    v = r.get(k, "")
                    r[k] = float(v) if v not in ("", "None") else None
                r["orientation"] = int(r["orientation"])
                r["abs_fail"], r["abs_fail_reason"] = a6(r["label_content_class"], r["label_bleed_class"], r)
                r["unit"] = (r["page_id"], r["tile_id"], r["orientation"])
                rows.append(r)
    return rows


def freeze_oracle(rows: list[dict], name: str = "oracle_c0") -> dict:
    """Per (page, tile, orientation): min MAE over the frozen 7-method set. Written once."""
    best: dict = {}
    have = defaultdict(set)
    for r in rows:
        if r["method"] in ORACLE_METHODS:
            have[r["unit"]].add(r["method"])
            b = best.get(r["unit"])
            if b is None or r["mae"] < b[1]:
                best[r["unit"]] = (r["method"], r["mae"])
    complete = {u: v for u, v in best.items() if have[u] == set(ORACLE_METHODS)}
    path = private_dir() / f"{name}.json"
    if path.exists():
        frozen = json.loads(path.read_text())
        return {tuple(json.loads(k)): tuple(v) for k, v in frozen["units"].items()}
    if not complete or len(complete) < 0.9 * len(best):
        raise RuntimeError(f"oracle incomplete: {len(complete)} of {len(best)} units have all 7 methods")
    blob = {"methods": list(ORACLE_METHODS),
            "units": {json.dumps(list(u)): [mv[0], round(mv[1], 6)] for u, mv in sorted(complete.items())}}
    path.write_text(json.dumps(blob, sort_keys=True))
    return complete


def oracle_sha(name: str = "oracle_c0") -> str:
    return hashlib.sha256((private_dir() / f"{name}.json").read_bytes()).hexdigest()


def summarise(rows: list[dict], oracle: dict, methods: list[str] | None = None) -> dict:
    by_m = defaultdict(list)
    for r in rows:
        if r["unit"] in oracle and r["label_bleed_class"] in SCORED_CLASSES:
            o = oracle[r["unit"]][1]
            r["oracle_mae"] = o
            r["severe"] = severe(r["mae"], o)
            by_m[r["method"]].append(r)
    methods = methods or sorted(by_m)
    ref_page = _page_fid(by_m[REF])
    out = {"oracle_methods": list(ORACLE_METHODS), "methods": {}}
    # design effects from the reference method (tile in page; page in family)
    ref = by_m[REF]
    o0 = certification_rows(ref)                      # certification unit (DD74)
    icc_t, m_t = ST.icc_oneway(np.array([r["mae"] for r in o0]), np.array([r["page_id"] for r in o0]))
    pf = ref_page
    fam_of = {r["page_id"]: r["family_id"] for r in ref}
    pk = sorted(pf)
    icc_p, m_p = ST.icc_oneway(np.array([pf[p] for p in pk]), np.array([fam_of[p] for p in pk]))
    out["design"] = {"icc_tile": round(icc_t, 4), "tiles_per_page": round(m_t, 2),
                     "de_tile": round(ST.design_effect(icc_t, m_t), 3),
                     "icc_page": round(icc_p, 4), "pages_per_family": round(m_p, 2),
                     "de_page": round(ST.design_effect(icc_p, m_p), 3),
                     "pages": len(pk), "n_families": len(set(fam_of.values()))}
    de_tile = max(1.0, out["design"]["de_tile"])
    refm = {r["unit"]: r["mae"] for r in ref}
    for m in methods:
        rs = by_m.get(m, [])
        if not rs:
            continue
        maes = np.array([r["mae"] for r in rs])
        fams = np.array([r["family_id"] for r in rs])
        sev = np.array([r["severe"] for r in rs])
        # CP-DE bound on orientation-0 units only: de_tile is measured on them, and rotations of
        # a tile are near-copies that would inflate n four-fold (DD74).
        sev0 = np.array([r["severe"] for r in certification_rows(rs)])
        af = np.array([r["abs_fail"] or 0 for r in rs])
        page = _page_fid(rs)
        common = sorted(set(page) & set(ref_page))
        gain = np.array([ref_page[p] - page[p] for p in common])
        g = ST.cluster_bootstrap(gain, np.array([fam_of[p] for p in common]))
        # paired tile delta (same unit) vs reference
        d = [(r["mae"] - refm[r["unit"]], r["family_id"]) for r in rs if r["unit"] in refm]
        dd = ST.cluster_bootstrap(np.array([x for x, _ in d]), np.array([f for _, f in d]))
        stop = _b9(rs)
        cell = {
            "tiles": len(rs), "n_families": int(len(set(fams))),
            "mae_mean": _r(maes.mean()), "mae_median": _r(np.median(maes)), "mae_p90": _r(np.quantile(maes, 0.9)),
            "mae_p99": _r(np.quantile(maes, 0.99)),
            "de_mean": _r(np.mean([r["delta_e"] for r in rs])),
            "seam_step_mean": _r(np.nanmean([r["seam_step"] for r in rs if r["seam_step"] is not None])),
            "bge_mean": _r(np.nanmean([r["boundary_gradient_error"] for r in rs if r["boundary_gradient_error"] is not None])),
            "severe_rate": _r(sev.mean()),
            # the CP-DE bound is an orientation-0 quantity (DD74), so publish its inputs next to it
            "tiles_o0": int(len(sev0)), "severe_o0": int(sev0.sum()),
            "severe_rate_o0": _r(sev0.mean()) if len(sev0) else 0.0,
            "severe_cp_de_ub95": _r(ST.cp_de_upper(int(sev0.sum()), len(sev0), de_tile)),
            "abs_fail_rate": _r(af.mean()),
            "trim_violations_tiles": int(sum(1 for r in rs if (r["trim_violations"] or 0) > 0)),
            "preclamp_changed_tiles": int(sum(1 for r in rs if (r["preclamp_changed"] or 0) > 0)),
            "runtime_ms_median": _r(np.median([r["runtime_ms"] for r in rs])),
            "delta_mae_vs_ref": _rd(dd),
            "system_gain_ungated": _rd(g),
            "restraint_no_ink": stop,
            "by_class": _by_class(rs),
        }
        out["methods"][m] = cell
    return out


def _page_fid(rs: list[dict]) -> dict:
    per = defaultdict(list)
    for r in rs:
        per[r["page_id"]].append(r["mae"])
    return {p: (float(np.quantile(v, 0.9)) if len(v) >= 5 else float(max(v))) for p, v in per.items()}


def _b9(rs: list[dict]) -> dict:
    """Edge-level restraint on NO_INK edges (paper at the trim): accepted if no tile adds ink."""
    edges = defaultdict(list)
    fam = {}
    for r in rs:
        if r["label_bleed_class"] == "NO_INK" and r["tile_kind"] == "edge" and r["orientation"] == 0                 and r["stop_accept"] is not None:
            key = (r["page_id"], r["edge"])
            edges[key].append(r["stop_accept"] == 1.0)
            fam[key] = r["family_id"]
    if not edges:
        return {"no_ink_edges": 0}
    ok = np.array([all(v) for v in edges.values()], float)
    fams = np.array([fam[k] for k in edges])
    b = ST.cluster_bootstrap(ok, fams)
    return {"no_ink_edges": len(ok), "b9_accept": _rd(b)}


def missing_bleed(rows: list[dict]) -> dict:
    """STOP edges: prevalence and how much of the ring each method extends with ink (higher is
    the production intent; there is no GT to score fidelity)."""
    out = {}
    for m in sorted({r["method"] for r in rows}):
        v = [r["stop_false_ink"] for r in rows if r["method"] == m and r["label_bleed_class"] == "STOP"
             and r["orientation"] == 0 and r["stop_false_ink"] is not None]
        if v:
            out[m] = {"tiles": len(v), "ring_extended_frac": _r(np.mean(v))}
    return out


def _by_class(rs: list[dict]) -> dict:
    by = defaultdict(list)
    for r in rs:
        by[r["label_content_class"]].append(r)
    out = {}
    for c, v in sorted(by.items()):
        pages = {r["page_id"] for r in v}
        fams = {r["family_id"] for r in v}
        maes = np.array([r["mae"] for r in v])
        cell = {"tiles": len(v), "pages": len(pages), "n_families": len(fams), "mae_mean": _r(maes.mean()),
                "mae_p90": _r(np.quantile(maes, 0.9)), "severe_rate": _r(np.mean([r["severe"] for r in v])),
                "abs_fail_rate": _r(np.mean([r["abs_fail"] or 0 for r in v])),
                "insufficient": len(pages) < 30 or len(fams) < 20}
        out[c] = cell if len(fams) >= 5 else {"suppressed": True}
    return out


def _r(x) -> float:
    return round(float(x), 4)


def _rd(d: dict) -> dict:
    if d["n_families"] < 5:                      # k-anonymity: never export a < 5-family cell
        return {"suppressed": True}
    return {"mean": _r(d["mean"]), "ci95": [_r(d["ci95"][0]), _r(d["ci95"][1])], "n_families": d["n_families"],
            "few_cluster": d["few_cluster"]}


def achieved_bounds(n_pages: int, n_tiles: int, de_tile: float, de_page: float) -> dict:
    """Zero-event one-sided 95% upper bounds the C0 sample can support (what it can certify)."""
    return {"pages": n_pages, "tiles": n_tiles,
            "zero_event_ub95_pages_raw": _r(ST.cp_upper(0, n_pages)),
            "zero_event_ub95_pages_de": _r(ST.cp_de_upper(0, n_pages, max(1, de_page))),
            "zero_event_ub95_tiles_raw": _r(ST.cp_upper(0, n_tiles)),
            "zero_event_ub95_tiles_de": _r(ST.cp_de_upper(0, n_tiles, max(1, de_tile)))}
