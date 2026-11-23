# bleedBENCH

A benchmark for **generative bleed extension in print production**: can an image model fill the 0.125 in (≈38 px at 300 DPI) bleed ring outside a page's trim line without touching the trim, without inventing content, without a visible seam, and in the page's own colour space?

This repository holds the **v2.1 specification** and its **reference harness** (`bleedbench/`). v2.1 is the first revision measured on real print jobs: a private print-shop corpus (Tier C0) was ingested, privacy-screened, rendered, labelled, split by client family and used for calibration, training and a dev table. The corpus itself, and everything derived from it except k-anonymous aggregates, never leaves the machine.

## Read this first

- **[`SPEC.md`](SPEC.md)** — the specification. Start with §0 (summary) and **§0.1 (what v2.1 changes and why)**, then §1 (v1 critique) and §1.3 (new pitfalls once a real corpus is used for training).
- **[`HANDOFF.md`](HANDOFF.md)** — current state, results, and what to do next.
- **[`aggregates/`](aggregates/)** — the only corpus-derived files in the repo: k-anonymous (≥ 5 families per cell) census and dev-table JSON, validated by `bleedbench.privacy.validate_export`.
- **[`reviews/`](reviews/)** — independent audits of v2.0.
- **[`tools/verify_spec_numbers.py`](tools/verify_spec_numbers.py)** — recomputes every arithmetic claim in the spec, including the C0 census consistency checks.

## What changed in v2.1 (short)

- **STOP edges are missing bleed, not restraint.** On real print-ready files, art that ends exactly at the trim is a prepress defect the shop wants extended; v2.0 scored "paper" as correct there. Restraint is now scored where the trim is paper (NO_INK).
- **D1/D2 contradiction fixed** — full-image models are no longer disqualified for regenerating pixels they then composite away.
- **V12**: a 0.125 in BleedBox is 37.5 px at 300 DPI; only the 37 whole pixels are scored.
- **Measured priors and design effects** replace v2.0's assumptions where the data are precise enough (quiet pages 27% not 50%; tile design effect 12.9 not 2.35).
- **Leakage controls for corpus-trained models**: evidence-based client families, train/dev/gate-fit partitions, training manifests, no unpickling of weights.

## The harness

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .[ml,dev]     # Windows; use .venv/bin/python elsewhere
.venv/Scripts/python -m pytest                        # public tests (no corpus needed)
python tools/verify_spec_numbers.py
```

With a private corpus (set `BLEEDBENCH_CORPUS`; outputs go to the gitignored `_private/`):

```bash
python -m bleedbench init-salt
python -m bleedbench ingest
python -m bleedbench probe
python -m bleedbench review          # build the private contact sheet; fill decisions by hand
python -m pytest -m private          # leakage tests: families, near-duplicates, reviewed-only
```

Layout:

```text
bleedbench/ingest     inventory, exclusions, PII screen, review queue
bleedbench/render     trim-aligned PDF rendering (V1, V11, V12)
bleedbench/label      ink test, hidden-bleed depth and class, vector material census, V13
bleedbench/families.py, splits.py, census.py
bleedbench/geometry.py, colour.py, features.py
bleedbench/baselines  classical fills (BL0–BL7), big-LaMa (BL9, safetensors)
bleedbench/harness    tile runner, metrics A–D, frozen oracle, aggregation, gate protocol, stats
bleedbench/bleedgen.py  procedural Tier A pages with census-fitted priors
bleedbench/train      strip U-Net (residual over edge repeat), LaMa FFC port, training, gates
tools/check_no_private.py   pre-commit guard against corpus-derived files
```

## Privacy

`_corpus/`, `_private/`, images, PDFs, archives and weights are gitignored. `tools/check_no_private.py` blocks staged files from private paths, binary types, files over 2 MB, and any token listed in the private token file. Exports pass a schema allowlist (no paths, names or free text; every cell ≥ 5 families). Family and case ids are HMAC-SHA256 with a salt that is never exported.

## Licence

Apache-2.0. See [`LICENSE`](LICENSE). big-LaMa weights (Apache-2.0) are downloaded by the user and pinned by SHA-256; no weights are distributed here.
