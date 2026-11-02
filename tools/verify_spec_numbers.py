#!/usr/bin/env python3
"""Verify the arithmetic claims in SPEC.md.

Not a benchmark harness. This script recomputes the numbers the spec uses for
sample-size planning, geometry and census arithmetic, and fails loudly if the
document and the math disagree. Run from the repo root:

    python tools/verify_spec_numbers.py
"""

from __future__ import annotations

import math
import sys

FAILS: list[str] = []


def check(name: str, got, want, tol=1e-9) -> None:
    ok = abs(got - want) <= tol if isinstance(got, (int, float)) else got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got={got!r} want={want!r}")
    if not ok:
        FAILS.append(name)


def binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Clopper-Pearson one-sided upper bound: smallest p with P(X<=k;p) <= alpha."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if binom_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def n_halfwidth(p: float, hw: float, z: float = 1.959963984540054) -> int:
    return math.ceil(z * z * p * (1 - p) / (hw * hw))


def v21_checks() -> None:
    """v2.1 additions: V12 scored ring, C0 census consistency, achieved C0 bounds."""
    import json
    from pathlib import Path
    # V12: 0.125 in at 300 DPI is 37.5 px; b rounds up (38), the scored ring rounds down (37)
    check("v12 bleed px 0.125in@300", 9.0 * 300 / 72, 37.5)
    check("v12 scored 0.125in@300", min(38, math.floor(9.0 * 300 / 72)), 37)
    check("v12 scored 0.25in@300", min(38, math.floor(18.0 * 300 / 72)), 38)
    check("v12 scored 0.125in@150", min(19, math.floor(9.0 * 150 / 72)), 18)
    agg = Path(__file__).resolve().parent.parent / "aggregates"
    c = agg / "census_c0.json"
    if not c.exists():
        print("SKIP  census_c0.json not present")
        return
    cen = json.loads(c.read_text(encoding="utf-8"))
    dep = cen["deployment"]
    for key in ("size", "colour", "rotation", "orientation"):
        tot = sum(v["p"] for v in dep[key].values() if not v.get("suppressed"))
        check(f"census {key} shares sum to 1", round(tot, 3), 1.0, tol=0.002)
    real = cen["real_gt_non_test"]
    sh = sum(v["p"] for v in real["material_share_inked"].values() if not v.get("suppressed"))
    check("census inked material shares sum to 1", round(sh, 3), 1.0, tol=0.002)
    cc, dh = real["edge_class_counts"], real["depth_q90_hist"]
    check("census depth hist == FULL+STOP+NO_INK edges", sum(dh.values()), sum(cc.values()))
    check("census depth gap 2-29 empty (bimodality)", dh.get("2-29", 0), 0)
    check("census p_full_given_inked n == FULL+STOP", real["p_full_given_inked"]["n"],
          cc.get("FULL", 0) + cc.get("STOP", 0))
    for f in agg.glob("*.json"):
        def walk(o):
            if isinstance(o, dict):
                if "n_families" in o and not o.get("suppressed"):
                    assert o["n_families"] >= 5, f"{f.name}: k-anonymity breach"
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(f.read_text(encoding="utf-8")))
    check("aggregates k-anonymity (n_families >= 5)", True, True)
    d = agg / "dev_c0.json"
    if d.exists():
        dev = json.loads(d.read_text(encoding="utf-8"))
        des = dev["design"]
        check("dev DE_tile = 1+(m-1)ICC", round(1 + (des["tiles_per_page"] - 1) * des["icc_tile"], 2),
              round(des["de_tile"], 2), tol=0.02)
        check("dev DE_page = 1+(m-1)ICC", round(1 + (des["pages_per_family"] - 1) * des["icc_page"], 2),
              round(des["de_page"], 2), tol=0.02)
        b = dev["achieved_bounds_test"]
        check("C0 test zero-event UB (pages, raw)", round(cp_upper(0, b["pages"]), 4),
              b["zero_event_ub95_pages_raw"], tol=2e-4)


