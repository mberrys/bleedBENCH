"""Load a legacy pickled checkpoint without executing anything from it.

`find_class` returns real objects only for a small allowlist (tensor/storage rebuild helpers,
OrderedDict, basic builtins); every other referenced class becomes an inert stub that only
records its state. Then only the tensors are kept and written as safetensors.
"""
from __future__ import annotations

import collections
import pickle
import types

import torch

_ALLOWED = {
    ("collections", "OrderedDict"): collections.OrderedDict,
    ("collections", "defaultdict"): collections.defaultdict,
    ("torch._utils", "_rebuild_tensor_v2"): torch._utils._rebuild_tensor_v2,
    ("torch._utils", "_rebuild_parameter"): torch._utils._rebuild_parameter,
    ("torch", "Size"): torch.Size,
    ("builtins", "set"): set,
    ("builtins", "frozenset"): frozenset,
    ("builtins", "dict"): dict,
    ("builtins", "list"): list,
    ("builtins", "tuple"): tuple,
}
for _n in ("FloatStorage", "HalfStorage", "DoubleStorage", "LongStorage", "IntStorage", "ByteStorage",
           "BoolStorage", "BFloat16Storage"):
    _ALLOWED[("torch", _n)] = getattr(torch, _n)


class _Stub:
    def __init__(self, *a, **k):
        self._args = a

    def __setstate__(self, state):
        self._state = state

    def __call__(self, *a, **k):        # reduce-style construction of an unknown callable
        return _Stub()

    # containers built by SETITEM(S)/APPEND(S) opcodes on a stubbed object: keep, never run
    def __setitem__(self, k, v):
        self.__dict__.setdefault("_items", {})[k] = v

    def append(self, v):
        self.__dict__.setdefault("_list", []).append(v)

    def extend(self, vs):
        self.__dict__.setdefault("_list", []).extend(vs)


def _stub_class(module: str, name: str):
    return type(f"Stub_{name}", (_Stub,), {"__module__": "stub." + module})


class Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in _ALLOWED:
            return _ALLOWED[(module, name)]
        return _stub_class(module, name)


safe_pickle = types.SimpleNamespace(Unpickler=Unpickler, load=lambda f, **k: Unpickler(f, **k).load(),
                                    __name__="safe_pickle")


def load_state_dict(path: str) -> dict[str, torch.Tensor]:
    ck = torch.load(path, map_location="cpu", weights_only=False, pickle_module=safe_pickle)
    sd = ck["state_dict"] if isinstance(ck, dict) and "state_dict" in ck else ck
    return {k: v for k, v in sd.items() if isinstance(v, torch.Tensor)}
