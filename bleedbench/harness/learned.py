"""Inference-time label isolation (SPEC V10).

`store.LabelStore` refuses to open while `BLEEDBENCH_INFERENCE=1`. This module wraps a method
call in that flag, so a learned method that reaches for GT fails loudly instead of silently
scoring against labels. The runner has already opened its own store before the guard, and the
methods only receive the input tile and its unknown mask, so sealing the call is enough here.

A subprocess boundary would also isolate imports and global state. It is not required for the
methods in this repo, which are plain callables over numpy arrays; if a method is added that
needs it, add the subprocess wrapper here rather than widening the runner.
"""
from __future__ import annotations

import contextlib
import os

FLAG = "BLEEDBENCH_INFERENCE"


@contextlib.contextmanager
def sealed():
    """Set BLEEDBENCH_INFERENCE for the duration of a method call, then restore it."""
    prev = os.environ.get(FLAG)
    os.environ[FLAG] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(FLAG, None)
        else:
            os.environ[FLAG] = prev
