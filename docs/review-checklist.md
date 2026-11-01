# bleedBENCH v2.0 — independent review checklist

This checklist is the ground truth for reviewers. The specification under review is `SPEC.md` in the repository root. The original customer brief is private; the requirements it imposes are summarised here. If `SPEC.md` and this checklist disagree, report it; do not edit `SPEC.md` (the Team Lead owns it).

## How to review

- Be adversarial and concrete. Cite section numbers and, where possible, line numbers (`SPEC.md:LNNN`).
- Separate **factual/arithmetic errors** (must fix), **domain errors** (a prepress or ML expert would say it is wrong), **requirements gaps** (the brief demands something that is missing), and **judgement calls** (defensible but debatable).
- Do not rewrite the document. Deliver findings with a recommended one-line fix and evidence.
- Use the review file assigned to you (`reviews/<role>-review.md`); do not touch `SPEC.md` or other reviewers' files.
- Finish with a verdict: `PASS`, `PASS WITH FIXES`, or `FAIL`, and a top-10 severity-ranked list.

## A. Required structure (the brief demands this order)

| # | Required section | Where `SPEC.md` claims it |
|---|---|---|
| A1 | One-page summary | §0 |
| A2 | Critique of v1: right / keep / replace, blunt | §1 (K1–K11, C1–C22) |
| A3 | Task definition: inputs, outputs, scored/not, latent masks, orientation, tile + whole-page | §2 |
| A4 | Data: three tiers, generator spec, validity rules, splits, counts | §3 |
| A5 | Metrics: one subsection per axis A–J; each metric has formula, range, direction, failure threshold, near-perfect sanity baseline, blind spot | §4 |
| A6 | Hallucination + restraint in detail, with and without GT; ≥2 independent approaches; validation against human labels | §5 |
| A7 | Structure continuation in detail: detect, match, angle/offset/width/colour | §6 |
| A8 | Aggregation: tile/edge/page/family/class; means, medians, p90/p99; page = worst tile or argued otherwise; final leaderboard number and why | §7 |
| A9 | Tracks: standard, whole page, robustness, colour, cost, scale; which are required | §8 |
| A10 | Baselines and expected synthetic numbers so a new harness can be checked | §9 |
| A11 | Statistical reporting: family bootstrap 1,000; exact one-sided zero-event bounds; multiplicity; minimum samples | §10 |
| A12 | Reproducibility: seeds, model/weight hashes, hardware, quiet timing, determinism rerun | §11 |
| A13 | Human study: cheap pairwise protocol, print size, seam visible, number of judgments | §12 |
| A14 | Leaderboard/submission: per-tile CSV superset of v1, aggregate JSON, DQ checks | §13 |
| A15 | Open questions, each with the experiment that settles it | §14 |

## B. All ten capability axes must be scored separately

A fidelity; B restraint/non-invention; C seam continuity (with and without GT); D known-pixel integrity; E colour (dE, flat drift, near-white, rich black, CMYK round-trip, spot/wide gamut); F geometry robustness (trim error 1/2/4 px outward, crop marks at 0/9/38 px, partial hidden bleed); G determinism/variance (same seed, seeds, orientation, batch order); H cost (quiet, declared GPU, batch, gain vs edge repeat); I scale (38/60/19 px, 512/1024, whole page); J corners separately.

For each axis check: is it separately scored? Is there at least one metric per required sub-item? Are the thresholds absolute where the brief demands absolute rules?

## C. Per-metric completeness

Every metric row must state all seven: **name; formula; range; direction; failure threshold; sanity baseline that should score near-perfect; what it fails to capture**. Flag any row missing one. The sanity baseline must be plausibly near-perfect (e.g. `gt_copy` for fidelity, `paper_fill` for restraint, `roundtrip_gt` for CMYK). A threshold must be numeric or a rule, not "TBD".

## D. Hard constraints and "do not" list

