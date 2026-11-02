"""Geometry, colour and the SPEC §9.3 analytic harness self-tests (no private data)."""
import numpy as np
import pytest

from bleedbench import config
from bleedbench.baselines import classical as C
from bleedbench.colour import de2000, srgb_to_lab
from bleedbench.geometry import (Geometry, canvas_masks, cut_all, latent_regen, place_tiles, rot,
                                 unrot, whole_page_margins)
from bleedbench.harness.metrics import tile_metrics


# --- geometry -----------------------------------------------------------------------------------
@pytest.mark.parametrize("dpi,b,a,B", [(150, 19, 13, 32), (300, 38, 10, 48), (600, 75, 5, 80)])
def test_band_table(dpi, b, a, B):
    assert config.bleed_px(dpi) == b
    assert config.apron_px(b) == a
    assert config.band_px(b) == B


def test_5mm_and_known_bands():
    assert config.bleed_px(300, 5 / 25.4) == 60 and config.band_px(60) == 64
    assert Geometry.at(300, tile=512).known_band() == 464
    assert Geometry.at(300, tile=1024).known_band() == 976
    assert Geometry.at(300, legacy_v1=True).known_band() == 474


def test_v12_scored_ring():
    assert config.ring_scored_px(9.0, 300) == 37        # 0.125 in -> 37.5 px -> 37 scored
    assert config.ring_scored_px(18.0, 300) == 38       # 0.25 in -> capped at b
    assert config.ring_scored_px(9.0, 150) == 18


def test_whole_page_letter():
    m = whole_page_margins(2550, 3300, 48)
    assert m["r_x"] == 6 and m["canvas"][1] % 16 == 0 and m["canvas"][0] % 16 == 0


def test_tiles_one_seam_and_masks():
    g = Geometry.at(300)
    W, H = 1500, 1200
    canvas = np.zeros((H + 2 * g.B, W + 2 * g.B, 3), np.uint8)
    specs = place_tiles("case-x", W, H, g)
    assert specs == place_tiles("case-x", W, H, g)       # hash-seeded, reproducible (K4)
    for t in specs:
        tile, unk, sc = cut_all(canvas, W, H, g, t)
        assert tile.shape == (512, 512, 3)
        if t.kind == "edge":
            assert unk[: g.B].all() and not unk[g.B:].any()   # exactly one seam, band on top
            assert sc.sum() == g.s * 512
        else:
            assert unk[: g.B].all() and unk[:, : g.B].all() and not unk[g.B:, g.B:].any()


def test_small_page_tiles_invalid():
    g = Geometry.at(300)
    specs = place_tiles("tiny", 300, 300, g)
    assert not any(t.valid for t in specs)


def test_rotation_roundtrip_and_latent():
    a = np.arange(48).reshape(6, 8)
    for r in (0, 90, 180, 270):
        assert (unrot(rot(a, r), r) == a).all()
    g = Geometry.at(300)
    unk, _ = canvas_masks(512, 512, g)
    assert latent_regen(unk, 16)[g.B:-g.B, g.B:-g.B].sum() == 0   # 16-aligned seam: no regen


