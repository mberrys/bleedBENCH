"""Dev report: freeze the oracle (first call only), summarise, gate-calibrate, export aggregates."""
from __future__ import annotations

import numpy as np

from .. import features as FT
from .. import splits as S
from ..config import AGGREGATES
from ..privacy import write_export
from . import aggregate as AG
from . import gate as GATE
from . import stats as ST
from .metrics import severe


def dev_report(run_ids: list[str], gates: dict | None = None, name: str = "dev_c0") -> dict:
    """gates: {method: callable(rows) -> confidence array} (input-only features)."""
    rows = AG.load_rows(run_ids)
    oracle = AG.freeze_oracle([r for r in rows if r["method"] in AG.ORACLE_METHODS])
    summ = AG.summarise(rows, oracle)
    d = summ["design"]
    n_val_pages = len({r["page_id"] for r in rows if r["split"] == "val"})
    n_val_tiles = len({r["unit"][:2] for r in rows if r["split"] == "val"})
    summ["achieved_bounds_val"] = AG.achieved_bounds(n_val_pages, n_val_tiles, d["de_tile"], d["de_page"])
    test_pages = sum(1 for r in S.load().values() if r["split"] == "test" and r["gt_source"] == "real_bleedbox")
    summ["achieved_bounds_test"] = AG.achieved_bounds(test_pages, test_pages * 28, d["de_tile"], d["de_page"])
    # oracle bias (O14): 6-method classical oracle vs frozen 7-method
    summ["o14_severe_rate_6_vs_7"] = _o14(rows, oracle)
    summ["missing_bleed_stop"] = AG.missing_bleed(rows)
    if gates:
        summ["gates"] = {m: _gate(rows, oracle, m, fn, max(1.0, d["de_tile"])) for m, fn in gates.items()}
    out = {"protocol": "bleedbench-v2.1", "tier": "C0", "splits": "cal_sel+cal_cert+val",
           "splits_sha256": S.sha(), "oracle_sha256": AG.oracle_sha(), **summ}
    write_export(out, AGGREGATES / f"{name}.json")
    return out


def _o14(rows, oracle7):
    six = {}
    for r in rows:
        if r["method"] in AG.ORACLE_METHODS and r["method"] != "lama":
            six[r["unit"]] = min(six.get(r["unit"], 1e9), r["mae"])
    out = {}
    for m in sorted({r["method"] for r in rows}):
        rs = [r for r in rows if r["method"] == m and r["unit"] in oracle7 and r["unit"] in six]
        if rs:
            out[m] = {"six": round(float(np.mean([severe(r["mae"], six[r["unit"]]) for r in rs])), 4),
                      "seven": round(float(np.mean([severe(r["mae"], oracle7[r["unit"]][1]) for r in rs])), 4)}
    return out


