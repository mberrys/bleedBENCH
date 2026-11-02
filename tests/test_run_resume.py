import csv

import numpy as np
import pytest


@pytest.fixture
def tiny_store(tmp_path, monkeypatch):
    monkeypatch.setenv("BLEEDBENCH_PRIVATE", str(tmp_path))
    import importlib
    from bleedbench import config
    importlib.reload(config)
    from bleedbench import store
    importlib.reload(store)
    from bleedbench.geometry import EDGES
    ins, lab = store.InputStore(tmp_path / "in"), store.LabelStore(tmp_path / "lab")
    rng = np.random.default_rng(0)
    keys = []
    for i in range(3):
        W = H = 600
        g = rng.integers(0, 256, (H + 96, W + 96, 3), dtype=np.uint8)
        k = f"p{i}:0"
        ins.put(k, g, W, H, 48, {"dpi": 300})
        lab.put(k, g, np.zeros(g.shape[:2], bool),
                {"scored_px": {e: 37 for e in EDGES},
                 "edges": [{"edge": e, "class": "FULL", "invalid": []} for e in EDGES]})
        keys.append(k)
    return tmp_path, ins, lab, keys


def test_resume_skips_completed_pages(tiny_store, monkeypatch):
    tmp, ins, lab, keys = tiny_store
    from bleedbench.baselines.classical import edge_repeat
    from bleedbench.harness import run as RUN
    monkeypatch.setattr(RUN, "private_dir", lambda *p: (tmp.joinpath(*p).mkdir(parents=True, exist_ok=True) or tmp.joinpath(*p)))
    monkeypatch.setattr(RUN, "InputStore", lambda: ins)
    monkeypatch.setattr(RUN, "LabelStore", lambda: lab)
    so = {k: "val" for k in keys}
    fo = {k: "f" for k in keys}
    full = RUN.run("r", keys, {"edge_repeat": edge_repeat}, so, fo, orients=(0,))
    n_full = len(list(csv.DictReader(open(full))))
    calls = []
    def counting(t, u):
        calls.append(1)
        return edge_repeat(t, u)
    RUN.run("r", keys, {"edge_repeat": counting}, so, fo, orients=(0,))
    rows = list(csv.DictReader(open(full)))
    assert len(rows) == n_full                          # no duplicates after resume
    assert 0 < len(calls) < n_full                      # only the last (possibly partial) page redone
