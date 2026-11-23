"""Merged run CSVs carry one block per page even after a re-partitioned resume."""
import csv

from bleedbench.harness import run as R


def _write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _row(pid, method, fields):
    return {k: "" for k in fields} | {"track": "t", "split": "s", "page_id": pid, "method": method,
                                      "orientation": 0}


def test_merge_keeps_one_block_per_page(tmp_path):
    fields = R._FIELDS
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    _write(a, [_row("p1", "m1", fields), _row("p1", "m2", fields), _row("p2", "m1", fields)], fields)
    _write(b, [_row("p1", "m1", fields), _row("p1", "m2", fields)], fields)   # stale duplicate
    out = tmp_path / "out.csv"
    R._merge_parts([str(a), str(b)], out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["page_id"] for r in rows] == ["p1", "p1", "p2"]
