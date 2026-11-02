"""Confidence gate: training on gate_fit, τ selection on cal_sel, certification on cal_cert
(SPEC §7.6–7.7, v2.1 DD71/DD74).

- The gate model sees only feat_* columns (closed list). `assert_feature_names` enforces it.
- Units for selection/certification are orientation-0 tiles (four rotations of a tile are not
  independent observations).
- Gate A: CP-DE one-sided 95% UB on accepted-tile severe <= 1% with n_eff >= 299.
  Gate B: UB <= the reference's own severe rate on the same half, n_eff >= 89.
- Certification recomputes the bound at the selected τ on the untouched half.
"""
from __future__ import annotations

import ast
import inspect

import numpy as np

from .. import features as FT
from . import stats as ST

GRID = np.round(np.arange(0, 1.0001, 0.005), 3)
FORBIDDEN_PREFIX = ("label_", "gt_", "case_id", "family", "page_id", "split", "severe", "oracle")


def assert_feature_names(names: list[str]) -> None:
    bad = [n for n in names if n not in FT.FEATURES or n.startswith(FORBIDDEN_PREFIX)]
    if bad:
        raise ValueError(f"gate uses non-feature columns: {bad}")


def assert_gate_code(fn) -> None:
    """Static audit: the gate's source may not mention label/id/split names."""
    src = inspect.getsource(fn)
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith(FORBIDDEN_PREFIX):
            raise ValueError(f"gate code references forbidden column {node.value!r}")


def X(rows: list[dict], names=FT.FEATURES) -> np.ndarray:
    assert_feature_names(list(names))
    return np.array([[float(r[n]) for n in names] for r in rows])


def scan(conf: np.ndarray, severe: np.ndarray, de: float, target: float, min_neff: float) -> dict | None:
    """Max-coverage τ whose CP-DE UB on accepted severe <= target and n_eff >= min_neff."""
    best = None
    for t in GRID:
        acc = conf >= t
        n = int(acc.sum())
        if n == 0 or n / de < min_neff:
            continue
        ub = ST.cp_de_upper(int(severe[acc].sum()), n, de)
        if ub <= target:
            cov = n / len(conf)
            if best is None or cov > best["coverage"]:
                best = {"tau": float(t), "coverage": cov, "accepted": n, "severe": int(severe[acc].sum()),
                        "ub95": ub}
    return best


def calibrate(sel_conf, sel_sev, cert_conf, cert_sev, de_tile: float, ref_rate_sel: float,
              ref_rate_cert: float) -> dict:
    out = {"de_tile": de_tile}
    for gate, target_sel, target_cert, neff in (("A", 0.01, 0.01, 299), ("B", ref_rate_sel, ref_rate_cert, 89)):
        pick = scan(sel_conf, sel_sev, de_tile, target_sel, neff)
        if pick is None:
            out[gate] = {"selected": False, "target": target_sel}
            continue
        acc = cert_conf >= pick["tau"]
        n = int(acc.sum())
        x = int(cert_sev[acc].sum())
        ub = ST.cp_de_upper(x, n, de_tile) if n else 1.0
        ok = n / de_tile >= neff and ub <= target_cert
        out[gate] = {"selected": True, "tau": pick["tau"], "target": round(target_sel, 4),
                     "selection": {k: round(v, 4) if isinstance(v, float) else v for k, v in pick.items()},
                     "certification": {"accepted": n, "severe": x, "ub95": round(ub, 4),
                                       "coverage": round(n / max(1, len(cert_conf)), 4)},
                     "certified": bool(ok)}
    return out
