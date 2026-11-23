"""Inferred-trim rasters get the inferred trim (media inset by the bleed), not the band."""
from PIL import Image

from bleedbench.label import pipeline as LP


def test_frame_line_flags_a_rule_but_not_the_media_step():
    import numpy as np
    from bleedbench.label import pipeline as LP

    B = 48
    paper = np.full((B + 64, 200, 3), 255, np.uint8)
    # a thin dark rule in the margin: both sides differ
    rule = paper.copy()
    rule[B - 20, :] = (20, 20, 20)
    assert LP.frame_line(rule, B, "top")
    # a media step (paper above, art below): only one side differs
    step = paper.copy()
    step[B - 20:, :] = (10, 10, 10)
    assert not LP.frame_line(step, B, "top")


def test_inferred_raster_uses_the_bleed_not_the_band(tmp_path):
    p = tmp_path / "page.png"
    Image.new("RGB", (400, 600), (255, 255, 255)).save(p, dpi=(300, 300))
    cv = LP._inferred_raster_canvas(str(p), B=48, b=38, dpi=300)
    assert cv.B == 48 and cv.dpi == 300
    assert cv.W == 400 - 2 * 38 and cv.H == 600 - 2 * 38
    assert cv.rgb.shape[:2] == (600 + 2 * 10, 400 + 2 * 10)
    assert cv.padded[:10].all() and not cv.padded[10:30, 200].any()
    assert cv.scored_px["top"] == 38