1. Trim pixels bit-identical; violation = disqualification, not penalty.
2. Severe rule retained as a safety metric; absolute failure rules added that do not depend on candidates.
3. Edge repeat is the reference; every headline table reports delta vs it with a CI.
4. Splits by job family only; sealed test read once, no tuning.
5. Classical and learned methods see identical inputs.
6. No metric may read GT as a run-time feature; label/feature columns separate.
7. Randomness seeded from case id.
8. No single composite score as the only output.
9. No FID/KID as a primary measure.
10. No prompt describing page content in the primary track; unprompted primary if prompted variants exist.
11. Do not assume RGB only: CMYK-native must be scoreable.
12. No tuning on sealed; no run-time feature reads GT.
13. Hallucination metric not hand-waved: if none can be validated, say so and propose the human-label study.

## E. Numerical consistency checks (reviewer must recompute where possible)

- `0.125 in × 300 DPI = 37.5 → 38 px`; `5 mm → 59.06 → 60 px`; `150 DPI → 18.75 → 19`; `600 DPI → 75`.
- `a = (−b) mod 16`: 38→10, 60→4, 19→13, 75→5; `B = b+a`.
- v1 arithmetic: 124 gold pages, 80 usable, 70/53 families; 10 blank + 33 short + 1 small = 44 dropped; 27% drop rate; 1,730 dev tiles = 384+384+372+360+230; 292 sealed.
- v1 audit: 179 + 280 = 459 of 496; 37 edges are neither 0–1 nor ≥30 px — the spec should account for them (NO_INK hypothesis).
- v1 statistics: 0/11 upper bound = 23.8%; 0/48 = 6.05%; 0/80 = 3.68%; 0/299 = 1.00%; 3.35% ±1 pp ≈ 1,244 pages; 3% ±1 pp ≈ 1,118.
- Synthetic mix: 640 pages / 64 families; 50% quiet = 320; material shares among inked edges 58/29/10/2.5/0.7; implied page counts (photo 186, flat 93, clipped 32, pattern 8, text 2) and edge counts (1,284 inked; ~831 FULL, ~453 STOP) — check the arithmetic adds up.
- Tile counts: 28 tiles/page (6×4 edges + 4 corners) → 160 × 28 = 4,480; ×4 orientations = 17,920; 1024 subset 25%.
- Baselines table: `gt_copy` 0; `edge_repeat` best non-learned on flat; `paper_fill` near 0 on B1; analytic gradient MAE `19.5·s` for b=38.
- `sd_refine` cost ratio ≈ 1295/0.5 ≈ 2,590× (brief says ~2,600×).
- Any place where two sections quote different counts or thresholds.

## F. Domain checks (prepress / ML)

Prepress: bleed vs trim vs MediaBox; corner L geometry; trim error is first-order; crop marks are vector and out of scope; paper white vs 245/200 thresholds; pale tints; rich black; TAC; CMYK profile/intent; spot tint ramps; page space vs sRGB; print-size viewing; 300/150/600 DPI physical consistency.

ML/eval: diffusion latent strides 8/16 and mask quantisation; DiT/MMDiT inpainting (FLUX.1 Fill, SD3-class); MAE/ViT masked modelling; CLIP null prompt vs no prompt; per-tile vs whole-page inference; tile compositing; determinism of diffusion samplers; bootstrap clustering; exact binomial bounds; power.

Feasibility: is each metric computable with described inputs? Is the human-labelled validation realistic? Is 100 ms/512 tile plausible for the named models? Does the synthetic generator spec suffice to build without questions?

## G. Review file format

```markdown
# <role> review — bleedBENCH v2.0
Verdict: PASS | PASS WITH FIXES | FAIL
## Top findings (severity order)
| # | Severity | Location | Finding | Evidence / recomputation | One-line fix |
## Detailed notes
...
## Checks performed
- [x] ...
```

Severity: **S1** wrong claim/factual error/requirement violation; **S2** domain error or unscorable metric; **S3** ambiguity/unbuildable detail; **S4** style/judgement.

## H. Non-goals

Do not ask for implementation code, a working harness, new customer data, or changes to the v1 numbers. Do not re-litigate the task; audit the spec against the brief.
