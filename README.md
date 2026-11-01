# bleedBENCH

A benchmark specification for **generative bleed extension in print production**: can an image transformer (diffusion transformer inpainting/outpainting, masked-image-modelling ViT) fill the 0.125 in / 38 px bleed ring outside a page's trim line without touching the trim, without inventing content, without a visible seam, and in the page's own colour space?

This repository currently contains the **v2.0 specification**, not a harness implementation.

## Read this first

- **[`SPEC.md`](SPEC.md)** — the full benchmark specification. Start with the one-page summary (§0), then the v1 critique (§1). Every metric and design decision is numbered for review.
- **[`docs/review-checklist.md`](docs/review-checklist.md)** — the requirements checklist used for independent review, including the full axis A–J and per-metric completeness matrix.
- **[`reviews/`](reviews/)** — independent audits of the specification (statistics, prepress/metric semantics, requirements compliance).
- **[`tools/verify_spec_numbers.py`](tools/verify_spec_numbers.py)** — recomputes every arithmetic claim in the spec (geometry, sample sizes, exact bounds, census counts, v1 arithmetic). Run it before trusting a table.

## What the benchmark decides

A production system always has a deterministic fallback (edge repeat) and a confidence flag; the benchmark decides whether a generative model ever gets routed to. The primary endpoint is therefore not a quality composite but a production quantity, `SystemGain`: average page MAE saved by routing to the model behind its own calibration-frozen confidence gate, with edge repeat as fallback. All ten capability axes (fidelity, restraint, seam continuity, known-pixel integrity, colour, geometry robustness, determinism, cost, scale, corners) are reported separately before that number.

Hard gates: trim pixels bit-identical; declared page colour space respected; deterministic same-seed rerun; family-disjoint splits; no ground-truth leakage into run-time features.

## Status

- Version: **2.0** (protocol-freeze candidate), supersedes medic v1 (2026-10-27).
- The private corpus is not in this repository and will not be; Tier A (public synthetic) and Tier B (public permissive real) are specified, not yet generated.
- Thresholds marked *provisional* are frozen only after the calibration run and before the sealed test is opened.

## Repository layout

```text
SPEC.md                      # the specification
README.md                    # this file
docs/review-checklist.md     # review / acceptance checklist
reviews/                     # independent review reports
tools/verify_spec_numbers.py # arithmetic self-check (Python 3, stdlib only)
LICENSE                      # Apache-2.0
```

## Running the arithmetic checks

```bash
python tools/verify_spec_numbers.py
```

The script uses only the Python standard library. It is a documentation check, not the benchmark harness.

## Licence

Apache-2.0. See [`LICENSE`](LICENSE). The synthetic generator, public real tier and harness, when built, will carry their own asset licences (CC0 for generated pages; permissive licences recorded per page for the real tier).