def main() -> int:
    # Geometry
    check("b 0.125in@150", math.ceil(0.125 * 150), 19)
    check("b 0.125in@300", math.ceil(0.125 * 300), 38)
    check("b 0.125in@600", math.ceil(0.125 * 600), 75)
    check("b 5mm@300", math.ceil(5 / 25.4 * 300), 60)
    for b, a in [(19, 13), (38, 10), (60, 4), (75, 5)]:
        check(f"apron a for b={b}", (-b) % 16, a)
        check(f"band B for b={b}", b + a, b + ((-b) % 16))
        check(f"512 known for b={b}", 512 - (b + a), 512 - b - a)
        check(f"1024 known for b={b}", 1024 - (b + a), 1024 - b - a)

    # v1 arithmetic
    check("v1 usable pages", 124 - 10 - 33 - 1, 80)
    check("v1 drop rate %", round(33 / 124 * 100, 1), 26.6)
    check("v1 dev tiles", 384 + 384 + 372 + 360 + 230, 1730)
    check("v1 edge accounting", 179 + 280, 459)
    check("v1 unaccounted edges", 496 - (179 + 280), 37)
    check("sd_refine cost ratio", round(1295 / 0.5), 2590)

    # Zero-event bounds
    for n, pct in [(11, 23.8), (48, 6.05), (80, 3.68), (89, 3.31), (160, 1.85),
                   (292, 1.02), (299, 1.00), (300, 0.99), (320, 0.93), (1000, 0.30),
                   (1300, 0.23)]:
        check(f"0/{n} upper bound %", round(cp_upper(0, n) * 100, 2), pct, tol=0.05)

    # Design-effect-adjusted gate sizes
    check("Gate A accepted tiles at DE 2.35", math.ceil(299 * 2.35), 703)
    check("Gate B accepted tiles at DE 2.35", math.ceil(89 * 2.35), 210)
    check("page-level accepted at DE 1.11", math.ceil(299 * 1.11), 332)
    check("350-page effective n at DE 1.11", round(350 / 1.11, 1), 315.3)
    check("350-page zero-event UB %", round(cp_upper(0, round(350 / 1.11)) * 100, 2), 0.95, tol=0.05)

    # Sample sizes
    check("3% +/-1pp", n_halfwidth(0.03, 0.01), 1118)
    check("3.35% +/-1pp", n_halfwidth(0.0335, 0.01), 1244)
    check("3.35% +/-0.5pp", n_halfwidth(0.0335, 0.005), 4976)
    check("3% +/-0.5pp", n_halfwidth(0.03, 0.005), 4472)
    check("1% +/-0.5pp", n_halfwidth(0.01, 0.005), 1522)

    # Two-proportion (80% power, two-sided 5%)
    def n_two(p1: float, p2: float) -> int:
        za, zb = 1.959963984540054, 0.8416212335729143
        pbar = (p1 + p2) / 2
        return math.ceil(
            (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
            / (p2 - p1) ** 2
        )

    check("2% vs 1% per group", n_two(0.01, 0.02), 2319)
    check("3% vs 2% per group", n_two(0.02, 0.03), 3826)
    check("4.35% vs 3.35% per group", n_two(0.0335, 0.0435), 5810)

    # MAE power (two-sided, 80%)
    def n_mae(sd: float, delta: float) -> int:
        return math.ceil(((1.959963984540054 + 0.8416212335729143) * sd / delta) ** 2)

    check("MAE sd20 delta2.5", n_mae(20, 2.5), 503)
    check("MAE sd15 delta2.5", n_mae(15, 2.5), 283)
    check("MAE sd15 delta1.0", n_mae(15, 1.0), 1766)

    # Synthetic population arithmetic
    check("synthetic pages", 320 + 185 + 93 + 32 + 8 + 2, 640)
    check("inked edges", (185 + 93 + 32 + 8 + 2) * 4, 1280)
    check("full edges", 370 + 298 + 128 + 29 + 4, 829)
    check("stop edges", 370 + 74 + 3 + 4, 451)
    check("full+stop", 829 + 451, 1280)
    check("page content classes", 250 + 147 + 211 + 32, 640)
    check("material shares %",
          round((740 / 1280 + 372 / 1280 + 128 / 1280 + 32 / 1280 + 8 / 1280) * 100, 1), 100.0)
    check("image share %", round(740 / 1280 * 100, 1), 57.8)
    check("quiet share %", round(320 / 640 * 100, 1), 50.0)
    check("edge class FULL %", round(829 / 2560 * 100, 1), 32.4)
    check("edge class STOP %", round(451 / 2560 * 100, 1), 17.6)

    # Weights
    w = [0.500, 0.289, 0.145, 0.050, 0.013, 0.003]
    check("production weights sum", round(sum(w), 4), 1.0)
    check("normalised first weight", round(w[0] / sum(w), 3), 0.5)

    # Tiles
    check("test tiles 512", 160 * 28, 4480)
    check("test tile-runs 4 orientations", 160 * 28 * 4, 17920)
    check("test tiles 1024 25%", int(160 * 20 * 0.25), 800)

    # Analytic gradient MAE for edge_repeat, b=38: mean distance 1..38
    check("edge-repeat gradient MAE slope", sum(range(1, 39)) / 38, 19.5)

    # Colour floors are reported, not asserted here; check threshold ordering only.
    check("flat dE fail > warn", 2.0 > 1.0, True)
    check("seam dE fail < seam step fail", 1.0 < 2.0, True)

    print()
    v21_checks()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("All spec arithmetic checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
