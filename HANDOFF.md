# Handoff — bleedBENCH v2.0 specification

**Date:** 2026-11-01 · **State:** protocol-freeze candidate, independently audited, S1 findings integrated. Not yet frozen; no harness implemented.

## What exists

| Path | Purpose |
|---|---|
| `SPEC.md` | The complete benchmark specification (~27.5k words, 1,556 lines): one-page summary, v1 critique, task definition, three data tiers, metrics A–J, hallucination/restraint, structure continuation, aggregation, tracks, baselines, statistics, reproducibility, human study, leaderboard/schema, open questions, decision log. |
| `docs/review-checklist.md` | Requirements checklist used by the independent audits (structure, axes, per-metric fields, hard constraints, do-nots, numerical checks). |
| `reviews/stats-review.md` | Independent statistical audit (revision 1), plus post-fix verification addendum. |
| `reviews/prepress-review.md` | Independent prepress/colour/metric audit (revision 1), plus post-fix verification addendum. |
| `reviews/compliance-review.md` | Independent requirements audit (revision 1), plus post-fix verification addendum. |
| `tools/verify_spec_numbers.py` | Recomputes geometry, sample sizes, exact bounds, census arithmetic and v1 numbers used in the spec. Stdlib only. |
| `README.md` | Repository entry point. |

Run:

```powershell
python tools/verify_spec_numbers.py
```

Expected: `All spec arithmetic checks passed.` (last run: 2026-11-01, pass).

## What was fixed after audit

Three audits (stats FAIL, prepress FAIL, compliance PASS WITH FIXES) were run on revision 1. Their S1s were integrated, then re-verified by the compliance and prepress auditors (both PASS WITH FIXES / PASS on S1s). Key fixes:

- **Whole-page latent alignment:** claims scoped to what is achievable; right/bottom seam remainder `r = W mod 16` is stated, measured by D5/D6. Tile windows are seam-anchored, so 464/976 known bands hold.
- **SystemGain:** one page-level definition (§0/§7.4/§7.6); no tile-weighted variant; gate remains tile-level with page acceptance = all tiles.
- **Gate statistics:** 50/50 calibration selection/certification; DE-adjusted Clopper-Pearson bounds; Gate A ≥703 accepted tiles, Gate B ≥210 at DE 2.35; private 350-page acceptance set, 0.95% zero-event UB; 1,300-page annual set supports ±1.03–1.06 pp, not a nominal ±1 pp.
- **SCS/C4:** no-line tiles are `n/a`; per-line tolerances are the operative pass rule; SCS is ranking-only; occlusion exclusion detected on frozen GT and capped.
- **Data arithmetic:** STOP/FULL derivation from conditional probabilities; 829/451 integers pinned; texture test oversample 2× (8/8/16), full-set balance test; 1,200-strip hallucination set (400+400+400, 200 ambiguous subset).
- **Metrics:** A1/A2/C3 thresholds above edge-repeat means; B5 per 1,000 tiles net of FPR; E6 scores model handling of out-of-gamut pixels; E3 net of rich-black round-trip floor; E4 two-sided; D1 raw pre-clamp + D1b final; ΔE00 in ICC PCS D50 via Bradford; paper estimate no longer trusts full-bleed ring.
- **Cost:** H2 ≤3.5 s/page at 512, ≤2.5 s at 1024; FLUX cost 800–2,500 ms; quiet protocol.
- **Human study:** 60 accept/reject/unsure strips + 300 pairs, print-size zoom formula, loupe, CMYK soft proof, ~5 rater-hours; threshold settings directional, press study O6 sets values.
- **Schema:** v1 superset retained (133 columns, all 22 v1 columns present); added line/text coverage, per-seam regen, D1b, paper confidence/source, final trim identity.

## Known residual items (non-blocking, but fix before freeze if time)

1. **PDF render region/MediaBox** for real Tier B/C pages is still not defined in the spec; render = BleedBox dilated by apron (clipped to MediaBox), pad missing pixels with paper. Needed for buildability.
2. **C8 four-pass models:** if a model runs whole-page inference as four seam-anchored passes, C8's "single pass vs composite" comparison is n/a; state this explicitly and score C7 only.
3. **Texture σ range** in §10.4 is quoted as σ≈15–20 for texture; pin the measured value at calibration.
4. **R1/R2 sourcing:** 44.29/45.96 and 59% come from v1 aggregates; cite the frozen private aggregate file at freeze.
5. **SD3-class baseline** is a constructed pipeline, not an official checkpoint; the exact adapter/derivation must be named at freeze.
6. **CP-DE approximation:** design-effect-adjusted Clopper-Pearson is an approximation, not a hierarchical model; report the cluster bootstrap beside it and label the certificate `CP-DE`.
7. **Synthetic joint assumption (A1):** 50/50 hidden bleed on image edges is an assumption; O1's 1,000-page audit settles it.
8. **Judge N1:** judge training generator pool is now declared disjoint from human-labelled model strips, but leave-one-generator-out for a genuinely unseen submission generator still requires the advisory fallback; keep that rule.

## What to do next (in order)

1. **Re-audit current revision** (`SPEC.md` SHA recorded at commit) with the same three reviewers; freeze only after no S1 and the residual list above is closed or explicitly accepted.
2. **Build `bleedgen`** from §3.1; implement the acceptance tests, especially the census and class-balance tests.
3. **Implement the reference harness** (`bleedbench verify`): §9.3 analytic tests, 400-tile stratified check set, oracle file, v1 legacy mode, schema validator.
4. **Freeze** `splits.json`, `synthetic_manifest.json`, `lite.json`, `robustness_manifest.json`, `oracle.json`, `expected_baselines.json`, `expected_baselines` with SHA-256s, then open the sealed test once.
5. **Run the press study (O6)** for flat-drift/rich-black thresholds before freezing A6/B1 numbers.
6. **Tier B sourcing:** licence-verified PDFs (CC0/PD/CC-BY), 300 pages / 100 families target; 120/40 minimum.
7. **Private harness:** v1-compatible aggregate export, 350-page acceptance set per submission; do not export images or job data.

## Freeze checklist

- [ ] no S1 in the re-audit; residual list accepted
- [ ] `python tools/verify_spec_numbers.py` passes
- [ ] spec SHA recorded in `reviews/` addenda
- [ ] all provisional thresholds marked and frozen
- [ ] sealed test unopened
- [ ] v1 legacy regression reproduced (±5%)
- [ ] schema validator passes the 133-column superset
- [ ] `SystemGain` reproducible from the per-tile CSV alone (`page_mae`/`system_mae`)

## Commit

The commit for this handoff contains `SPEC.md`, `README.md`, `docs/`, `reviews/`, `tools/`, and this file. No private customer data, no model weights, no harness implementation.
