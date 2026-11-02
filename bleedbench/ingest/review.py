"""Manual review support: a private contact sheet, and the decision loader.

The human fills the `decision` column of _private/review/pii_queue.csv with include / exclude /
include_no_export. Rows left blank are treated as NOT reviewed, and such files enter no split.
"""
from __future__ import annotations

import csv
import html
from pathlib import Path

import pymupdf
from PIL import Image

from ..config import private_dir
from . import inventory

VALID = {"include", "exclude", "include_no_export"}
THUMB_PX = 360


def _thumb(abspath: str, ext: str, out: Path) -> None:
    if out.exists():
        return
    if ext == ".pdf":
        with pymupdf.open(abspath) as doc:
            pg = doc[0]
            z = THUMB_PX / max(pg.rect.width, pg.rect.height)
            pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False).save(out)
    else:
        with Image.open(abspath) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_PX, THUMB_PX))
            im.save(out)


def contact_sheet() -> Path:
    rev = private_dir("review")
    thumbs = private_dir("review", "thumbs")
    by_sha = {r["sha256"]: r for r in inventory.load()}
    rows = list(csv.DictReader(open(rev / "pii_queue.csv", encoding="utf-8-sig")))
    cells = []
    for r in rows:
        inv = by_sha[r["sha256"]]
        t = thumbs / f"{r['sha256'][:16]}.png"
        try:
            _thumb(inv["abspath"], inv["ext"], t)
            img = f'<img src="thumbs/{t.name}" loading="lazy">'
        except Exception as e:
            img = f"<div class=err>render failed: {html.escape(type(e).__name__)}</div>"
        cls = "ex" if r["suggested"] == "exclude" else "in"
        cells.append(
            f'<figure class={cls}>{img}<figcaption><b>{html.escape(r["suggested"])}</b> '
            f'{html.escape(r["why"])} {html.escape(r["pii"])}<br>{html.escape(r["relpath"])}'
            f'<br><code>{r["sha256"][:16]}</code></figcaption></figure>')
    page = rev / "contact_sheet.html"
    page.write_text(
        "<!doctype html><meta charset=utf-8><title>bleedbench review</title><style>"
        "body{font:12px system-ui;margin:16px;background:#fafafa}"
        "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}"
        "figure{margin:0;background:#fff;border:2px solid #ccc;padding:6px}"
        "figure.ex{border-color:#c33}img{max-width:100%;max-height:300px;display:block;margin:auto}"
        "figcaption{word-break:break-all;margin-top:4px}</style>"
        "<h1>Private review sheet: fill the decision column in pii_queue.csv</h1><main>"
        + "\n".join(cells) + "</main>", encoding="utf-8")
    return page


def decisions() -> dict[str, str]:
    """sha256 -> decision, only for reviewed rows."""
    path = private_dir("review") / "pii_queue.csv"
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        d = r.get("decision", "").strip().lower()
        if d:
            if d not in VALID:
                raise ValueError(f"invalid decision {d!r} for {r['sha256'][:16]}")
            out[r["sha256"]] = d
    return out


def merge_previous(new_path: Path, old_rows: list[dict]) -> None:
    """Keep human decisions when the queue is regenerated."""
    keep = {r["sha256"]: (r.get("decision", ""), r.get("note", "")) for r in old_rows}
    rows = list(csv.DictReader(open(new_path, encoding="utf-8-sig")))
    for r in rows:
        if r["sha256"] in keep:
            r["decision"], r["note"] = keep[r["sha256"]]
    with open(new_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def accept_suggested() -> int:
    """Copy `suggested` into empty `decision` cells. Run only after a human has looked at the
    contact sheet; any decision already filled in is kept."""
    path = private_dir("review") / "pii_queue.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    n = 0
    for r in rows:
        if not r.get("decision", "").strip():
            r["decision"] = r["suggested"]
            r["note"] = (r.get("note", "") + " accepted-suggestion").strip()
            n += 1
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return n
