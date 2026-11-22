"""Feature stats must not read the zeroed unknown band through a bounding-box pad."""
import numpy as np

from bleedbench import features as FT


def test_stats_ignores_the_zeroed_unknown_band():
    rgb = np.full((64, 64, 3), 128, np.uint8)
    rgb[:16] = 0                              # the input store zeroes outside the trim
    unknown = np.zeros((64, 64), bool)
    unknown[:16] = True
    region = np.zeros((64, 64), bool)
    region[16:32] = True                      # known band beside the seam
    st = FT._stats(rgb, region, unknown)
    assert st["grad_mean"] == 0.0
    assert st["edge_density"] == 0.0


def test_stats_is_zero_on_a_flat_tile_whatever_the_seam_side():
    """The seam border is excluded from the gradient, so rotating the band does not fabricate
    an edge on an otherwise flat known region."""
    base = np.full((64, 64, 3), 128, np.uint8)
    base[:16] = 0
    unk = np.zeros((64, 64), bool)
    unk[:16] = True
    reg = np.zeros((64, 64), bool)
    reg[16:32] = True
    for k in range(4):
        st = FT._stats(np.ascontiguousarray(np.rot90(base, k)),
                       np.ascontiguousarray(np.rot90(reg, k)),
                       np.ascontiguousarray(np.rot90(unk, k)))
        assert st["grad_mean"] == 0.0, k
        assert st["edge_density"] == 0.0, k
