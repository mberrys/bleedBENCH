"""Leakage and privacy checks on the local private corpus (run with: pytest -m private)."""
import collections
import json
import os

import pytest

pytestmark = pytest.mark.private


@pytest.fixture(scope="module")
def S():
    from bleedbench import splits
    return splits.load()


def test_no_family_spans_splits(S):
    seen = collections.defaultdict(set)
    for r in S.values():
        seen[r["family"]].add(r["split"])
    assert all(len(v) == 1 for v in seen.values())


def test_real_gt_never_in_train(S):
    for r in S.values():
        if r["split"].startswith(("train", "gate")):
            assert r["gt_source"] not in ("real_bleedbox", "inferred_trim")


def test_no_near_duplicate_across_splits(S):
    import imagehash
    from PIL import Image
    from bleedbench.config import private_dir
    thumbs = private_dir("review", "thumbs")
    by_file = {}
    for k, r in S.items():
        by_file.setdefault(k.split(":")[0], r["split"])
    hashes = {}
    for prefix, sp in by_file.items():
        t = thumbs / f"{prefix}.png"
        if t.exists():
            with Image.open(t) as im:
                hashes[prefix] = (imagehash.phash(im.convert("L")), imagehash.dhash(im.convert("L")), sp)
    keys = sorted(hashes)
    bad = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]
           if hashes[a][2] != hashes[b][2] and hashes[a][0] - hashes[b][0] <= 6 and hashes[a][1] - hashes[b][1] <= 8]
    assert not bad, f"{len(bad)} near-duplicate pairs cross splits"


def test_only_reviewed_pages_in_splits(S):
    from bleedbench.ingest import review
    dec = review.decisions()
    shas = {s[:16]: d for s, d in dec.items()}
    for k in S:
        assert shas.get(k.split(":")[0]) in ("include", "include_no_export")


def test_label_store_blocked_during_inference(monkeypatch):
    from bleedbench.store import LabelAccessDuringInference, LabelStore
    monkeypatch.setenv("BLEEDBENCH_INFERENCE", "1")
    with pytest.raises(LabelAccessDuringInference):
        LabelStore()


def test_aggregates_pass_export_validator():
    from bleedbench.config import AGGREGATES
    from bleedbench.privacy import validate_export
    for f in AGGREGATES.glob("*.json"):
        validate_export(json.loads(f.read_text(encoding="utf-8")))
