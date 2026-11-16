"""Separate input and label stores (SPEC V10 label isolation).

InputStore holds what a method may see: page canvases with every pixel outside the trim set to 0.
LabelStore holds GT canvases and labels. Opening the LabelStore while BLEEDBENCH_INFERENCE=1 is
set raises, so inference subprocesses cannot read labels even by accident.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

from .config import private_dir

Image.MAX_IMAGE_PIXELS = None


class LabelAccessDuringInference(PermissionError):
    pass


def _save_png(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(path, compress_level=3)


def _load_png(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB")).copy()


class InputStore:
    def __init__(self, root: Path | None = None):
        self.root = root or private_dir("input_store")

    def put(self, key: str, gt_canvas: np.ndarray, W: int, H: int, B: int, meta: dict) -> None:
        inp = np.zeros_like(gt_canvas)
        inp[B:B + H, B:B + W] = gt_canvas[B:B + H, B:B + W]
        _save_png(inp, self.root / f"{_fn(key)}.png")
        (self.root / f"{_fn(key)}.json").write_text(json.dumps({"W": W, "H": H, "B": B, **meta}))

    def get(self, key: str) -> tuple[np.ndarray, dict]:
        return _load_png(self.root / f"{_fn(key)}.png"), self.meta(key)

    def meta(self, key: str) -> dict:
        return json.loads((self.root / f"{_fn(key)}.json").read_text())

    def has(self, key: str) -> bool:
        return (self.root / f"{_fn(key)}.png").exists()


class LabelStore:
    def __init__(self, root: Path | None = None):
        if os.environ.get("BLEEDBENCH_INFERENCE") == "1":
            raise LabelAccessDuringInference("label store is not available during inference")
        self.root = root or private_dir("label_store")

    def put(self, key: str, gt_canvas: np.ndarray, padded: np.ndarray, labels: dict) -> None:
        _save_png(gt_canvas, self.root / f"{_fn(key)}.png")
        np.save(self.root / f"{_fn(key)}.padded.npy", np.packbits(padded, axis=None))
        (self.root / f"{_fn(key)}.json").write_text(json.dumps(labels))

    def gt(self, key: str) -> np.ndarray:
        return _load_png(self.root / f"{_fn(key)}.png")

    def padded(self, key: str, shape: tuple[int, int]) -> np.ndarray:
        bits = np.load(self.root / f"{_fn(key)}.padded.npy")
        return np.unpackbits(bits)[: shape[0] * shape[1]].reshape(shape).astype(bool)

    def labels(self, key: str) -> dict:
        return json.loads((self.root / f"{_fn(key)}.json").read_text())

    def has(self, key: str) -> bool:
        return (self.root / f"{_fn(key)}.json").exists()


def _fn(key: str) -> str:
    return key.replace(":", "_")