def _gate(rows, oracle, method, conf_fn, de_tile):
    def part(split):
        rs = [r for r in rows if r["method"] == method and r["split"] == split and r["orientation"] == 0
              and r["unit"] in oracle and r["label_bleed_class"] in AG.SCORED_CLASSES]
        sev = np.array([severe(r["mae"], oracle[r["unit"]][1]) for r in rs])
        ref = [r for r in rows if r["method"] == AG.REF and r["split"] == split and r["orientation"] == 0
               and r["unit"] in oracle and r["label_bleed_class"] in AG.SCORED_CLASSES]
        ref_rate = float(np.mean([severe(r["mae"], oracle[r["unit"]][1]) for r in ref])) if ref else 0.0
        # the gate sees feat_* columns only (DD71): never mae/ssim/abs_fail or ids
        feats = [{k: r[k] for k in FT.FEATURES} for r in rs]
        return rs, sev, conf_fn(feats) if rs else np.zeros(0), ref_rate
    s_rows, s_sev, s_conf, s_ref = part("cal_sel")
    c_rows, c_sev, c_conf, c_ref = part("cal_cert")
    res = GATE.calibrate(s_conf, s_sev, c_conf, c_sev, de_tile, s_ref, c_ref)
    # gated SystemGain on val (page accepted iff all its orientation-0 tiles accepted)
    v_rows, v_sev, v_conf, _ = part("val")
    for g in ("A", "B"):
        cell = res.get(g, {})
        if not cell.get("selected"):
            continue
        tau = cell["tau"] if cell.get("certified") else -1.0          # uncertified -> ungated
        acc_page = {}
        for r, c in zip(v_rows, v_conf):
            acc_page[r["page_id"]] = acc_page.get(r["page_id"], True) and (c >= tau)
        ref_pf = AG._page_fid([r for r in rows if r["method"] == AG.REF and r["split"] == "val"
                               and r["label_bleed_class"] in AG.SCORED_CLASSES])
        m_pf = AG._page_fid([r for r in rows if r["method"] == method and r["split"] == "val"
                             and r["label_bleed_class"] in AG.SCORED_CLASSES])
        fam = {r["page_id"]: r["family_id"] for r in v_rows}
        pages = sorted(set(ref_pf) & set(m_pf) & set(acc_page))
        gain = np.array([ref_pf[p] - (m_pf[p] if acc_page[p] else ref_pf[p]) for p in pages])
        b = ST.cluster_bootstrap(gain, np.array([fam[p] for p in pages]))
        cell["val_system_gain"] = AG._rd(b)
        cell["val_coverage"] = round(float(np.mean([acc_page[p] for p in pages])), 4)
    return res


def transfer_table(real_runs: list[str], pseudo_runs: list[str]) -> dict:
    """T10 / O15: same methods on real-GT and pseudo pages of the dev families (orientation 0)."""
    real = [r for r in AG.load_rows(real_runs) if r["orientation"] == 0 and r["label_bleed_class"] in AG.SCORED_CLASSES]
    pseudo = [r for r in AG.load_rows(pseudo_runs) if r["orientation"] == 0 and r["label_bleed_class"] in AG.SCORED_CLASSES]
    out = {}
    for name, rs in (("real", real), ("pseudo", pseudo)):
        by = {}
        for r in rs:
            by.setdefault(r["method"], []).append(r)
        out[name] = {m: {"mae_mean": AG._r(np.mean([r["mae"] for r in v])),
                         "mae_median": AG._r(np.median([r["mae"] for r in v])),
                         "tiles": len(v), "n_families": len({r["family_id"] for r in v})}
                     for m, v in sorted(by.items()) if len({r["family_id"] for r in v}) >= 5}
    common = sorted(set(out["real"]) & set(out["pseudo"]))
    out["spearman_mae_real_vs_pseudo"] = _spearman([out["real"][m]["mae_mean"] for m in common],
                                                   [out["pseudo"][m]["mae_mean"] for m in common])
    out["methods_compared"] = len(common)
    return out


def rank_transfer(tier_a_runs: list[str], real_runs: list[str]) -> dict:
    """O13: does the synthetic tier rank methods like real C0 does? (orientation 0, scored classes)"""
    def means(runs):
        by = {}
        for r in AG.load_rows(runs):
            if r["orientation"] == 0 and r["label_bleed_class"] in AG.SCORED_CLASSES:
                by.setdefault(r["method"], []).append(r["mae"])
        return {m: float(np.mean(v)) for m, v in by.items()}
    a, c = means(tier_a_runs), means(real_runs)
    common = sorted(set(a) & set(c) - {"paper_fill"})
    return {"methods": len(common), "spearman": _spearman([a[m] for m in common], [c[m] for m in common]),
            "tier_a_mae": {m: AG._r(a[m]) for m in common}, "c0_mae": {m: AG._r(c[m]) for m in common},
            "low_power": True}


def _spearman(x, y) -> float | None:
    if len(x) < 3:
        return None
    from scipy.stats import spearmanr
    return AG._r(spearmanr(x, y).statistic)
