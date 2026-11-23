"""Severe CP-DE bound (DD74): its inputs are orientation-0 units and are published as such."""
from bleedbench.harness import aggregate as AG
from bleedbench.harness import stats as ST


def _row(method, page, tile, ori, mae):
    return {"method": method, "unit": (page, tile, ori), "page_id": page, "family_id": f"fam_{page}",
            "orientation": ori, "mae": mae, "delta_e": 1.0, "seam_step": 0.0,
            "boundary_gradient_error": 0.0, "runtime_ms": 1.0, "abs_fail": 0,
            "label_bleed_class": "FULL", "label_content_class": "texture",
            "tile_kind": "edge", "edge": "top", "stop_accept": None,
            "trim_violations": 0, "preclamp_changed": 0}


def test_severe_bound_is_built_from_the_orientation_zero_subset():
    orients = (0, 90, 180, 270)
    units = [(p, t, o) for p in ("p1", "p2", "p3") for t in ("t1", "t2") for o in orients]
    oracle = {u: ("edge_repeat", 1.0) for u in units}       # severe iff mae > 2*1 + 2
    rows = []
    for p, t, o in units:
        rows.append(_row("edge_repeat", p, t, o, 1.0 + (p == "p2")))     # never severe
        # probe: severe on 1 of the 6 orientation-0 tiles, and on all 18 rotated ones
        rows.append(_row("probe", p, t, o, 5.0 if o != 0 or (p, t) == ("p1", "t1") else 2.0))
    summ = AG.summarise(rows, oracle)
    de = summ["design"]["de_tile"]
    ref, probe = summ["methods"]["edge_repeat"], summ["methods"]["probe"]
    assert ref["tiles"] == probe["tiles"] == 24          # the new fields do not disturb `tiles`
    assert probe["severe_rate"] == round(19 / 24, 4)     # ...or the four-rotation rate
    assert (probe["tiles_o0"], probe["severe_o0"]) == (6, 1)
    assert probe["severe_rate_o0"] == round(1 / 6, 4)
    assert probe["severe_cp_de_ub95"] == round(ST.cp_de_upper(1, 6, de), 4)
    assert probe["severe_cp_de_ub95"] != round(ST.cp_de_upper(19, 24, de), 4)   # not the all-rotation bound
    assert (ref["severe_o0"], ref["severe_rate"]) == (0, 0.0)


def test_gate_rejects_a_label_aware_confidence_function():
    import pytest
    from bleedbench.harness import report as RP

    def conf(rows):
        return [r["label_content_class"] == "flat" for r in rows]

    with pytest.raises(ValueError, match="forbidden"):
        RP._gate([], {}, "m", conf, 1.0)


def test_missing_bleed_publishes_n_families_and_suppresses_small_cells():
    stop = [(f"p{i}", 5.0) for i in range(3)]
    rows = [_row("probe", p, "t1", 0, mae) | {"label_bleed_class": "STOP", "stop_false_ink": 0.1}
            for p, mae in stop]
    assert AG.missing_bleed(rows)["probe"] == {"suppressed": True}
    rows += [_row("probe", f"p{i}", "t1", 0, 5.0) | {"label_bleed_class": "STOP", "stop_false_ink": 0.1}
             for i in range(3, 6)]
    cell = AG.missing_bleed(rows)["probe"]
    assert cell["n_families"] == 6 and cell["tiles"] == 6