# --- colour (Sharma, Wu, Dalal 2005 reference pairs) -------------------------------------------
SHARMA = [((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
          ((50, 3.1571, -77.2803), (50, 0, -82.7485), 2.8615),
          ((50, 2.8361, -74.0200), (50, 0, -82.7485), 3.4412),
          ((50, 0, 0), (50, -1, 2), 2.3669),
          ((50, 2.5, 0), (73, 25, -18), 27.1492),
          ((50, 2.5, 0), (61, -5, 29), 22.8977),
          ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
          ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082)]


@pytest.mark.parametrize("l1,l2,ref", SHARMA)
def test_ciede2000(l1, l2, ref):
    assert abs(float(de2000(np.array(l1), np.array(l2))) - ref) < 1e-4


def test_srgb_white_is_d50_white():
    lab = srgb_to_lab(np.array([255, 255, 255]))
    assert abs(lab[0] - 100) < 1e-3 and abs(lab[1]) < 1e-2 and abs(lab[2]) < 1e-2


# --- §9.3 analytic self-tests --------------------------------------------------------------------
def _edge_case(gt):
    g = Geometry.at(300)
    unk = np.zeros(gt.shape[:2], bool)
    unk[: g.B] = True
    sc = np.zeros_like(unk)
    sc[g.B - g.b: g.B] = True
    inp = gt.copy()
    inp[unk] = 0
    return g, inp, unk, sc


def test_solid_page_copy_is_perfect():
    gt = np.full((512, 512, 3), (40, 120, 200), np.uint8)
    g, inp, unk, sc = _edge_case(gt)
    for fn in (C.edge_repeat, C.stretch, C.mirror, C.linear_extrapolation):
        m = tile_metrics(fn(inp, unk), inp, gt, unk, sc, content_class="flat", edge_class="FULL")
        assert m["mae"] == 0 and m["delta_e"] == 0 and m["solid_drift"] == 0
        assert m["trim_violations"] == 0 and m["final_trim_identity"]


def test_gt_copy_is_perfect():
    rng = np.random.default_rng(0)
    gt = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
    g, inp, unk, sc = _edge_case(gt)
    m = tile_metrics(C.gt_copy(inp, unk, gt), inp, gt, unk, sc, content_class="texture")
    assert m["mae"] == 0 and m["delta_e"] == 0 and m["seam_step"] == 0 and m["boundary_gradient_error"] == 0
    assert abs(m["ssim"] - 1) < 1e-9 and m["invented_area"] == 0


def test_vertical_gradient_edge_repeat_19_5s():
    g = Geometry.at(300)
    y = np.arange(512)
    col = np.clip(150 + (g.B - y), 0, 255).astype(np.uint8)          # slope s = 1 level/px
    gt = np.repeat(np.repeat(col[:, None, None], 512, 1), 3, 2)
    _, inp, unk, sc = _edge_case(gt)
    m = tile_metrics(C.edge_repeat(inp, unk), inp, gt, unk, sc, content_class="gradient")
    assert abs(m["mae"] - 19.5) < 1e-9


def test_edge_repeat_rotation_equivariant():
    g = Geometry.at(300)
    rng = np.random.default_rng(1)
    gt = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
    _, inp, unk, sc = _edge_case(gt)
    base = tile_metrics(C.edge_repeat(inp, unk), inp, gt, unk, sc)["mae"]
    for r in (90, 180, 270):
        ri, ru, rs, rg = rot(inp, r), rot(unk, r), rot(sc, r), rot(gt, r)
        assert tile_metrics(C.edge_repeat(ri, ru), ri, rg, ru, rs)["mae"] == pytest.approx(base, abs=1e-12)


def test_paper_fill_on_no_ink_and_stop():
    gt = np.full((512, 512, 3), 255, np.uint8)
    g, inp, unk, sc = _edge_case(gt)
    m = tile_metrics(C.paper_fill(inp, unk), inp, gt, unk, sc, edge_class="STOP")
    assert m["mae"] == 0 and m["stop_false_ink"] == 0 and m["stop_accept"] == 1
    gt2 = gt.copy()
    gt2[g.B:] = (30, 30, 30)                                            # ink stops at the trim
    _, inp2, _, _ = _edge_case(gt2)
    m2 = tile_metrics(C.edge_repeat(inp2, unk), inp2, gt2, unk, sc, edge_class="STOP")
    assert m2["stop_false_ink"] > 0 and m2["stop_accept"] == 0
    assert "ink" not in m2["abs_fail_reason"]          # v2.1: STOP is missing bleed, not a restraint event
    ink = inp.copy()
    ink[unk] = (0, 0, 0)
    m3 = tile_metrics(ink, inp, gt, unk, sc, edge_class="NO_INK")
    assert m3["stop_accept"] == 0 and "no_ink_ink" in m3["abs_fail_reason"]


def test_trim_violation_detected_and_clamped():
    gt = np.full((512, 512, 3), 90, np.uint8)
    g, inp, unk, sc = _edge_case(gt)
    raw = C.edge_repeat(inp, unk)
    raw[g.B + 3, 10] = (0, 0, 0)
    m = tile_metrics(raw, inp, gt, unk, sc, content_class="flat")
    assert m["trim_violations"] == 1 and m["final_trim_identity"] and m["preclamp_changed_max"] == 90


def test_classical_never_touch_known():
    rng = np.random.default_rng(2)
    gt = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
    g = Geometry.at(300)
    unk = np.zeros((512, 512), bool)
    unk[: g.B] = True
    unk[:, : g.B] = True                                                # corner L
    inp = gt.copy()
    inp[unk] = 0
    for name, fn in C.CLASSICAL.items():
        out = fn(inp, unk)
        assert (out[~unk] == inp[~unk]).all(), name
        assert out.shape == inp.shape and out.dtype == np.uint8


def test_checkerboard_gt_copy_ssim_one():
    gt = np.zeros((512, 512, 3), np.uint8)
    gt[((np.indices((512, 512)).sum(0)) % 2) == 0] = (255, 0, 0)
    gt[((np.indices((512, 512)).sum(0)) % 2) == 1] = (0, 0, 255)
    g, inp, unk, sc = _edge_case(gt)
    m = tile_metrics(C.gt_copy(inp, unk, gt), inp, gt, unk, sc)
    assert m["mae"] == 0 and abs(m["ssim"] - 1) < 1e-9


def test_determinism_classical():
    rng = np.random.default_rng(3)
    gt = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
    g, inp, unk, sc = _edge_case(gt)
    for fn in C.CLASSICAL.values():
        assert (fn(inp, unk) == fn(inp, unk)).all()
