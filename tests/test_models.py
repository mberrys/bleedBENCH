import numpy as np
import pytest

torch = pytest.importorskip("torch")


def test_untrained_strip_unet_is_edge_repeat():
    from bleedbench.baselines.classical import edge_repeat
    from bleedbench.train.models import StripUNet, TorchFill
    net = StripUNet()
    torch.nn.init.zeros_(net.out.weight)              # zero correction => exactly the prefill
    f = TorchFill(net, "t", device="cuda" if torch.cuda.is_available() else "cpu")
    rng = np.random.default_rng(0)
    x = rng.integers(0, 256, (256, 256, 3), dtype=np.uint8)
    u = np.zeros((256, 256), bool)
    u[:48] = True
    u[:, :48] = True
    for k in range(4):
        uu = np.ascontiguousarray(np.rot90(u, k))
        inp = x.copy()
        inp[uu] = 0
        assert (f(inp, uu) == edge_repeat(inp, uu)).all()


def test_lama_architecture_keys_match_shapes():
    from bleedbench.train.ffc import LamaGenerator
    sd = LamaGenerator().state_dict()
    assert len(sd) == 989 and sd["model.34.weight"].shape == (3, 64, 7, 7)
