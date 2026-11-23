"""The inference guard seals the label store for the duration of a method call."""
import os

import pytest

from bleedbench.harness import learned
from bleedbench.store import LabelAccessDuringInference, LabelStore


def test_sealed_sets_and_restores_the_flag(monkeypatch):
    monkeypatch.delenv(learned.FLAG, raising=False)
    with learned.sealed():
        assert os.environ[learned.FLAG] == "1"
        with pytest.raises(LabelAccessDuringInference):
            LabelStore()
    assert learned.FLAG not in os.environ
