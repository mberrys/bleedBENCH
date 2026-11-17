"""Gate model: P(severe) from feat_* only, fitted on the gate_fit partition (pseudo GT), which
is disjoint from inpainter training data (DD70, no stacking leakage). confidence = 1 - P.

Severe labels on gate_fit use the same frozen 7-method oracle definition, computed on those
units (gate_fit is never used for oracle *freezing*; the frozen file covers real-GT units).
"""
from __future__ import annotations

import json
import pickle

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .. import features as FT
from ..config import private_dir
from ..harness import gate as GATE
from ..harness.aggregate import ORACLE_METHODS
from ..harness.metrics import severe


def severe_labels(rows: list[dict], method: str) -> tuple[list[dict], np.ndarray]:
    """rows: all methods on the same units. Returns (method rows, severe array)."""
    best: dict = {}
    have: dict = {}
    for r in rows:
        if r["method"] in ORACLE_METHODS:
            best[r["unit"]] = min(best.get(r["unit"], 1e9), r["mae"])
            have.setdefault(r["unit"], set()).add(r["method"])
    # same definition as the frozen oracle: only units where all 7 methods ran
    best = {u: v for u, v in best.items() if have[u] == set(ORACLE_METHODS)}
    mine = [r for r in rows if r["method"] == method and r["unit"] in best]
    sev = np.array([severe(r["mae"], best[r["unit"]]) for r in mine])
    return mine, sev


def fit(rows: list[dict], method: str, name: str) -> dict:
    mine, sev = severe_labels(rows, method)
    X = GATE.X(mine)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                         l2_regularization=1.0, random_state=0)
    clf.fit(X, sev)
    path = private_dir("weights", name)
    (path / "gate.pkl").write_bytes(pickle.dumps(clf))      # our own object, never loaded from outside
    meta = {"method": method, "features": list(FT.FEATURES), "n": int(len(sev)), "severe_rate": float(sev.mean()),
            "trained_on": "gate_fit"}
    (path / "gate.json").write_text(json.dumps(meta, indent=1))
    return meta


def load(name: str):
    return pickle.loads((private_dir("weights", name) / "gate.pkl").read_bytes())


def confidence(clf, rows: list[dict]) -> np.ndarray:
    X = GATE.X(rows)
    if len(getattr(clf, "classes_", [])) < 2:
        return np.ones(len(rows))
    return 1.0 - clf.predict_proba(X)[:, list(clf.classes_).index(1)]
