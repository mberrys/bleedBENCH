# bleedBENCH v2.1 — Benchmark specification for generative bleed extension in print production

**Status:** v2.1 draft, 2026-11-01 · **Supersedes:** v2.0 (protocol-freeze candidate) and medic benchmark v1 (run 2026-10-27) · **Deliverable:** specification plus the reference harness in `bleedbench/` and a first private pilot tier (C0). The v2.1 amendments are listed in §0.1 and override any conflicting v2.0 text below; every amendment has a decision-log entry (DD67–DD85).

**Audit status.** Revision 1 was independently audited by three reviewers (`reviews/stats-review.md`, `reviews/prepress-review.md`, `reviews/compliance-review.md`). Their S1 findings are integrated in this revision: whole-page latent alignment is now restricted to the seams it can actually align and the right/bottom remainder is measured; SCS has an explicit no-line convention; SystemGain is defined once at page level; the gate is selected and certified on disjoint calibration halves with design-effect-adjusted bounds; the 1,200-strip hallucination set, B5 unit, cost gates, texture oversampling and page-level 1% sample algebra are corrected. Residual S2/S3 items (e.g. merged report-only rows, the exactness of the CP-DE approximation, the synthetic joint assumption) are recorded in those reviews and in §14 rather than silently dropped.

**Normative words:** MUST, SHOULD, MAY are used in the RFC sense. A submission that violates a MUST fails qualification; it is not merely penalised.

**Companion files:** `README.md` (repository entry point), `docs/review-checklist.md` (requirements-to-spec checklist), `reviews/` (independent audits). The private corpus and all v1 job data remain private; this document contains only aggregates already disclosed in the v1 brief.

---

## Table of contents

0. [One-page summary](#0-one-page-summary)
1. [Critique of v1](#1-critique-of-v1)
2. [Task definition](#2-task-definition)
3. [Data](#3-data)
4. [Metrics, axes A–J](#4-metrics-axes-aj)
5. [Hallucination and restraint metrics in detail](#5-hallucination-and-restraint-metrics-in-detail)
6. [Structure-continuation metric in detail](#6-structure-continuation-metric-in-detail)
7. [Aggregation](#7-aggregation)
8. [Tracks](#8-tracks)
9. [Baselines and numbers to beat](#9-baselines-and-numbers-to-beat)
10. [Statistical reporting](#10-statistical-reporting)
11. [Reproducibility](#11-reproducibility)
12. [Human study](#12-human-study)
13. [Leaderboard and submission format](#13-leaderboard-and-submission-format)
14. [Open questions](#14-open-questions)
15. [Appendix A — decision log](#appendix-a--decision-log)
16. [Appendix B — constants and derived geometry](#appendix-b--constants-and-derived-geometry)

---

## 0. One-page summary

Bleed is the strip of artwork outside the trim line that survives a cutting error. The default is 0.125 in (3.175 mm), 38 px at 300 DPI, and the ring is L-shaped at each corner. bleedBENCH scores a model that receives a print-resolution page render with the bleed ring missing and must fill it, while every pixel inside the trim remains bit-identical. It is a **fidelity-and-restraint** benchmark, not a distribution-matching benchmark: pixel-exact ground truth exists for the strip, and a wrong invention is a production defect even when it is photorealistic.

**What v2 changes, in one line each.** Every page is scored as a whole 38 px ring, not only as isolated tiles; the unknown band is padded outward to 48 px on a 16 px grid so latents do not straddle the trim line on tile-mode and left/top whole-page seams (the unavoidable right/bottom whole-page remainder is measured, not assumed away); the 33 “art stops at the trim” pages v1 discarded become the scored **restraint** class; absolute per-class failure rules sit beside the oracle-relative severe rule; hallucination, structure continuation, flat-colour drift, rich black and CMYK round-trip become first-class metrics; the private corpus is joined by a public synthetic tier and a public permissively licensed real tier; cost is measured quiet; and every interval is a family-cluster bootstrap or an exact one-sided bound where events are zero.

**Primary endpoint — a production quantity, not a quality composite.** Let `M_ref` be edge-repeat and `M_m` the submitted method. A submission supplies a run-time confidence score computed **only** from input/known pixels. The harness selects the gate threshold on one calibration half and certifies it on the other, then applies it unchanged to the sealed test: Gate A requires the one-sided, design-effect-adjusted 95% upper bound on **accepted-tile** severe rate to be ≤1%, Gate B only non-inferiority to edge repeat (≤3.35%). Page-level ≤1% is certified separately on the private 350-page acceptance set, where the unit is a page. The headline is

```text
page_MAE(m,p) = q90 of tile MAE over page p                       (page_fidelity, §7.4)
SystemGain(m) = Σ_p w_p · [ page_MAE(M_ref,p) − page_MAE(M_system,p) ] / Σ_p w_p
M_system(p)   = M_m(p) if every sampled tile of p is accepted by the gate, else M_ref(p)
```

This is the average page MAE the benchmark saves by routing to the model instead of the deterministic fallback. Rejecting everything yields 0, not a win; a model with poor coverage but a large gain can still rank, and coverage is reported next to the gain. It is a single number for ordering, never the only output: all ten axes, gates, tails and costs are published alongside.

**Hard gates (disqualification, not penalty).** Raw and final trim pixels bit-identical to the input; declared output colour space and profile respected; same-seed rerun bit-identical (or an explicitly stochastic entry, reported separately and barred from the production-candidate badge); no label column used by any run-time feature or gate; required tracks present; family-disjoint splits; weights and environment hashed. See §13.4.

**Tracks required for a leaderboard entry:** standard tile fidelity (T1), whole-page ring (T2), restraint/hallucination (T3), colour (T5), cost (T6), determinism (part of every submission). Robustness (T4) is required for the “production router candidate” badge; scale (T7) for the “general-purpose” badge; prompted variants are a diagnostic only (T8).

**What it will not tell you.** It cannot tell you whether a model is safe on *all* print jobs: the private tier is needed for that, and the public tiers are calibration and leaderboard instruments. It cannot replace a press proof for a new spot colour or substrate. It cannot validate a model that was trained on the public sealed test; that is an honour-system plus canary-and-audit problem, not a metric problem.

| Capability | Primary instrument | Hardest part |
|---|---|---|
| A Fidelity | A1–A7, page ring | GT is private; synthetic GT is not real photos |
| B Restraint | STOP/NO_INK classes, B1–B9 | “Correct answer is paper” has no positive content to score |
| C Seam continuity | C1–C8, structure/text continuation | Continuation detection is itself an estimator |
| D Known-pixel integrity | D1/D1b gates, D2–D6 clamp seam | Latent-resolution masks regenerated trim pixels |
| E Colour | E1–E8, CMYK round-trip | sRGB→CMYK round-trip floor exists even for GT |
| F Geometry robustness | F1–F6 | Trim error is first-order; v1 shows 7× MAE inflation at 2 px |
| G Determinism | G1–G4 | Diffusion samplers are only reproducible with fixed seed/backend |
| H Cost | H1–H4, quiet protocol | v1 timings were under load |
| I Scale | I1–I6 | 1024 px and whole page blow up compute |
| J Corners | J1–J5 | Two edges must agree; v1 corner tiles were scored alone |

## 0.1 What v2.1 changes (normative amendments)

v2.1 is the first revision written against real data: a private print-shop corpus ("Tier C0", §3.3a) ingested, privacy-screened, rendered, labelled and split by the reference harness in `bleedbench/`. Each amendment below overrides conflicting v2.0 text and has a decision-log entry.

| # | Amendment | Why (measured on C0 unless stated) | DD |
|---|---|---|---|
| M1 | **STOP is missing bleed, not restraint.** STOP edges have no fidelity GT; they leave A/C fidelity, `severe`, A6, gates and SystemGain and are reported in a separate missing-bleed table. Restraint (B1/B2/B9) is scored on NO_INK edges. | 290 of 615 real inked edges (47%; 44% of all 659 valid real edges) have art ending exactly at the trim; scoring "paper" there makes every continuation method look catastrophic (~147 MAE) and inverts the production intent. | DD84 |
| M2 | **D1 on the returned output, D2–D4/D6 on the network output.** | v2.0 gave D1 and D2 the same formula with different consequences; every full-image model (LaMa) was a DQ. | DD83 |
| M3 | **V12 scored ring** `min(b, floor(bleed_pt·dpi/72))`. | 142 of 169 real pages have 37.5 px of bleed at 300 DPI; the 38th pixel is half outside the BleedBox. | DD73 |
| M4 | **A6 seam rule (C1 > 2) applies to flat and gradient tiles only.** | The all-class rule failed edge repeat on most structure/texture tiles (median seam step 8.7 / 11.3), violating §4.1's own requirement that the reference passes the absolute rules. | DD86 |
| M5 | **Tier C0 pilot, pseudo-GT track P, train partitions.** | Real GT exists on 165 pages / 34 families only; no-bleed pages supply training data via inward crops (V13) but never headline numbers. | DD67–DD70 |
| M6 | **Families from evidence, not filenames.** Union-find over folder, filename key, tracker client, text shingles, shared embedded images and render hashes, with hub suppression. | A naive folder rule merged 412 of 455 files (a preview portfolio and date-named batch folders mix clients); generic product words ("dinner", "wine") chained unrelated clients. | DD72 |
| M7 | **Measured priors replace assumptions where precise enough.** | Quiet pages 27.9% (95% CI 16–40%) vs 50% assumed; P(FULL \| image edge) 26% (CI 9–73%) vs `ASM-A1` 50%; no real edge in the 2–29 px depth gap. | DD77 |
| M8 | **Gate units are orientation-0 tiles; measured design effects replace planning values.** | Measured `DE_tile` = 12.9 (ICC 0.46, 27 tiles/page) vs 2.35 planned; four rotations of a tile are not independent. Tile-level Gate A needs ≈3,860 accepted tiles at this DE. | DD74 |
| M9 | **Corpus-trained submissions** declare a training manifest audited against eval families and near-duplicates; real-GT families never train; gates are fitted on a partition disjoint from inpainter training. | Prevents the three leakage paths a real corpus opens: near-duplicate versions, stacking, and generator priors fitted on test families. | DD69–DD71, DD75, DD76 |
| M10 | **Weights are loaded without unpickling.** Legacy checkpoints are converted once with a restricted unpickler to safetensors and pinned by SHA-256. | The big-LaMa checkpoint is a Lightning pickle; `weights_only=True` cannot load it. | DD85 |

---

## 1. Critique of v1

v1 is a good first instrument: it established the production question, collected real gold pages, chose the right reference baseline, and produced a result that is already decision-relevant (a generative refiner matched classical fills at ~2,600× the cost). It is also under-powered, mis-specified at the ring boundary, and — most importantly — it deletes the cases that decide whether a generative model can be routed at all. The critique is ordered by how much it changes conclusions.

### 1.1 What v1 got right and must be kept

| # | Keep | Why |
|---|---|---|
| K1 | `edge_repeat` as the reference baseline | It is fast, deterministic, production-real, and surprisingly strong; every gain must be paired against it. |
| K2 | Per-tile oracle `severe` rule, retained as a safety metric | It catches method-relative regressions that absolute thresholds miss, and it is robust to hard GT. |
| K3 | Hard clamp of known pixels plus `preclamp_changed` count | A model that rewrites trim pixels cannot ship; measuring the raw violation is necessary even if clamped. |
| K4 | Hash-seeded tile placement from case id | Reproducible sampling without storing a manifest per page; keep exactly. |
| K5 | Family-level splits, never page or tile | Content in a job family is correlated; page-level splits leak. |
| K6 | Aggregate-only private protocol and hashed ids | The only way a company can contribute; keep schema-compatible. |
| K7 | The per-tile CSV schema as a minimum superset | Historical comparability and tooling reuse. |
| K8 | Three-tier data thinking (private now, public later) | Correct; v2 merely fills in the public tiers. |
| K9 | The production insight that trim accuracy is first-order | v2 turns it into a robustness track rather than a footnote. |
| K10 | The run-time confidence gate concept (AUROC 0.93 self-reported) | Right idea, wrong evaluation; v2 makes gates first-class submissions. |
| K11 | The five qualitative conditions in “Numbers to beat” | They encode real routing decisions; v2 operationalises them. |

### 1.2 What v1 got wrong and v2 replaces

**C1 — The validity rule is brittle and biases the benchmark.** An edge is excluded when >5% of positions have a first trim pixel with any channel <200 and an outermost ring pixel with all channels ≥245. That is an absolute-threshold heuristic: it misses pale tints (levels 200–244), misreads coloured paper and non-sRGB profiles, and makes “valid” depend on how far the artwork happens to extend. It also removes the 33 pages whose artwork stops at the trim — exactly the **restraint** cases a production router must get right. v2 replaces exclusion with a **classification**: each edge is NO_INK, STOP, FULL or AMBIGUOUS, measured with a paper-relative ΔE00 ink test, and STOP is scored, not dropped. The 10 blank-ring pages are almost certainly NO_INK pages, not invalid data.

**C2 — The bimodality is a design signal, not a nuisance.** Of 496 gold edges, 179 have 0–1 px of art past the trim and 280 have ≥30 px; none have 2–29. The 37 edges unaccounted for by those two counts (179 + 280 = 459 ≠ 496) are most likely edges with no ink at the trim at all. v1's single continuous “valid edge” rule forces one threshold onto two physically different populations. v2 models the two populations directly (STOP vs FULL), treats the 2–29 gap as a held-out ambiguity class, and generates PARTIAL cases synthetically for the geometry-robustness track. This is a stronger design than smoothing the histogram.

**C3 — The 5% / 200 / 245 rule also makes the drop rate itself unreliable.** v1 reports ~27% of real jobs with “bleed” have less than the full bleed width. Under v2 that number is not a data-quality failure; it is the production prevalence of restraint, and it should be reported as a **result** (how often the right answer is paper), not as attrition. Any headline that only scores FULL edges is conditional on the easy half of the problem.

**C4 — Tiles are not a page, and v1 has no ring.** Scoring 512 px tiles never tests adjacent-tile seams, corner joins, cross-edge consistency, or a model that can see both sides of the page at once. More subtly, v1's per-tile clamp means a learned model may produce a different local style on each tile; the assembled ring can be visibly quilted even when every tile scores well. v2 adds a required whole-page track (T2) and a tile-seam metric (C7), and reports the tile-to-page gap (I4).

**C5 — One orientation is a canonicalisation assumption, not a property of the task.** Production can rotate a page so one edge is at the top, so top-only tiles are not automatically unfair. But whole-page inference cannot do that for all four edges, and diffusion models are known to have orientation bias. v2 evaluates all four orientations in the standard track (headline = mean, orientation gap reported separately) and includes a paired orientation-invariance subset.

**C6 — 512 px and the latent grid were unexamined.** Current DiT/MMDiT inpainting models work at 1024 px or larger and at 8/16 px latent resolution. v1's 38 px strip at 8 px latent is 4.75 cells; the mask is quantised, boundary latent cells straddle the trim line, and the model regenerates up to one latent cell (8–16 px) *inside* the trim. v1 clamped those pixels and counted them, but never scored the seam this clamping creates. v2 fixes the tile geometry (48 px unknown band aligned to a 16 px grid; see §2.3), scores the clamp seam (D6), and adds a 1024 px track. This is the most consequential interface change in v2.

**C7 — MAE mean is dominated by a minority of hard tiles.** Every v1 method has median MAE 1.9–4.7 but mean 11.5–17.4 (LaMa 14.1, median 4.7); SD2 is 78.4/77.9. The mean is dominated by texture tiles, which are 4.5% of dev (77 tiles) and are exactly where GT is least reliable. v1 headlines a mean and reports a median as a side column. v2 keeps means for comparability but makes paired, family-clustered deltas the primary inference, adds p90/p99 tails, and reports class-stratified results with census weights.

**C8 — The severe rule alone is not a safety rule.** `mae > 2 × oracle_mae + 2` is relative to whichever candidates ran. If every method is bad, every method passes; if one candidate is excellent, all others become severe. v1's floor of 2 is sensible (a 3-level drift on flat is a defect), but it cannot stand alone. v2 keeps it with a **frozen reference oracle set** (the seven classical/LaMa methods, computed once), and adds absolute per-class failure thresholds and an absolute tile-failure flag (A6, §7.2). The routing gate is defined on the absolute event, not the oracle event.

**C9 — No hallucination or restraint metric.** Raw SD2 scored MAE 78 because it invented content; MAE catches that only where GT exists. On the private STOP pages there is GT, so a restraint metric is possible there; on any page without GT, “invented a logo” is unmeasured. v1 explicitly notes the gap but has no instrument. v2 specifies four independent detector families (structure-extension, OCR, object/logo, learned judge) plus a GT-support metric, a human-labelled validation set, and a hard rule: a detector that cannot reach a pre-registered prevalence-adjusted precision on that set is advisory, not gating. §5.

**C10 — Seam gradient error is a weak proxy for structure continuation.** A rule, border, text baseline or horizon crossing the trim must continue at the same angle, width and colour. `boundary_gradient_error` measures a magnitude difference at the seam and is blind to a line that continues at the wrong angle, or to a 1 px offset. v2 adds a line/text continuation detector with angle, offset, width and colour errors (§6). This is a new estimator with its own validation burden; it is not free.

**C11 — Colour is treated as if sRGB were the page space.** Production converts the strip back into the page's own colour space; a flat 100% K page must get 100% K. With naive sRGB conversion the seam error on a colorimetric model is up to 15 dE00; with recipe matching it is under 1 for flat fills. v1 measures sRGB dE00 only. v2 makes page-space dE00, flat absolute drift, near-white, rich black, gamut and CMYK round-trip first-class (E1–E8), and explicitly reports the round-trip floor so a GT-copy cannot be blamed on the model.

**C12 — The confidence result is promising but not yet evidence.** AUROC 0.93, and at threshold 0.665 accepted 48 pages with zero severe, was measured in-sample on 80 pages and cannot bound a 1% false-accept rate: zero events in 48 pages has a 95% upper bound of ~6.1%. v1 also notes the score cannot catch “correct answer is paper”. v2 freezes the gate on calibration only, evaluates accepted-tile severe at the tile unit (where a 1% zero-event bound needs 299 effective accepted tiles) and accepted-page severe on the private 350-page set, requires an exact design-effect-adjusted upper bound, and explicitly measures restraint failure as a separate gate input (§5.4).

**C13 — The sealed test is too small to seal anything.** 11 pages, 292 tiles. Zero severe events in 11 pages has a 95% upper bound of 23.8%; a single severe page moves the point estimate by 9 percentage points. The point estimate is not the issue, the interval is. v1's rank replication is encouraging, not confirmatory. v2 sets minimum sample sizes per claim (§10) and treats the private sealed split as read-once, after freeze.

**C14 — Cost was measured under load, on 12 tiles.** “ms/tile” in a table where SD2 is 1,928 ms and LaMa 75 ms is not a quiet measurement. v2 defines a quiet protocol (H1, §11.3): fixed GPU, locked clocks, warm-up, batch 1, median of ≥100 tiles, no concurrent jobs, power limit declared. v1's ~2,600× cost ratio for `sd_refine` will move under this protocol; that is expected and reportable.

**C15 — Empty prompt is a missed upper bound, not a fair test of promptable models.** Production has no caption, so the unprompted track is primary — correct. But an empty prompt is also the worst possible prompt for a text-conditioned model; it measures the model in a regime production would never use and may understate it. v2 keeps unprompted as primary and adds an optional **caption-oracle diagnostic** (GT-derived caption, clearly non-deployable) as an upper bound only. It never appears in the leaderboard.

**C16 — The content classes are hand-set and under-sampled.** Thresholds are plausible but undocumented, texture is 4.5% of dev, and the classes are computed from the known band within 64 px, which may not represent a full-page background. v2 freezes the thresholds on the calibration split, reports them with units, adds material labels from the vector census, oversamples texture in the evaluation manifest (with census weights), and reports both.

**C17 — The oracle is candidate-dependent and therefore not a stable label.** Per-tile oracle over six classical fills is MAE 9.00; adding LaMa gives 8.58. Both are properties of the candidate set. v2 freezes a **reference oracle file** (same seven methods, fixed versions and seeds) and hashes it; entries cannot change it. `severe`, `regret` and `oracle_win` remain comparable across submissions.

**C18 — No public tier means no leaderboard and no reproducibility.** The private corpus cannot be published. v2 adds a public synthetic tier with exact GT and a public permissively licensed real tier, both fixed and hashed; the private harness remains aggregate-only and v1-compatible.

**C19 — `preclamp_changed` is a count, not a seam measurement.** A model can change 200 trim pixels by 1 level (invisible after clamp) or 2 pixels by 40 levels (a visible step). v2 keeps the count and adds changed fraction, max change, and the clamp-seam dE conditional on the changed neighbourhood (D2–D6).

**C20 — “Family” independence is asserted, not measured.** 80 pages from 53 families still overstates independence: 57 calibration pages from 53 families means most families contribute one page, but tiles within a page share content. v2 reports the intraclass correlation (ICC) of per-tile errors by family and uses family-cluster bootstrap; the effective sample size is reported, not assumed.

**C21 — The confidence gate is described as a three-feature score, but the features are not specified as a contract.** If different entries use different features and thresholds, “accepted severe ≤1%” is not comparable. v2 defines an allowed feature namespace (input-only), requires the gate to be submitted as code plus a declared feature list, and audits it (§13.4).

**C22 — The private protocol's aggregate export is underspecified.** “Only aggregates exist” needs a precise allowlist, hashing salt, k-anonymity floor and re-identification checks, or the first serious contributor will fail its own legal review. v2 defines the export contract (§3.4).

### 1.3 New pitfalls once a real corpus is used for training *and* evaluation (v2.1)

v1's pitfalls are about measurement. Using a real corpus as training data adds leakage and population pitfalls; v2.1 names them and gives each a mechanism, not a promise.

| # | Pitfall | v2.1 mechanism |
|---|---|---|
| N1 | Near-duplicate leakage: the same design exists as `v2`, `copy`, `final`, front/back, several sizes, imposed sheets and web previews | Evidence-based families (DD72) and a private leakage test: no family, render-hash pair (pHash ≤ 6 and dHash ≤ 8) or shared embedded image crosses a split |
| N2 | Pseudo-GT shift: a page's own outer margin is not real bleed (safe zones, frames, text) | V13 rejection; track P is training/diagnostic only; the transfer gap is measured, never assumed (O15) |
| N3 | Stacking leakage: a gate trained on the outputs of the data its inpainter trained on learns optimistic confidence | `gate_fit` partition disjoint from `train_fit`; τ selected on `cal_sel`, certified on untouched `cal_cert` |
| N4 | Prior leakage: generator priors fitted on test families teach the test distribution | Census priors are computed on non-test families only (DD76) |
| N5 | Evaluation population ≠ deployment population: real-GT pages are designer exports that already carry a BleedBox; production needs bleed mostly on pages that lack it | Two censuses (deployment vs real-GT), never pooled; O16 |
| N6 | Half-pixel ring and fractional trims | V12 and device-space trim alignment |
| N7 | PII in the corpus and memorisation in weights | Exclusion rules + per-file human review before any split; corpus-trained weights are private artefacts; exports are k ≥ 5-family aggregates validated by schema |
| N8 | Unsafe or non-reproducible weights | No unpickling at evaluation; safetensors + SHA-256; licences recorded per baseline |
| N9 | Reference baseline swamped by an invalid class | Class-stratified reporting is mandatory before any pooled mean (§7.9); M1 removed the class whose GT is not the desired output |

## 2. Task definition

### 2.1 Coordinate system and units

All geometry is in **page pixels at the render DPI**, origin at the top-left corner of the **trim box**, x right, y down. The page is rendered once, at target DPI, from the source PDF with its real artwork. The bleed ring is the set of pixels outside the trim box but inside the bleed box; it is removed from the input and is the only region a method may invent.

| Symbol | Meaning | Default |
|---|---|---|
| `dpi` | render resolution | 300 |
| `b` | bleed width in px | `ceil(bleed_mm / 25.4 × dpi)` = 38 for 0.125 in at 300 DPI |
| `a` | apron width in px | `(-b) mod 16` = 10 for `b=38` |
| `B` | unknown band width in px | `b + a` = 48 for `b=38` |
| `W,H` | trim-box size in px | page-dependent |
| `L` | model latent stride in px | declared by model (1, 8, 16 or 32) |
| `τ_sev` | severe threshold | `2 × oracle_mae + 2` (retained from v1) |

`b` is rounded **up** so the strip is never narrower than the requested physical bleed. This matters at 150 DPI: 0.125 in = 18.75 px, and 19 px is correct; truncation would under-fill the physical requirement.

### 2.2 Two canvas modes

| Mode | Canvas | Unknown region | Scored region | Use |
|---|---|---|---|---|
| **Tile** | 512×512 or 1024×1024 | `B`-wide band along the page-edge side(s) | the `b`-wide ring only | efficient fidelity, orientation, corners, cost |
| **Whole page** | trim + margins: `B` on left/top, `B + δ` on right/bottom to make the canvas 16-aligned (§2.3) | border of width `B` left/top and `B+δ` right/bottom | the `b`-wide ring, all four edges and four corners jointly | ring consistency, tile-to-page gap, production simulation |

Tile windows are **anchored to their own seam**, so an edge tile always puts the trim line at row/column `B` and the known band is exactly 464/976 px, including right and bottom page edges. A tile is not a crop of the whole-page canvas for right/bottom edges (that canvas is `B+δ` wide on those sides); it is a seam-anchored crop of the page. An edge tile contains exactly one seam; a corner tile contains two seams meeting in an L.

**Tile placement.** For each page edge, `E` tiles are placed with centres evenly spaced along the edge, then jittered by up to 25% of the spacing; the placement seed is `hash(case_id, edge, tile_index)`. `E=6` at 512 px and `E=4` at 1024 px (a 1024 px tile overlaps heavily if six are placed on a typical edge). Four corner tiles are always placed, one per corner. The default manifest allows overlap but does not guarantee it; the consistency metrics C7/J2 use a dedicated **50%-overlap subset** (100 pages) where adjacent tile centres are exactly `tile_px/2` apart and the overlap is composited with a 32 px cosine feather (§4.3). Placement never depends on model output.

### 2.3 Latent-aligned geometry (DD1–DD4)

The v1 tile put the seam at row 38, which is not a multiple of 8 or 16. At 8 px latent that makes the boundary latent cell contain both known trim pixels and unknown bleed pixels; the model regenerates up to 8 px inside the trim, and the clamp either hides or creates a seam. v2 removes the ambiguity by **padding the unknown band outward to `B = b + a` where `a = (-b) mod 16`**, and by anchoring the seam at row/column `B`, which is a multiple of 16.

Consequences:

1. The model is asked for `B` pixels of new content but only the inner `b` pixels are scored. The outer `a` pixels are the **apron**: unscored context, like a painter's margin. The model is not told which is which.
2. In **tile mode every seam is aligned**: the tile is anchored to its seam, so the unknown band is exactly `B` and the seam sits at pixel `B` (a multiple of 16). For `L ∈ {1,8,16}` no trim pixel then shares a latent cell with an unknown pixel. In whole-page mode the left/top seams are aligned at `B`, but the right/bottom seams sit at `B + W` and `B + H`, which are on the 16 grid only when `W` and `H` are multiples of 16. **No margin padding can move a seam**; the asymmetry below therefore aligns the *canvas* to the latent grid (required by the VAE), not the right/bottom seam. The unavoidable off-grid remainder is measured by D5 and its clamp seam by D6, not assumed away.
3. Classical methods receive the same `B`-wide blank band, so inputs are identical across method families. Classical fills that only fill `b` pixels are still valid; the apron is unscored.
4. The cost is that the model fills 26% more strip than production needs at `b=38`. This is the price of latent exactness on the aligned seams. It is ablated in O2: if a 38 px band with a documented boundary policy scores identically, v2.1 may drop the apron. Until then, the apron is normative.

For the whole page, the left and top margins are exactly `B`. The right and bottom margins are `B + δx` and `B + δy`, where

```text
δx = (-W) mod 16
δy = (-H) mod 16
```

so the **canvas dimensions** are multiples of 16, as the VAE encoder requires. The scored ring remains exactly `b` wide on every side. The right/bottom seams remain at `B + W` and `B + H`; their off-grid remainder is

```text
r_x = (B + W) mod 16 = W mod 16
r_y = (B + H) mod 16 = H mod 16
```

For a US Letter page at 300 DPI (`W=2550`), `r_x = 6`: a 16 px latent cell on the right seam contains 6 known trim columns and 10 unknown columns. This is a property of the page size, not a fixable padding choice. A model that needs every seam aligned MAY run whole-page inference as four seam-anchored strip passes plus four corner passes and composite them; that is a declared inference strategy, and C7/C8 verify that the composite agrees with a single-pass output. **The whole-page track is therefore a ring-consistency instrument, not a claim of universal latent alignment.**

| DPI | Physical bleed | `b` | `a` | `B` | tile known band (512 / 1024) |
|---|---|---|---|---|---|
| 150 | 0.125 in | 19 | 13 | 32 | 480 / 992 |
| 300 | 0.125 in (default) | 38 | 10 | 48 | 464 / 976 |
| 300 | 5 mm | 60 | 4 | 64 | 448 / 960 |
| 600 | 0.125 in | 75 | 5 | 80 | 432 / 944 |

### 2.4 Interfaces (normative)

The v1 interface contracts are **extended, not replaced**. A v1-shaped call with `apron_px=0` and `b=38` must reproduce v1 geometry (legacy mode, `protocol=legacy_v1`).

```python
# Classical (all non-learned methods)
fill(
    image: uint8[H, W, C],          # trim known, ring+apron blank; C=3 (RGB) or 4 (CMYK-native)
    trim: PixelRect,                 # trim rect inside image, origin (B, B) for a top-edge tile
    bleed_px: int,                   # b
    apron_px: int,                   # a
    page_space: ColorSpaceSpec,      # profile hash, intent, bit depth
) -> uint8[H, W, C]
# Contract: every pixel inside `trim` is bit-identical to the input.
# Contract: output shape and channel count equal input.
# Contract: pixels outside trim are the method's invention; only the ring is scored.

# Learned (transformer or any pixel generator)
inpainter(
    tile: uint8 or float[H, W, C],   # known pixels as rendered; unknown pixels set to 0 (or declared fill)
    unknown: bool[H, W],             # True = ring + apron; the only pixels that may change
    meta: TileMeta,                  # orientation, dpi, b, a, L, page_space, model space, seed
) -> uint8 or float[H, W, C]
# Harness copies known pixels back from the input after inference (hard clamp).
# The harness computes D1/D2/D4 from the raw output it holds; the attributes below
# are informational and never trusted for scoring.
# inpainter.last_changed      : int,  submission-reported count (informational)
# inpainter.last_changed_max  : int,  submission-reported max (informational)
# inpainter.latent_stride     : int,  declared L
# inpainter.mask_policy       : "pixel" | "latent_or" | "latent_nearest"
# inpainter.confidence        : float in [0,1], run-time, input-only features
```

`meta` MUST NOT contain a caption, page text, case id, family id, split, ground truth, or any label. It MAY contain the seed, geometry, profile description and orientation. A model that requires a caption is scored in the optional diagnostic track (T8) and is not eligible for the main leaderboard.

**Classical vs learned parity.** Both receive the same known pixels and the same unknown region. The learned model additionally receives the boolean mask because it cannot otherwise know where to paint; the classical method receives the trim rectangle because that is its contract. No method receives the scored-mask (ring-only) distinction, GT, or page metadata not listed above.

### 2.5 Mask semantics at latent resolution (DD5–DD7)

The official mask is pixel-resolution: `unknown = True` for ring ∪ apron. The harness derives the model's effective mask for audit but never substitutes it.

```text
M_L(c) = OR over the L×L pixel block c of unknown
```

The harness records `regen_trim_px = |{p : p inside trim, M_L(block(p)) = True}|` and the pre-clamp change statistics. In tile mode, the seam is 16-aligned, so `regen_trim_px = 0` for `L ≤ 16` unless the model resamples internally. In whole-page mode it is 0 on the left/top seams and expected to be nonzero on the right/bottom seams when `W mod 16 ≠ 0` or `H mod 16 ≠ 0`; this is reported per seam (`regen_trim_px_left/top/right/bottom`), scored by D6, and never a DQ. For `L = 32`, a 16 px overlap is possible everywhere and is measured by D5. A model that writes outside `unknown` is disqualified (D1), not merely clamped.

### 2.6 Orientation policy (DD8–DD9)

Each tile is generated in a **base canonical orientation**: for an edge tile the unknown band is on **top**; for a corner tile the unknown L is at **top-left**. For evaluation orientation `r ∈ {0°,90°,180°,270°}`, the harness rotates the **entire tile, content and mask together**, by `r`; the resulting unknown region is no longer on top for `r≠0`, and that is intentional. `orientation = r` is recorded in `meta` and in the CSV. “Canonical orientation” therefore describes tile generation, not the absence of rotation during evaluation.

The standard track evaluates **all four orientations of every tile**. The headline fidelity is the mean over orientations; the paired orientation gap is reported separately (G3). Because the mask rotates with the content, `edge_repeat` is rotation-equivariant (its error on the same content is identical in every orientation), which is what makes the §9.3 gradient self-test exact: a horizontal gradient rotated 90° changes orientation *relative to the page*, but not relative to the rotated seam and mask.

### 2.7 What is and is not scored

**Scored:** pixels in the ring (outside trim, inside bleed box), all colour channels, in the declared page space. Derived metrics that use known pixels (seam step, structure continuation, clamp seam) are scored on the ring and its immediate known neighbourhood only.

**Not scored:** the apron (must be produced but is context); pixels inside the trim (they are a **disqualification check**, not a fidelity metric); crop marks, registration marks and other vector geometry as *produced output* (out of scope; production draws them by code), though they are an in-scope **input distractor** in F3; PDF object structure, file size, embedding, overprint; captions/prompts; distribution-level metrics (FID/KID are explicitly not primary and are not reported); anything outside the rendered page.

**Ground-truth isolation.** Metrics MAY read GT. Run-time features and the confidence gate MUST NOT. The harness enforces this by file-system isolation (GT store not mounted during inference), by the feature namespace (`feat_*` only, §13.1 and Appendix B.4), and by code audit of the submitted gate.

### 2.8 Colour pipeline (DD10–DD13)

A page has a **page space**, declared in its metadata: `srgb`, `adobe_rgb`, `cmyk` + ICC profile hash, `gray`, or `spot` + recipe table. The harness feeds the model a **model space** render and converts the returned strip back into page space for scoring.

| Page space | Model sees (default) | Scoring space | Round-trip floor |
|---|---|---|---|
| sRGB | sRGB 8/16-bit | Lab D50 (Bradford-adapted) | 0 |
| Adobe RGB | Adobe RGB (preferred) or sRGB (declared) | Lab D50 | 0 if model space is Adobe RGB; measured if an sRGB proxy is used |
| CMYK | sRGB proxy by default, or CMYK-native if declared | CMYK→Lab D50 via ICC, plus channel drift | measured with `roundtrip_gt` |
| Gray | Gray→RGB | Gray→Lab D50 | 0 |
| Spot | RGB proxy of recipe tint | Lab D50 of spot recipe | measured with `roundtrip_spot_gt` |

Conversion uses the profile named by the page's ICC hash, **relative colorimetric intent with black-point compensation ON** unless the submission declares otherwise; one declaration per entry, applied everywhere. 8-bit vs 16-bit output is declared; dithering is off. A **CMYK-native** model may declare `native_space = cmyk`, receive 4-channel tiles and return 4-channel tiles; it is scored directly and appears in a separate native-colour sub-table, never mixed with RGB-proxy entries.

`roundtrip_gt` is the GT strip passed through model-space conversion and back; it is the floor for E5, not zero. `roundtrip_spot_gt` is the GT spot strip passed through the RGB proxy tint reconstruction and back; it is the floor for E7. Reporting a model's CMYK or spot dE without subtracting or showing that floor is invalid.

### 2.9 Production contract (why the benchmark is shaped this way)

In production the original page is placed unchanged in a live PDF and only the new strip pixels are added. The router therefore has exactly four decisions per page: (1) is the trim accurate, (2) does the page need fill, (3) does the model's strip pass the colour/continuity checks, (4) is the confidence gate high enough to skip the deterministic fallback. The benchmark mirrors this: trim integrity is a gate (D1), restraint is a scored class (B), seam/colour are metrics (C/E), and the gate is evaluated as part of the submission (G/§7.6). A benchmark that only measured strip MAE would optimise the wrong decision.

---

## 3. Data

Three tiers, each with a different job. They are never pooled into one headline; the private tier is the production decision, the public tiers are reproducibility and model development.

| Tier | Name | Role | Access | GT | Counts (target) |
|---|---|---|---|---|---|
| **A** | Public synthetic | Harness check, training data for public baselines, public leaderboard | Public, CC0/Apache-2.0 | Exact, all pixels | 2,000 train + 640 eval pages; 200 + 64 families |
| **B** | Public real | Cross-domain sanity, public leaderboard, licence-clean real artefacts | Public, permissive licences | Exact ring from PDF bleed box | 300 pages / 100 families (min 120 / 40) |
| **C** | Private real | Production acceptance, sealed test, severe-rate bounds | Company-internal; aggregate export only | Exact ring from real bleed | 1,300 pages / 400 families annual; 350-page acceptance set per submission |

### 3.1 Tier A — public synthetic set

**Why it exists.** Exact GT, controllability, and the ability for an external model author to run the benchmark without access to customer files. It is not a substitute for real photos; a model that only wins on synthetic pages has not earned production routing.

**Generator.** A deterministic procedural page generator, `bleedgen`, defined by a JSON page spec plus a seed. Rendering uses a pinned version of Cairo (or MuPDF) with anti-aliasing on, at the declared DPI, in both sRGB and CMYK. Every page has a `family_id` = generator template hash; pages within a family share layout grammar, font, palette and photo set, with seeded variation. Rendering renders **full bleed plus apron** (`b + a` plus a 40 px safety margin), then masks the ring for the input and stores GT separately.

**Primitives** (each with a documented parameter distribution):

| Primitive | Parameters | Purpose |
|---|---|---|
| Solid fill | RGB or CMYK recipe, including 100% K, rich black (e.g. C60 M40 Y40 K100), pale tints (3–20%) | flat drift, rich black, colour |
| Linear/radial gradient | 2–6 stops, angle, length, colour space | gradient continuity |
| Rule/border | width 0.25–6 pt, angle 0–90°, colour, inside/outside trim | structure continuation |
| Text block | open-licence font, size 4–72 pt, leading, rotation, baseline crosses trim | text continuation, OCR |
| Tiling pattern | dots/stripes/checks, period 2–80 px, rotation, CMYK recipe | pattern continuation |
| Photo | CC0 image, crop 0–30%, scale 10–40% page area, 0–2 stops colour grade | the dominant real workload |
| Clipped vector art | vector illustration scaled 1.2–3× trim, offset 0–60 px, hidden source pixels | hidden bleed |
| Mixed page | background + 1–3 primitives, shared palette, layered order | realistic composition |

**Mix targets (normative).** The generator MUST hit these marginals within a 2% absolute tolerance, verified by an automated census test over the eval split. The joint distribution is seeded; only the marginals are fixed.

| Dimension | Target | Derivation |
|---|---|---|
| Pages with no ink at trim (quiet) | 50% | “about half of real pages need no pixel fill at all” |
| Inked edges: material = placed image | 57.9% | v1 census 58% |
| Inked edges: flat fill | 29.0% | v1 census 29% |
| Inked edges: clipped content with hidden pixels | 10.0% | v1 census 10% |
| Inked edges: tiling pattern | 2.5% | v1 census 2.5% |
| Inked edges: stroke/text | 0.6% | v1 census 0.7% (rounded to sum) |
| Image edges with hidden bleed | 50% of image edges (FULL); 50% STOP | assumption `ASM-A1` (the joint is unmeasured; settled by the 1,000-page audit in O1); sensitivity at 75/25 in O1 |
| Flat edges with hidden bleed | 80% FULL; 20% STOP | continued solids are the common flat case |
| Clipped-art edges with hidden bleed | 100% FULL | hidden pixels are the definition of the class |
| Pattern edges with hidden bleed | 90% FULL; 10% STOP | pattern may end at the trim |
| Text/stroke edges with hidden bleed | 50% FULL; 50% STOP | text may cross or end at the trim |
| Edge hidden-bleed class, all edges | NO_INK 50%, FULL 32.4%, STOP 17.6% | quiet pages + the stop shares above (829 FULL / 451 STOP) |
| Content class (page) | flat 39%, gradient 23%, structure 33%, texture 5% | v1 dev class counts 680/405/568/77 |
| Special pages | CMYK 30%, Adobe RGB 5%, pale tint 10%, rich black 5%, near-white 10%, spot 3%, partial bleed 2%, crop marks 5%, 150 DPI 10%, 600 DPI 5% | colour/geometry coverage |

With 640 eval pages this yields approximately: 320 quiet pages, 185 photo pages, 93 flat pages, 32 clipped-art pages, 8 pattern pages, 2 text pages; 1,280 inked edges of which **829 are FULL and 451 are STOP after integer allocation** (the conditional probabilities give 828.4 / 451.6; the manifest assigns the rounding residual to FULL); 2,560 edges total. The page counts are the material shares applied to the 320 fill pages (each fill page is single-material by construction, so page share equals edge share at four edges/page); the 50% quiet share is a brief fact (“about half of real pages need no pixel fill at all”), not a derived v1 statistic. Mixed-material pages are generated only in the 5% realism subset and do not enter the marginal counts. Exact counts are pinned in `synthetic_manifest.json` at freeze.

**Page count per split.** 640 eval pages / 64 families: calibration 320 pages / 32 families, validation 160 / 16, sealed test 160 / 16. A separate **train** split of 2,000 pages / 200 families is published for baseline training (MAE/ViT inpainter, small CNNs, fine-tunes) and is family-disjoint from eval. Public baselines MUST declare whether they trained on Tier A train; models that did not are not disadvantaged because the train split contains no real customer content.

**Generator acceptance tests** (must pass before freeze): (i) census χ² test against the table above, p > 0.05; (ii) **full eval-set** class balance within ±20% relative; per-split balance is not required for classes smaller than 60 pages because the test manifest deliberately oversamples texture; (iii) 10% of pages visually inspected for render defects (bad clipping, font fallback, alpha) against a written checklist, any defect re-renders; (iv) GT ring exactly `b` wide and input ring exactly blank; (v) no text or metadata contains the seed→split mapping; (vi) same seed renders byte-identical PNGs; (vii) 50 pages rendered at 150/300/600 DPI and the 300 DPI version downsampled to 150 matches within **2 levels mean / 5 levels max** after accounting for the 1.3% physical-bleed quantisation (19/38/75 px).

### 3.2 Tier B — public real set

**Sourcing criteria.** Print-ready PDFs that are (a) under CC0, public domain, or CC-BY 4.0; (b) have a **BleedBox strictly larger than TrimBox** on all four sides by at least 0.125 in; (c) embed their ICC profile and fonts; (d) contain no third-party trademarks, logos, personal data, or identifiable faces unless the licence clearly covers them; (e) are renderable by the pinned renderer at 300 DPI without errors. Candidate sources: public-domain book scans with print wrappers, PDF Association / PDF/X sample files, open-design portfolios with explicit CC licences, government print publications. Every page records `source_url`, `licence`, `licence_evidence_hash` (archived page or licence text), and `pdf_sha256`.

**Licence check.** A page enters the set only if the licence is verified by two reviewers and the licence text is archived; “free to download” is not a licence. The set is redistributed as rendered 16-bit PNG crops with a NOTICE file, or as a downloader that verifies the PDF hash, depending on the licence's redistribution terms.

**Validity** uses §3.4 (including the V11 render region: BleedBox dilated by the apron, clipped to the MediaBox, missing pixels padded with paper and unscored), fixed for pale tints. **Counts:** target 300 pages / 100 families; minimum 120 / 40. Families are job/template clusters (same publisher series, same design template, or same source document); when uncertain, merge families (conservative). Splits by family 50/25/25. Tier B cannot support a 1% severe-rate bound; it is a generalization and public-leaderboard instrument, not a production acceptance set.

### 3.3 Tier C — private protocol

**Purpose.** The only tier that can decide production routing. Runs inside the company; only aggregates and the per-tile CSV leave.

**Compatibility with v1.** The v1 private corpus of 124 pages / 70 families remains usable. v2 recomputes validity under §3.4 and recovers **all 44 v1-dropped pages in principle**: the 10 blank-ring pages are NO_INK, the 33 short-bleed pages are STOP or NO_INK (43 reclassified), and the 1 small page is handled by whole-page mode (V7). After V5 exclusions the expected usable count is ~120 pages / ~68 families, not “124” — the exact number is reported in the manifest. It also keeps a `protocol=legacy_v1` subset (38 px unknown band, 474 known, top orientation only, sRGB, six-method v1 oracle) to reproduce v1's table for regression. The legacy subset is not used for v2 leaderboard ranking.

**Counts.** Annual calibration set: 1,300 pages / 400 families (see §10.3 for why). Per-submission acceptance set: 350 held-out pages / 120 families, disjoint from any tuning data; at `DE_page = 1.11` this gives 315 effective accepted pages and a zero-event 95% upper bound of 0.95% on accepted-page severe rate (a 300-page set would have no gate-rejection headroom). v1's 80-page set is retained as a regression set only.

**Aggregate export contract.** The harness emits: the per-tile CSV with hashed `case_id`/`family_id` (HMAC-SHA256 with a per-company salt, salt never exported); aggregate JSON with k-anonymity floor (no cell with <5 families is exported, suppressed cells marked); no images, no PDFs, no free-text, no timestamps finer than day, no absolute paths. The allowlist is enforced by a schema, not by convention.

### 3.3a Tier C0 — private pilot (v2.1)

**What it is.** One print shop's real job files (PDF and raster), used under the §3.3 aggregate-only contract. It is the first real data the benchmark has run on, and it is a **pilot**: it calibrates thresholds, measures design effects and priors, supplies training data, and produces a dev table — it does **not** certify production routing.

**Intake (all automated steps are in `bleedbench/ingest`, all decisions are recorded privately):**

1. Inventory: SHA-256 of every file, nested archives extracted with path-traversal checks, exact duplicates dropped.
2. Exclusion rules: non-print types, unrelated datasets, phone photos, AI-generated images, and sensitive forms (payment authorisation, fingerprint cards, agreements, benefit guides, name badges, personal greetings) by generic rule plus a private file-specific list.
3. PII screen on every PDF text layer (SSN, Luhn-valid card numbers, dates of birth, form keywords; phone/e-mail flagged); pages without a text layer go to a visual contact sheet. **No file enters a split without a recorded human decision.**
4. Render: trim mapped to integer pixel `B` in device space; CropBox reset to MediaBox in memory; rotation normalised; V11 padding; V1 2× integrity measured.
5. Labels: V2–V5, V12, V13, V14; vector material census from the PDF display list.

**Counts (frozen splits, SHA in `aggregates/census_c0.json`):** 628 files inventoried; 455 candidate files after exclusions; 588 usable pages / 90 families after review. Real GT (`real_bleedbox`): 165 pages / 34 families. Inferred-trim candidates: 8 pages, unverified, unscored.

| Partition | Pages | Real-GT pages | Families | Use |
|---|---|---|---|---|
| `cal_sel` | 79 | 43 | 6 | gate τ selection, threshold fitting |
| `cal_cert` | 80 | 57 | 5 | gate certification only |
| `val` | 64 | 32 | 11 | dev table, gated SystemGain |
| `test` | 57 | 33 | 12 | sealed, read once after freeze |
| `train_fit` | 215 | 0 | 8 | inpainter training (pseudo GT) |
| `train_dev` | 31 | 0 | 11 | checkpoint selection |
| `gate_fit` | 62 | 0 | 37 | gate model fitting |

Families larger than 20% of a real-GT split's target are restricted to the calibration halves; families larger than 20% of `gate_fit`'s target are restricted to `train_fit`.

**What C0 can and cannot claim.** With ~33 test pages from 12 families, a zero-event one-sided 95% bound on page severe is ≈ 8.7% before the design effect — C0 cannot support a 1% claim at any unit. Tile-level Gate A needs `299 × DE_tile` ≈ 3,860 accepted orientation-0 tiles at the measured `DE_tile` = 12.9; the calibration halves hold far fewer, so Gate A is **not certifiable on C0** and Gate B is reported as a pilot certificate. These are results, not failures: they size the Tier C collection (§10).

### 3.3b Track P — pseudo ground truth (v2.1)

Pages without a BleedBox (the deployment population) can still provide supervised strips: the MediaBox inset by `B` is treated as a pseudo-trim and the page's own outer pixels as the ring. V13 removes edges whose outer band holds text, frame lines or marks. Track P is used for (i) training (`train_fit`), (ii) checkpoint selection (`train_dev`), (iii) gate fitting (`gate_fit`), and (iv) the **transfer diagnostic** T10: the same methods scored on pseudo pages of the dev families, reported beside the real-GT table. Track P numbers are never pooled with real GT and never appear in a headline.

### 3.4 Validity rules (fixed for pale tints)

These rules decide whether an edge's GT is trustworthy and what class it is. They do **not** drop an edge because the artwork stops at the trim; they classify it.

**V1 — Render integrity.** TrimBox and BleedBox present and consistent with the declared page geometry; ICC present (or sRGB default declared); fonts embedded; render at target DPI exactly; no transparency-flattening artefacts in the ring (checked by re-render at 2× and downsampling; a >2-level discrepancy invalidates).

**V2 — Paper estimate.** Paper colour is estimated from (in order): the PDF's declared background/white point; a declared in-trim paper margin if the page has one; the mode of the outermost 2 px of the GT ring **only when that ring is uniform and near-paper** (≥90% of its pixels within 2 dE00 of the candidate, and the candidate is not dark artwork). Estimating paper from a full-bleed photo ring is prohibited: it would classify artwork as paper and collapse `D_e` to STOP, which is the v1 failure mode v2 exists to fix. The source and confidence of the estimate are recorded (`paper_source`, `paper_confidence`); if confidence is low the edge is marked `paper_uncertain` and excluded from STOP/B1 scoring but retained for FULL fidelity. The estimate is never given to the model.

**V3 — Ink test (pale-tint fix).** A pixel is ink if `ΔE00(pixel, paper) > 1.5` **or** `L* < L*_paper − 2`. The v1 thresholds (channel <200 for ink, all channels ≥245 for paper) are prohibited: a 5% K tint is ~L* 95 and a 10% tint ~L* 89, both well below paper but both above 200 in 8-bit sRGB; the v1 rule can neither see them as ink nor count them as paper.

**V4 — Hidden-bleed depth.** For each position `x` along an edge, walk outward from the trim line and let `d(x)` be the number of consecutive ink pixels before the first paper pixel (0 if the first ring pixel is paper). The edge depth is `D_e = quantile_0.9({d(x)})`. Then:

| Class | Rule | Meaning | v1 analogue |
|---|---|---|---|
| `NO_INK` | no ink in the first 2 px inside the trim on ≥98% of positions | trim edge is paper | often dropped as blank ring |
| `STOP` | `D_e ≤ 1` and ink at trim | artwork stops at trim; correct answer is paper | **dropped** by v1 |
| `FULL` | `D_e ≥ full_min`, where `full_min = max(2, round(0.8·s))` and `s` is the scored ring width (V12) | real hidden bleed exists | “valid” |
| `AMBIGUOUS` | `2 ≤ D_e < full_min` | held out of primary analysis; synthetic only for F | none (gap) |

**V5 — Edge valid if GT trustworthy.** An edge is included unless: the GT ring contains crop/registration marks or vector marks that are not page artwork; the source has missing/incorrect ICC; the render is corrupted; or >2% of positions have contradictory evidence (ink at trim but alternating paper/ink in the ring at a spatial frequency inconsistent with artwork). Reasons are recorded; the default is include, classify and score.

**V6 — Pale-tint confirmation.** For every page whose GT ring contains a tint in the 3–20% range, a human or a reference patch confirms that the ink test detects it; the audit sample is 100 pages. A failure rate >1% rejects the renderer/calibration for Tier B until fixed.

**V7 — Small pages.** A page whose trim is smaller than a tile is not dropped: whole-page mode still scores it, and tile placements that do not fit are marked invalid for that tile only. This reverses v1's “trim smaller than a tile” drop.

**V8 — Apron GT.** If the real artwork extends less than `B` pixels, the apron has no GT; this is expected and does not invalidate the ring. Only the `b` ring is scored.

**V9 — Model-space GT.** GT is stored in page space and converted to the model space with the same pipeline as the input; the converted GT is what A/C metrics compare against. The page-space GT is used for E metrics.

**V10 — Label isolation.** GT, paper estimates, class labels and depth are stored in a separate label store with a different access path from the input store; no run-time component may read it.

**V11 — Render region.** For real pages (Tier B/C) the render region is the BleedBox dilated by the apron `a` on each side, clipped to the MediaBox. Pixels of the dilated region that fall outside the MediaBox are filled with the paper estimate (V2) and counted per edge as `padded_px`, stored in the label store (not in the per-tile CSV). Padded pixels carry no GT: they are treated like V8 (unscored, never counted in A/B/C/E metrics) and are excluded from paper estimation. An edge whose scored ring `b` is itself partly padded (BleedBox exceeds MediaBox) is invalid under V5 (GT not trustworthy), not silently scored. Synthetic Tier A renders the full canvas and has `padded_px = 0`.

**V12 — Scored ring on real pages (v2.1).** The model is still asked for `B` pixels and `b` stays `ceil(bleed·dpi)`, but on a real page only pixels whose footprint lies wholly inside the BleedBox are scored: `ring_scored_px = min(b, floor(bleed_pt · dpi / 72))`. At 300 DPI a 0.125 in BleedBox is 37.5 px, so 37 px are scored and the 38th (half outside the box) is not. Measured on C0: 142 of 169 real pages have exactly 37.5 px of bleed; without V12 every one of them would score a blended half-pixel column. The canvas is rendered with the trim mapped to integer pixel `B` (device-space translation), never by rounding a page-space clip.

**V13 — Pseudo-GT validity (v2.1, track P only).** A page without a BleedBox can supply a *pseudo* ring by treating the MediaBox inset by `B` as the trim. Such an edge is rejected if its outer band contains a text block, a straight line parallel to the edge (frame/rule test: a row differing by > 10 dE00 from rows ±3 on ≥ 60% of positions), or crop marks. Pseudo rings measure continuation of a page's own margin, which is systematically different from real bleed (safe zones, frames); they are training and transfer-diagnostic data only and never enter a headline (DD68).

**V14 — Not GT (v2.1).** Imposed sheets (n-up), rasters below 240 DPI (unless their pixel size equals a standard trim or trim + 0.25 in at exactly 300 DPI), and pages whose bleed is inferred from a media size of "standard + 0.25 in" without a TrimBox are not ground truth. The last group (`gt_source = inferred_trim`) may be promoted to scored GT only after a human verifies the trim, page by page, and is reported as its own stratum (DD79).

**STOP reinterpreted (v2.1, DD84).** v2.0 treated `STOP` (ink at the trim, `D_e ≤ 1`) as a restraint class whose correct answer is paper. On real print-ready files this is wrong: art that touches the trim and does not continue is the classic missing-bleed defect (a sub-millimetre cutting error shows a white sliver), and the production intent on such an edge is to extend the art. The GT ring of a STOP edge is therefore **not** the desired output, and a STOP edge has no fidelity GT. From v2.1: STOP edges are excluded from A/C fidelity, `severe`, A6, gates and SystemGain; they are reported in a separate *missing-bleed* table (prevalence, and the fraction of the ring each method extends). Restraint (B1/B2/B9, A6 "invented ink") is scored on **NO_INK** edges, where the trim itself is paper and the correct ring is paper. Synthetic generators MUST NOT produce paper-beyond-trim targets for inked edges.

### 3.5 Family definitions, splits and contamination

**Family.** A cluster of pages that share content, template, brand, photographer or design series. Private: the existing `family_id` from v1 (job family). Public real: same publisher series / same source document / same template, merged when uncertain. Synthetic: generator template hash. Family is the resampling unit for all intervals.

**Splits.** 50% calibration / 25% validation / 25% sealed test by family, stratified by material mix, hidden-bleed class and content class. No page or tile from a family appears in more than one split. The split assignment is generated once from a seed and frozen in `splits.json` with a SHA-256. The sealed test is opened once, after the protocol and thresholds are frozen; no model selection, threshold choice, prompt tuning or calibration may use it.

**Contamination.** Public train families are disjoint from public eval families. Tier A synthetic is generated from templates, not from Tier B/C pages. Tier B pages are checked against a perceptual hash for near-duplicates before split assignment. Submissions MUST declare all training data; a submission trained on Tier B or the sealed test is disqualified if detected, and the canary set (§13.4) is designed to make undetected use less likely.

### 3.6 Target counts per class and per tier

| Class / stratum | Tier A synthetic (eval) | Tier B public real | Tier C private |
|---|---|---|---|
| Pages total | 640 | 300 | 1,300 |
| Families | 64 | 100 | 400 |
| Quiet (NO_INK pages) | 320 | 150 (expected) | 650 (expected) |
| Pages needing fill | 320 | 150 | 650 |
| Edge FULL | ~829 | ~ measured | ~ measured |
| Edge STOP | ~451 | ~ measured | ~ measured |
| Flat content | 250 | 117 | 507 |
| Gradient | 147 | 69 | 299 |
| Structure | 211 | 99 | 429 |
| Texture | 32 (population 8 cal / 8 val / 16 test = 2× oversample in test) | 15 | 65 |
| CMYK pages | 192 | 90 | 390 |
| Wide-gamut RGB (Adobe RGB) | 32 | 15 | 65 |
| Corner tiles needed | 2,560 (4 × 640) | 1,200 | 5,200 |

Texture is oversampled **2×** in the public **test manifest** (16/160 = 10% versus the 5% census population): the 32 texture pages are split 8 calibration / 8 validation / 16 test, so the test class claim has 16 pages, not 32. The calibration split therefore carries 8 texture pages (2.5% of 320) **by design**; the generator's class-balance test is on the full 640-page eval set (5%), not per split, for classes below 60 pages. All aggregates are reported with census weights, so the oversampling cannot inflate the headline. A 4× oversample would require all 32 texture pages in the sealed test and would leave calibration/validation with zero texture pages, violating §3.5 stratification.

### 3.7 Canary and audit pages

Ten canary pages per public split are generated with distinctive, harmless content (e.g., a unique stripe frequency and a nonsense glyph string) and are not announced. If a model reproduces a canary's GT ring with pixel-level fidelity from a prompt-free input, that is evidence of test-set training; the submission is referred for audit, not automatically disqualified. Canary pages are scored normally and their metrics are excluded from aggregates. Tier C uses a private canary set drawn from retired jobs.

## 4. Metrics, axes A–J

### 4.0 Notation and general rules

Let `U` be the scored ring pixels in a tile/page, `K` the known trim pixels, `R` the final output after clamping, `G` the ground truth in page space, `I` the input, `C` the number of channels. `ΔE00` is CIEDE2000 computed in the **ICC PCS D50** reference (sRGB D65 is Bradford-adapted to D50 first; CMYK/spot use the profile PCS directly; no D65/D50 mixing). `∇` is the Sobel gradient magnitude on L*. A **seam pair** is a 4-neighbour pair `(p,q)` with `p ∈ U`, `q ∈ K`. “Per tile” means one evaluated tile in one orientation; “per page” means aggregated as in §7.

Unless stated otherwise: metrics are computed per tile at 8-bit output precision, in float; means are over `U` only; higher-is-better metrics are marked ↑, lower ↓. Thresholds are **per tile** and are pre-registered at protocol freeze; the provisional values below are chosen from print tolerances and v1's measured distribution, then frozen after the calibration run. A threshold may be revised only before the sealed test is opened.

**Sanity baselines.** Every metric names a baseline that should score near-perfect. The universal one is `gt_copy` (fill the unknown with GT), which is the harness's correctness check and must score exactly 0 error / 1.0 score on every **GT-referenced** fidelity and seam metric. For **detector-based no-GT metrics** (B3–B6, C6) “near-perfect” is the detector's calibrated GT false-positive rate, not zero; that FPR is measured at freeze, subtracted, and reported. Where a different baseline is more informative (paper fill for restraint, round-trip GT for CMYK), it is named in the table. A metric whose `gt_copy` score is not at its stated ideal is a harness bug, not a model result.

**The retained v1 safety rule.** The per-tile severe rule and its two companions are defined here once and used everywhere:

```text
oracle_mae(t) = min MAE over the frozen seven-method reference oracle on tile t     (§9.1)
regret(t)     = MAE(t) − oracle_mae(t)
oracle_win(t) = 1[MAE(t) = oracle_mae(t)]
severe(t)     = 1[MAE(t) > 2·oracle_mae(t) + 2]                                    (v1 rule)
```

`severe` is retained unchanged in form because it is v1's safety number and reviewers understand it. v2's oracle set is the seven-method reference set (six classical + LaMa), so v2 severe rates are **not numerically identical** to v1's; `legacy_v1` mode recomputes the six-method v1 oracle to reproduce the old table (Appendix B.5). The severe rule is candidate-relative by construction and is therefore a *safety* metric only; it is never the primary endpoint (that is §7.6) and it never replaces the absolute rules in A6.

---

### 4.1 Axis A — fidelity where ground truth exists

```text
A1  MAE_U      = 1/(|U|·C) · Σ_{p∈U} Σ_c |R(p,c) − G(p,c)|                     [0,255]
A2  dE_U       = 1/|U| · Σ_{p∈U} ΔE00(R(p), G(p))                              [0,100]
A3  SSIM_U     = 1/|U| · Σ_{p∈U} SSIM(L_R, L_G)(p)                            [−1,1]
A4  PSNR_U     = 10·log10(255² / MSE_U)                                       [0,∞) dB
A5  MAE_class  = A1 restricted to a content/hidden-bleed class
    A5b        = quantile_0.90 of per-tile A1 within a class
A6  AF(tile)   = 1 if any absolute rule in the table below fires, else 0
A7  A7(page)   = quantile_0.99 of per-tile A1 over a page's tiles
```

SSIM uses the standard 11×11 Gaussian window (σ=1.5) computed on the **whole tile** (so windows near the seam see real known context), then averaged over `U` only. This is v1's definition and is kept for comparability.

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| A1 | MAE, overall | 0–255 | ↓ | page-level > 15 (catastrophic); per-tile pass/fail is via A5/A6, not a bare A1 cut | `gt_copy` = 0 | Perceptual weight: 2 levels in shadow vs highlight differ; dominated by hard texture |
| A2 | Mean dE00 | 0–100 | ↓ | > 5.0 overall; > 1.5 flat | `gt_copy` = 0 | Direction of drift; a uniform shift can look worse than a local defect |
| A3 | Masked SSIM | −1–1 | ↑ | < 0.88 overall; < 0.98 flat | `gt_copy` = 1.000 | Hue/absolute colour (luminance-structure only); window edge effects |
| A4 | PSNR | 0–∞ dB | ↑ | < 20 dB is a catastrophic floor; reported, never used for ranking | `gt_copy` = ∞ | Same as MAE, in log units; not a primary metric |
| A5 | Class MAE + p90 | 0–255 | ↓ | class mean: flat > 2.0; gradient > 5.0; structure > 25; texture > 45; class p90: flat > 4.0, gradient > 12, structure > 45, texture > 70 | `gt_copy` = 0 each | Class label noise; texture GT itself is a rendering choice |
| A6 | Absolute fail rate | 0–1 | ↓ | > 2% of tiles overall; > 0.5% flat tiles | `gt_copy` = 0 | Thresholds are provisional print tolerances, not yet validated by a press study (O6) |
| A7 | Tail MAE p99 | 0–255 | ↓ | > 60 (catastrophic page tail) | `gt_copy` = 0 | Which tail tiles are visually bad vs merely hard |

**A6 absolute rules.** A tile fails if any of: flat class and (`A1 > 2.0` or `A2 > 1.5`); gradient and (`A1 > 5.0` or `A2 > 3.0`); structure and (`A1 > 25` or `A2 > 6.0`); texture and `A2 > 8.0`; `C1 > 2.0`; on STOP edges only, `B1 > 0` or `B2 > 0`; any trim violation. These are stricter than edge repeat on flat colour, because a visible step on a solid is a customer complaint even if it is the best of a bad candidate set. They are deliberately looser on texture, because GT texture is a render-version choice and no model should be failed for matching statistics rather than pixels. **No threshold here sits below edge repeat's own published mean** (11.50 MAE / 4.01 dE / 3.78 BGE): the reference baseline passes its own absolute rules, otherwise the rules measure candidate difficulty rather than defects.

**Why A1 is not the headline.** v1's own table shows every method with median 1.9–4.7 and mean 11.5–17.4; the mean is a texture-and-tail statistic. v2 reports A1 for comparability but ranks on paired, family-clustered `SystemGain` (§7.6) and reports A5/A6/A7 next to it. This is a disagreement with v1's presentation, not with its metric.

---

### 4.2 Axis B — restraint and non-invention

Restraint has two halves: **do nothing** when the answer is paper (B1–B2, B9), and **invent nothing** that is not a continuation (B3–B7). B1/B2/B7 have GT; B3–B6 are ground-truth-free and are validated separately (§5).

```text
paper(p)   = estimated paper colour of the page (label store only; never given to the model)
ink(p)     = 1[ΔE00(R(p), paper) > 2]
B1         = |{p ∈ U : ink(p)}| / |U|                       on STOP edges          [0,1]
B2         = max 8-connected component size of ink pixels on STOP edges            [px]
B3         = 10⁴ · |E_gen \ dilate(E_exp, 3)| / |U|  −  FPR_prior      [per 10⁴ px, net]
B4         = 10⁴ · (# OCR chars in U, conf > 0.7, unmatched to a known text line) / |U|  −  FPR_ocr
B5         = 1000 · (# face/logo/object detections in U) / (# tiles)   −  1000·FPR_det  [per 1,000 tiles, net]
B6         = mean over tiles of P_fake(known band + strip)                           [0,1]
B7         = |{p ∈ U : ΔE00(R(p),G(p)) > 4 and local_std(G,7×7) < 2, in blobs ≥ 50 px}| / |U|
B8         = max_c |mean_{p∈U_flat}(R(p,c) − G(p,c))|                               [levels]
B9         = |{STOP edges with B1 = 0}| / |STOP edges|                              [0,1]
```

`FPR_prior`, `FPR_ocr`, `FPR_det` are the detectors' false-positive rates measured on frozen GT strips (2,000 strips) and stored with the oracle file; they are subtracted so a perfect fill scores ≈0 on B3–B5.

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| B1 | STOP false-ink rate | 0–1 | ↓ | **any ink pixel on a STOP edge (>0)** | `paper_fill` = 0; `gt_copy` = 0 | Paper estimate error; a legitimate tint that matches paper within 2 dE00 |
| B2 | Largest false-ink blob | 0–∞ px | ↓ | **any blob on a STOP edge (>0)** | `paper_fill` = 0; `gt_copy` = 0 | A very faint large blob below the ink threshold |
| B3 | Invented-edge density (net) | 0–10,000 /10⁴ px | ↓ | > 20 on flat/STOP; > 100 overall (provisional) | `gt_copy` ≈ 0 after FPR subtraction | Legitimate texture continuation counted as invention; subtle low-contrast objects |
| B4 | Invented OCR characters (net) | 0–∞ /10⁴ px | ↓ | > 0 on STOP/flat; > 2 overall | `gt_copy` ≈ 0 after FPR subtraction | Non-Latin scripts, decorative type, OCR false positives |
| B5 | Object/face/logo hits (net) | 0–∞ per 1,000 tiles | ↓ | > 1 per 1,000 tiles after FPR subtraction | `gt_copy` ≈ 0 after FPR subtraction | Objects no detector knows; abstract “new shape” |
| B6 | Continuation-judge fake rate | 0–1 | ↓ | > 0.10, or > 2× the judge's GT FPR | `gt_copy` ≈ judge FPR (calibrated 5%), not 0 | Judge may key on generator fingerprints rather than semantics |
| B7 | Invented-content area (GT) | 0–1 | ↓ | > 0.002 | `gt_copy` = 0 | Wrong content that happens to be within 4 dE00; hard texture |
| B8 | Solid continuation drift | 0–255 | ↓ | > 2 levels on a flat FULL edge | `gt_copy` = 0; `edge_repeat` ≈ 0 | Non-uniform drift within the strip (reported via p99) |
| B9 | STOP accept rate | 0–1 | ↑ | < 0.98 | `paper_fill` = 1; `gt_copy` = 1 | The cause of failure; use B1/B2/B3 with it |

**B8 is the absolute flat-drift metric v1 lacked.** v1's severe floor caught Telea and LaMa drifting 3–5 levels on flat colour only because it compared them to an oracle; B8 fails them regardless of which other methods ran. It is computed on FULL flat edges (GT is a continued solid), where the correct answer is known exactly and a 1-level drift is achievable by recipe sampling.

**B9 is the page-level restraint decision.** A STOP edge is “accepted” if the model produced no ink at all; B9 is the fraction of STOP edges that pass. A model that produces one 2 px speck fails that edge. This is harsh by design: on a stop-at-trim page, a speck is a visible defect at print size.

---

### 4.3 Axis C — seam continuity

```text
C1  seam_step = mean_{(p,q)∈P} 1/C · Σ_c |[R(p,c) − R(q,c)] − [G(p,c) − G(q,c)]|     [0,255]
C2  seam_dE   = mean_{(p,q)∈P} |ΔE00(R(p),R(q)) − ΔE00(G(p),G(q))|                  [0,100]
C3  BGE       = per v1: for p∈U with known 4-neighbour, mean over directions of
                |(R(p)−R(nb)) − (G(p)−G(nb))|, then mean over p                     [0,255]
C4  SCS       = line-continuation score, §6                                          [0,1]
C5  TCS       = text-continuation score, §6                                          [0,1]
C6  UER       = |salient generated edges at seam without a known continuation| /
                |salient generated edges at seam|                                    [0,1]
C7  TSD       = mean |R_A − R_B| over the overlap of two adjacent tiles, same page,
                on the 50%-overlap subset (§2.2)                                         [0,255]
C8  RCG       = mean |R_page − R_composited| over the ring (whole-page vs tile mode)  [0,255]
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| C1 | Seam step error | 0–255 | ↓ | > 2.0 | `gt_copy` = 0; `edge_repeat` ≈ 0 on solids | A seam that has the right step but the wrong texture across it |
| C2 | Seam dE error | 0–100 | ↓ | > 1.0 | `gt_copy` = 0 | Very local colour break narrower than one pixel pair |
| C3 | Boundary gradient error (v1) | 0–255 | ↓ | > 4.0 overall; > 2.0 flat | `gt_copy` = 0; `edge_repeat` = 3.78 passes | Wrong-angle structure, offset lines, wrong colour along a line |
| C4 | Line continuation | 0–1 score + binary pass | ↑ | fail if `match_rate < 0.90` or any matched line breaches a per-line tolerance; `n/a` (excluded) when no known line reaches the seam; SCS reported but not gating | `gt_copy` = pass where lines exist; `n/a` on line-free tiles | Continuations that no line detector sees; line-free tiles carry no signal |
| C5 | Text continuation | 0–1 score + binary pass | ↑ | fail if `match_rate < 0.90` or any matched text line breaches a tolerance; `n/a` when no text line reaches the seam; TCS reported but not gating | `gt_copy` = pass where text exists; `n/a` otherwise | Fonts OCR cannot read; decorative/non-Latin type |
| C6 | Unsupported-edge ratio | 0–1 | ↓ | > 0.15 | `gt_copy` ≈ 0 | Legitimate high-frequency texture; continuation prior errors |
| C7 | Tile-seam disagreement | 0–255 | ↓ | > 2.0 | `gt_copy` = 0 | Models that hide inconsistency by blending, not by agreement |
| C8 | Ring-consistency gap | 0–255 | ↓ | > 3.0 | `gt_copy` = 0 | Models that are deterministic but context-dependent (the gap is the point) |

**C1 vs C2 vs C3.** C1 is a directed step across the trim line; C2 is a colour-distance version in ΔE; C3 is v1's gradient error, retained because all historical numbers use it and because it sees the one-sided gradient direction. They are correlated but not redundant: C2 catches a chroma-only step, C3 catches a luminance ramp mismatch that averages to zero over the ring, C1 catches a step that happens to preserve ΔE because both sides shifted together. Report all three; C2 is the print-relevant one.

**C7/C8 are consistency, not quality.** They do not measure whether the fill is right; they measure whether the method gives the same answer when the same page is presented twice with different tilings. A method that is inconsistent cannot be productionised even if its per-tile mean is good, because the assembled ring will quilt. The **reference composite** for C8 is: place each tile's prediction in page coordinates; in a 32 px overlap, blend with a raised-cosine feather whose weights sum to 1; outside overlaps, take the single covering tile. The same rule is used for both the whole-page and tile-composite arms so C8 measures model consistency, not a compositing choice. **C4/C5 are scored only where a known line/text line actually reaches the seam**; tiles with none are `n/a`, excluded from the C4/C5 denominator, and reported as `line_coverage` / `text_coverage`. This is what makes `gt_copy` near-perfect on a solid page: there is no line to continue, so C4 is not applicable, not failed.

**C8 applicability.** C8 compares a single whole-page pass with the tile composite. A model that runs whole-page inference as four seam-anchored passes (one per edge) has no single-pass arm, so C8 is `n/a` for that submission: `ring_gap` is left empty, C8 is excluded from its axis C aggregate and the C8 failure threshold is not applied. Such a submission is scored on C7 only, and the declaration (`passes_per_page = 4`) is recorded in the submission package (§13.3).

---

### 4.4 Axis D — known-pixel integrity

```text
D1  trim_violations = |{p ∈ K : R_raw(p) ≠ I(p)}|  → MUST be 0; otherwise disqualification
D1b final_trim_identity = 1[R_final(p) = I(p) for all p ∈ K]  → must be true (post-clamp gate)
D2  preclamp_changed      = |{p ∈ K : R_raw(p) ≠ I(p)}|      (harness-computed, not self-reported)
D3  preclamp_changed_frac = min(1, D2 / |K_seam2|),  K_seam2 = known pixels within 2 px of the seam
D4  preclamp_changed_max  = max over p ∈ K of max_c |R_raw(p,c) − I(p,c)|   [0,255]
D5  regen_trim_px         = |{p ∈ K : effective_latent_mask(p) = unknown}|  [count]
D6  clamp_seam_dE         = mean over seam pairs whose known side had a pre-clamp change of
                            |ΔE00(R(p),R(q)) − ΔE00(G(p),G(q))|; 0 if none     [0,100]
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| D1 | Raw trim violations | 0–∞ | ↓ | **any value > 0 → DQ** | `gt_copy` = 0; `edge_repeat` = 0 | Nothing; this is the production contract |
| D1b | Final trim identity | bool | — | **false → DQ** | `gt_copy` = true | Nothing |
| D2 | Pre-clamp changed pixels | 0–∞ | ↓ | > 0 for production-candidate badge (unless D6 passes); report all | `edge_repeat` = 0 | Magnitude and location (D3/D4/D6) |
| D3 | Changed fraction near seam | 0–1 | ↓ | > 0.001 | `edge_repeat` = 0 | One 40-level pixel is invisible to a fraction metric |
| D4 | Max pre-clamp change | 0–255 | ↓ | > 8 levels | `edge_repeat` = 0 | Whether the change is in a visually critical region |
| D5 | Regenerated trim pixels | 0–∞ | ↓ | > 0 on tile-mode or left/top whole-page seams for declared `L ≤ 16`; expected and scored on right/bottom whole-page seams | `gt_copy` = 0 | Models that declare `L=32` and accept a 16 px regenerated band |
| D6 | Clamp-seam dE | 0–100 | ↓ | > 1.5 | `gt_copy` = 0 | A clamp seam visible as a texture/boundary discontinuity but not as colour |

**v2.1 correction (DD83).** In v2.0, D1 and D2 had the same formula with different consequences (DQ vs badge), which disqualifies every full-image model even when it composites like production does. v2.1 separates the two outputs a learned submission has: `R_sub`, what the submission returns (it MUST copy known pixels itself, as production places the original page unchanged), and `R_net`, the network's own pre-composite output, which a submission SHOULD expose (`last_raw`). **D1 is computed on `R_sub`** and remains a disqualification. **D2–D4 and D6 are computed on `R_net`** when exposed (otherwise on `R_sub`, which makes them 0) and measure how much of the trim the network rewrote — a property of the model, reported and used for the production-candidate badge, never a DQ.

**D1 is a gate, not a score.** The harness keeps the raw pre-clamp output. A submission that changes a trim pixel is disqualified; it is not “penalised 5 points”. This mirrors the production PDF, where the original page is placed unchanged. `D1b` verifies the final (clamped) canvas independently; D1 would otherwise be trivially true because the harness clamps. The submission's `last_changed` attribute is informational only and is never trusted for scoring.

**D2–D6 exist because a clamp is not free.** A model that regenerates 8 px inside the trim and is then clamped has a one-pixel-wide boundary where the clamped known pixels meet freshly generated ones. v1 counted that but did not score it. D6 measures the resulting seam in the same units as C2, so a model that “fixes” its mask leakage by relying on the clamp is visible.

---

### 4.5 Axis E — colour fidelity

All E metrics are computed in **page space**, after the declared round-trip. `floor` is the round-trip GT error (§2.8). For RGB pages, floor is 0. For CMYK pages, `floor = E5(roundtrip_gt)`.

```text
E1  page_dE      = mean_{p∈U} ΔE00(R_page(p), G_page(p))                          [0,100]
E2  flat_drift_c = |mean_{p∈U_flat}(R_c(p) − G_c(p))| for c ∈ {L*,a*,b*} or {C,M,Y,K} [levels/%]
    flat_drift_E = mean_{p∈U_flat} ΔE00(R,G)                                       [0,100]
E3  rich_black_raw = (ΔK, ΔCMY, ΔTAC) on rich-black FULL edges                      [% dot]
    ΔCMY = max_c |mean(R_c − G_c)| for c∈{C,M,Y}; TAC = C+M+Y+K
    rich_black_net = rich_black_raw − roundtrip_floor_richblack
E4  near_white_leak = |{p∈U_paper : |ΔE00(R(p), paper)| > 2}| / |U_paper|,
    U_paper = ring pixels whose GT is within 2 dE00 of paper                       [0,1]
E5  cmyk_roundtrip_dE = E1 on CMYK pages;  net = E5 − floor                        [0,100]
E6  gamut_handling = |{p∈U_out : ΔE00(R(p), G_clip(p)) > 2}| / |U_out|,
    U_out = GT pixels outside the model-space gamut; G_clip = GT after declared mapping [0,1]
E7  spot_recipe_error = mean over spot pixels of |tint(R) − tint(G)|                [% tint]
E8  colour_space_declaration = declared page space/profile hash matches page        [bool]
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| E1 | Page-space dE00 | 0–100 | ↓ | > 1.5 flat; > 5.0 overall | `gt_copy` = 0 | Direction and localisation; a large but uniform cast |
| E2 | Flat channel drift (absolute) | levels/% | ↓ | warn > 1 level (RGB) / 1% dot (CMYK); fail > 2 | `gt_copy` = 0; `recipe_match` < 1 dE | Non-uniform drift inside a nominally flat area (report p99/E1) |
| E3 | Rich-black error (net) | % dot | ↓ | net ΔK > 2%; net ΔTAC > 10%; net ΔE > 2 | `roundtrip_gt` net = 0 | Ink-limit/overprint behaviour on press; only a proxy |
| E4 | Near-white leak (two-sided) | 0–1 | ↓ | > 0.005 | `gt_copy` = 0; `paper_fill` = 0 | Paper texture and optical brighteners |
| E5 | CMYK round-trip dE | 0–100 | ↓ | net > 1.5 | `roundtrip_gt` net = 0 | Wrong rendering intent on one channel; black generation (GCR/UCR) choices |
| E6 | Gamut handling error | 0–1 | ↓ | > 0.05 | `roundtrip_gt` = floor | What the model does outside gamut (it has no way to signal it) |
| E7 | Spot tint error | 0–100% | ↓ | net > 2% tint or net ΔE > 1.5 | `roundtrip_spot_gt` net = 0 | Tint ramp interpolation and overprint of spot over CMYK |
| E8 | Colour-space declaration | bool | — | mismatch → DQ | exact match | Intentional working-space changes that are declared |

**E5's floor is not optional.** Passing GT through sRGB→CMYK→sRGB and back already produces a nonzero dE; a model cannot be required to beat the transform. The harness publishes the floor per page and per profile. A submission that reports E5 without the floor, or that chooses a different intent for the model than for the floor, is invalid. E3's rich-black metrics are net of `roundtrip_floor_richblack` for the same reason: `roundtrip_floor_richblack` is the dE/ΔK/TAC produced by passing the GT rich-black strip through the declared pipeline and back; a GT rich black C60 M40 Y40 K100 passed through an sRGB proxy will not return the same recipe, and an RGB-proxy entry must not be failed for the transform's black-generation choice. E2's `recipe_match` sanity baseline is a classical fill that samples the mean known flat colour and fills uniformly; it should score <1 dE00 on a true solid.

**Wide-gamut pages.** The colour track includes Adobe RGB pages: E1/E2 are computed on them in page space with the Adobe RGB profile, and the round-trip floor is measured with `roundtrip_gt` exactly as for CMYK. An Adobe RGB page scored through a default sRGB proxy has a nonzero floor; the floor is reported, never assumed zero.

### 4.6 Axis F — geometry robustness

F is evaluated on a dedicated **robustness manifest** of 200 Tier-A-style pages / 40 families, generated for this purpose and disjoint from the T1/T2 eval pages, plus the Tier A partial-bleed pages. Each page is rendered once clean and once per injected condition; the GT ring is recomputed for the injected geometry and stored with the variant. The injection never changes the GT ring except by the declared geometry change.

```text
F1  trim_inflation(δ)  = MAE_δ / max(MAE_0, 0.1)     for outward trim error δ ∈ {1,2,4} px
F2  margin_coping      = |{tiles at δ=2 whose output ink share is within ±5% of GT}| / n
    ink_share(R)       = fraction of U with ΔE00(R, paper) > 2
F3  cropmark_leak(o)   = |{p∈U : ΔE00(R(p), mark_ink) < 2 and dist(p, mark_line) < 2}| / |U|
    offset o ∈ {0,9,38} px; mark = 0.25 pt, 100% K, parallel to the edge, full edge length
F4  partial_accuracy   = |{synthetic PARTIAL edges whose output is classified correctly}| / n
    classify(R) = "paper" if ≥99% of U is within 2 dE00 of paper, else "continue"
F5  margin_false_alarm = |{clean FULL edges where paper_share(R) > paper_share(G) + 0.05}| / n
    paper_share = fraction of U within 2 dE00 of paper
F6  inward_inflation(δ)= MAE_δ / max(MAE_0,0.1)      for inward trim error δ ∈ {1,2} px
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| F1 | Outward-trim MAE inflation | ratio | ↓ | > 1.25 at δ=1; > 1.5 at δ=2; > 3.0 at δ=4 | `trim_aware_fill` ≈ 1.0 (oracle margin detector) | It measures coping, not whether the margin was detected |
| F2 | Margin coping rate | 0–1 | ↑ | < 0.95 | oracle trim detector = 1.0 | Correct behaviour for the wrong reason (e.g., always paper) |
| F3 | Crop-mark leak rate | 0–1 | ↓ | > 0.01 at each offset 0/9/38 | `mark_filter` = 0; `gt_copy` = 0 | Marks whose colour is close to artwork; marks outside the rendered canvas |
| F4 | Partial-bleed decision accuracy | 0–1 | ↑ | < 0.90 | `paper_oracle` = 1.0 | AMBIGUOUS GT is synthetic; it is not a natural class |
| F5 | Margin false alarm | 0–1 | ↓ | > 0.01 | `gt_copy` = 0 | A model that suppresses legitimate pale content |
| F6 | Inward-trim inflation | ratio | ↓ | > 1.5 at δ=1; > 2.0 at δ=2 | `trim_aware_fill` ≈ 1.0 | Artwork genuinely clipped by a bad trim is unrecoverable; this is a proxy |

`trim_aware_fill`, `mark_filter` and `paper_oracle` are **reference implementations**, not models: `trim_aware_fill` detects a paper-white margin from the known band and excludes it before edge repeat; `mark_filter` removes the injected mark colour before filling; `paper_oracle` classifies paper vs continuation using GT only (an upper bound, not a deployable method). They exist so each F metric has a near-perfect sanity baseline; they are added to `expected_baselines.json` at freeze.

**Why F1 uses a ratio to δ=0.** v1 measured edge-repeat MAE rising from 12.5 to 88 at a 2 px outward trim error (7.0×). An absolute threshold would be dominated by how hard the page is; the ratio isolates the brittleness. A model that detects paper-white margin and excludes it from its context should keep the ratio near 1. A model that simply copies the last row will fail catastrophically, which is the correct outcome: trim accuracy is first-order and a generator must not amplify it.

**Why F6 is separate.** Outward trim error creates a paper margin in the input; inward error clips real artwork and leaves a white sliver *inside* the trim, which the model cannot legally repair (trim is immutable). F6 measures whether the model's fill at the seam degrades when the known context is clipped; it is a robustness proxy, not a repairable defect.

**Crop marks: scope.** Crop marks are out of scope as *output* geometry (production draws them as vectors, §2.7). They are in scope as a *distractor in the input* for F3: the benchmark injects a mark at 0, 9 or 38 px outside the trim and measures whether the model copies it into the strip. V5 (validity) excludes edges whose **GT ring** contains marks; F3 pages are a separate manifest, not V5-invalid eval pages.

---

### 4.7 Axis G — determinism and variance

```text
G1  same_seed_id  = 1[∀p : R_run1(p) = R_run2(p)] on a 10% rerun subset
G2  seed_spread_MAE = max_s MAE − min_s MAE over s ∈ {1..5} seeds, per tile
    seed_spread_severe = max_s severe_rate − min_s severe_rate over the 5 seeds
G3  orient_gap_MAE = max_r MAE_r − min_r MAE_r over r ∈ {0,90,180,270}, per tile
    orient_gap_dE  = max_r dE_r − min_r dE_r over the four orientations
G4  batch_gap     = max over batch sizes {1,4,8} and shuffled order of
                    |metric(batch) − metric(1)|; fail on any difference > 1e-6
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| G1 | Same-seed identity | bool | — | **false → DQ** for deterministic entries | `edge_repeat` = true | A stochastic sampler that is seeded but not portable across GPU/driver |
| G2 | Seed metric spread | 0–255 MAE | ↓ | > 0.5 MAE, or severe-rate range > 1 pp | `edge_repeat` = 0 | The shape of the output distribution, only its metric spread |
| G3 | Orientation gap | 0–255 MAE | ↓ | > 2.0 MAE or > 0.5 dE | `gt_copy` = 0 | Content-dependent orientation bias that averages out |
| G4 | Batch/order gap | 0–255 MAE | ↓ | any nonzero beyond floating tolerance | `edge_repeat` = 0 | Non-determinism in model parallelism that is invisible at this batch |

G1 is a gate for the production-candidate badge. A model may be explicitly stochastic; it then declares `stochastic=true`, runs 5 seeds on 100% of the test manifest, and is scored as a distribution (mean + range). It cannot receive the production-candidate badge, because a page whose strip changes between runs cannot be reviewed and released without a human.

---

### 4.8 Axis H — cost

All timings follow the quiet protocol (§11.3): dedicated GPU, locked clocks, power limit declared, 20-tile warm-up discarded, batch size 1 unless declared, ≥100 timed tiles, median and p90 reported, no concurrent workload, CPU/GPU utilisation and temperature recorded.

```text
H1  runtime_p50 = median over timed tiles of wall-clock inference + post-process, batch 1   [ms]
H2  page_runtime = Σ runtime of the page's sampled tiles + assembly, at the declared tile size [s]
H3  realised_gain_per_s = (SystemGain per page) / page_runtime                             [MAE/s]
H4  peak_vram, load_time, throughput batch 1/4/8                                           [MB, s, tiles/s]
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline (near-perfect) | What it fails to capture |
|---|---|---|---|---|---|---|
| H1 | p50 tile runtime, 512 | 0–∞ ms | ↓ | > 100 ms on the declared single consumer GPU | `edge_repeat` ≈ 0.5 ms | Tail latency and queueing under production load |
| H2 | Page runtime | 0–∞ s | ↓ | > 3.5 s/page at 512 (28 × 100 ms + assembly); > 2.5 s/page at 1024 (20 tiles); whole-page single pass > 1.5 s | `edge_repeat` < 0.1 s | Batching effects across pages |
| H3 | Realised gain per second | −∞–∞ MAE/s | ↑ | must be > 0 at the certified gate operating point | `edge_repeat` = 0 by definition | Whether the gain is worth a human review step (a business cost, not measured) |
| H4 | VRAM / load / throughput | MB, s, tiles/s | ↓/↑ | OOM, peak VRAM > declared GPU memory, or load time > 60 s → fail; otherwise report | `edge_repeat` trivial | Energy, dollar cost, multi-tenant contention |

H3 uses the **gated** gain, not the raw MAE difference: `(SystemGain per page) / (page_runtime_s)`. A model whose raw gain is large but whose gate rejects most pages has a small realised gain. v1's `sd_refine` matched classical quality at ~2,600× the cost, so its realised gain per second was effectively zero. A generative model that gains 1 MAE per page at 1.4 s/page is a 0.7 MAE/s trade; whether that is worth it is a deployment decision, but the benchmark must show it.

---

### 4.9 Axis I — scale generalisation

| ID | Metric | Formula | Range | Dir | Failure threshold | Sanity baseline | What it fails to capture |
|---|---|---|---|---|---|---|---|
| I1 | Bleed-width ratio, 60 px | `MAE(60)/MAE(38)` (ratio = 1 if both are 0) | ratio | ↓ | > 1.5 | `gt_copy` = 1.0 | Very large bleed where continuation is impossible |
| I2 | Bleed-width ratio, 19 px | `MAE(19)/MAE(38)` (ratio = 1 if both are 0) | ratio | ↓ | > 1.3 | `gt_copy` = 1.0 | Small-bleed latent quantisation differences |
| I3 | DPI consistency | `max_dE(150,300,600) − min_dE` for the same physical page | dE | ↓ | > 1.0 | `gt_copy` = 0 | Renderer differences masquerading as model scale effects |
| I4 | 1024 tile gain | `MAE(512) − MAE(1024)` (0 if both 0) | MAE | ↑ | < 0 (1024 worse) | `gt_copy` = 0 | Cost of 1024 (H1) |
| I5 | Whole-page vs tile gap | `MAE_page − MAE_tile` | MAE | ↓ | > 2.0 | `gt_copy` = 0 | A page model that is good per tile but inconsistent globally |
| I6 | Aspect-ratio gap | `MAE(long-thin)/MAE(normal) − 1` (0 if both 0) | ratio | ↓ | > 0.5 | `gt_copy` = 0 | Very large pages where OOM forces tiling |

The scale track uses the same page set at 150/300/600 DPI only for synthetic pages (Tier A), because the private real set has one native render per page. Physical bleed width is held constant across DPI: 0.125 in at 150/300/600 is 19/38/75 px. The 5 mm (60 px at 300 DPI) and 150 DPI variants are generated in Tier A; the private set uses 38 px and 60 px where the PDF provides it.

---

### 4.10 Axis J — corners

The L-shaped corner is where two independently generated edges must agree. It is scored separately because v1's corner tiles (230 of 1,730) were pooled into the overall mean and a corner is the most visible part of a mis-registered ring.

```text
J1  corner_MAE, corner_dE     = A1/A2 restricted to the corner tile's ring (both arms)
J2  corner_arm_disagreement   = mean |R_corner − R_edge| in the overlap between a corner tile
                                and the adjacent edge tiles, on the 50%-overlap subset only
J3  corner_structure_pass      = 1 if every corner arm with ≥1 known line passes C4; n/a if neither arm has a line
J4  corner_miter_dE           = dE00 between the two arms at the 45° miter line, on solid/pattern corners
J5  corner_fail_rate          = |{corner tiles with any A6/B1/C1 failure, or C4 failure on an applicable arm}| / |corner tiles|
```

| ID | Metric | Range | Dir | Failure threshold | Sanity baseline | What it fails to capture |
|---|---|---|---|---|---|---|
| J1 | Corner MAE (and dE) | 0–255 / 0–100 | ↓ | MAE > 1.5× the same-page edge mean; dE > 1.5 | `gt_copy` = 0 | Corner content is often harder; a ratio is fairer than an absolute |
| J2 | Corner-arm disagreement | 0–255 | ↓ | > 2.0 (50%-overlap subset only) | `gt_copy` = 0 | Models that buffer the whole page (no independent arms to compare) |
| J3 | Corner structure pass | 0/1/n-a | ↑ | any applicable arm fails C4 | `gt_copy` = 1.0 (or n/a) | Curved or diagonal structure at the corner; line-free corners |
| J4 | Miter dE | 0–100 | ↓ | > 1.5 | `gt_copy` = 0 | Corners that are not solids/patterns; most real corners are image |
| J5 | Corner fail rate | 0–1 | ↓ | > 5% | `gt_copy` = 0 | Corner defects hidden by forgiving content |

**Why corners can fail even when edges pass.** A model that fills each edge independently in canonical orientation has no mechanism to make the two arms meet: the horizontal arm's last 38 px and the vertical arm's first 38 px are generated from different contexts. The L is the only place where both continuity constraints are visible at once. Whole-page mode (T2) is the primary corner instrument; corner tiles (T1) are the cheap diagnostic. J2 is only defined for methods that produce tiles independently; whole-page methods report `n/a` with a reason, and J1/J3/J4 still apply.

---

## 5. Hallucination and restraint metrics in detail

### 5.1 Why this is hard

Fidelity metrics need GT; hallucination is precisely the failure mode where the model produces something the page does not contain, and it matters most exactly where GT is unavailable (a customer page with no known bleed). There is no single detector that can say “this is an invented logo” without a reference. v2 therefore uses **four independent detector families**, validates each against human labels, and makes only the ones that clear a pre-registered precision bar gating. The rest are advisory and are reported, not scored.

The four families are deliberately different in what they can see:

| Family | Sees | Strong at | Blind to |
|---|---|---|---|
| **F1 structure-extension** (B3, C6) | edges/lines crossing the seam | new edges, broken rules, wrong-angle structure | low-contrast texture, photographic content |
| **F2 OCR** (B4) | characters | invented letters, words, numbers, logos with text | non-text objects, non-Latin/decorative type |
| **F3 object detectors** (B5) | faces, logos, common objects | photorealistic invention of people/products | abstract shapes, novel objects |
| **F4 learned continuation judge** (B6) | known band + strip | holistic “does this look continued?” | anything the judge's training distribution misses; may learn generator fingerprints |
| **F5 GT-support** (B7) | GT | everything, where GT exists | where GT does not exist (the real production case) |

F1–F4 are the four independent no-GT detector families; F5 is the GT-referenced support metric and is not a detector.

### 5.2 With ground truth

**B7 (invented-content area)** is the primary GT metric. It counts pixels that are far from GT in colour (`ΔE00 > 4`) *and* sit in a locally flat GT neighbourhood (`local_std(G) < 2`), clustered into 8-connected blobs of at least 50 px. The flatness condition is what separates “invented a mark on paper” from “texture continued with different noise”: on a flat paper region, any 50 px of wrong colour is an object or a smear, not a texture. On a textured photo, the same 4 dE difference is expected and is not counted.

**Structure continuation with GT** is measured by edge-map agreement in the strip:

```text
E_R = Canny(L_R) ∩ U,  E_G = Canny(L_G) ∩ U
edge_precision = |dilate(E_G,2) ∩ E_R| / |E_R|
edge_recall    = |dilate(E_R,2) ∩ E_G| / |E_G|
halluc_edges   = |E_R \ dilate(E_G,3)| / |U|        [px/px]
missed_edges   = |E_G \ dilate(E_R,3)| / |U|
```

`halluc_edges` is B3-with-GT; it is the cleanest hallucination metric available and is used to validate the no-GT version of B3 (the two should correlate on the same tiles). `edge_precision`, `edge_recall` and `missed_edges` are **supporting diagnostics**, not scored leaderboard metrics; they exist to validate the detectors and to explain a B3 result, and they carry no separate pass/fail threshold.

**Restraint with GT** is B1/B2/B9 on STOP/NO_INK edges. The GT paper colour is known per page, so “no ink” is exactly measurable. This is the only place where “correct answer is paper” can be scored without inference.

### 5.3 Without ground truth

**F1 — Structure-extension prior (B3, C6).** Build an expected edge field from the known band: Canny with hysteresis (low 20, high 60 levels) and LSD (minimum length 12 px, minimum contrast 3 levels). For every edge pixel within 4 px of the seam, extend it across the strip along its local structure-tensor orientation (11×11 window) for `b` pixels; skip tangents that graze the seam (`|tangent · seam_normal| < 0.2`) because their extension is degenerate. Dilate the predicted field **once** by 3 px. A generated edge pixel is salient if `|∇| > 8` levels; it is unsupported if it is not within the dilated predicted field. B3 normalises by strip area; C6 normalises by generated salient edge count. The prior is deliberately conservative: it over-predicts continuation so its false-positive rate on GT strips is low while its recall of subtle invention is limited. That trade is chosen because a gating metric must not accuse a correct fill. The prior's GT false-positive rate is measured once on a separate 2,000-strip detector-calibration set (distinct from the 1,200-strip human-labelled set) at freeze and frozen; B3 and C6 are reported **net of that FPR**, and the raw and net values are both in the CSV.

**F2 — OCR (B4).** Run OCR on the known band and on the strip. Project every known text line across the seam (baseline angle, cap height, colour) and predict which character boxes could legitimately continue. Any OCR token with confidence > 0.7 in the strip that is not within one cap-height of a predicted line is “unmatched”. Count per 10⁴ strip pixels. On Tier A, synthetic text crosses the trim, so the detector's recall can be measured exactly; on Tier B/C, human labels are required. OCR's GT false-positive rate (characters it hallucinates on clean GT strips) is measured and frozen; B4 is reported net of it.

**F3 — Object/face/logo detectors (B5).** An ensemble (face detector, open-vocabulary detector, logo detector) run on the strip with the known band as context. A detection is “invented” if it is not present in the known band and has no continuation into it (IoU with a known-band detection < 0.1 after projection). This is high-precision, low-recall; it is a gating metric only for faces and legible logos, where a single false positive is a serious defect. Detector versions and thresholds are frozen and hashed; the ensemble's GT false-positive rate is measured and frozen, and B5 is reported net of it.

**F4 — Learned continuation judge (B6).** A binary classifier `J(known band, strip) → P(fake)` trained on public data only: positives are GT strips (true continuation); negatives are (a) strips from a different page, (b) paper-filled strips on inked edges, (c) model outputs collected across generators, (d) synthetically perturbed GT (shift, rotate, recolor, paste an object). The judge is validated **leave-one-generator-out**: trained on all generator families except one, tested on the held-out family, to reduce fingerprint learning. The generator pool used to train the judge is **disjoint from the 400 model strips that carry human labels**, so the precision estimate is not contaminated by train/test overlap. For a submission whose generator family was never in the judge's pool, the judge is **advisory only**; gating requires either a covered generator family or a held-out validation that includes that family. Threshold is chosen at 5% FPR on GT strips and frozen. The score is reported as `judge_fake_rate`; it gates only if the human-label validation below clears its precision bar at the stated deployment prevalence.

### 5.4 Validation against human labels

A dedicated **hallucination validation set** of **1,200 strips** is built once and frozen:

| Component | Count | Construction |
|---|---|---|
| GT positives | 400 strips | Tier A + Tier B, balanced across STOP/FULL/flat/photo/text |
| Injected hallucinations | 400 strips | paste a logo, a word, a face, a shifted texture patch, or a new rule into a GT strip; record mask and category |
| Model negatives | 400 strips | outputs from ≥5 baseline methods, including raw SD2-style invention and LaMa/edge-repeat failures |
| Ambiguous (subset) | 200 of the 1,200 | preselected subtle continuations; analysed separately for annotator disagreement, **not additive** |

The set is deliberately enriched: invented content is present in ~33% of strips versus a production prevalence that is estimated at 5% or lower. **Precision must therefore be reported at the deployment prevalence, not at the set prevalence.** For a detector with sensitivity `Se` and specificity `Sp`, the prevalence-adjusted PPV at prevalence `π` is

```text
PPV(π) = Se·π / (Se·π + (1−Sp)(1−π))
```

Three annotators (prepress operators, not ML researchers) label each strip with a binary “contains invented content that was not a continuation” plus a category and a confidence. Annotation protocol: the strip and 64 px of known context are shown at print size on a colour-managed display; the seam is marked; the annotator may toggle a 4× zoom. Target Krippendorff's α ≥ 0.70; if lower, the category is re-defined and the set relabelled.

Each detector is evaluated on the human labels with:

```text
sensitivity Se, specificity Sp, AUROC, average precision
PPV(0.05) from the formula above
threshold fixed at 95% specificity on the separate 2,000-strip GT detector-calibration set;
never tuned on the 1,200 human-labelled strips
95% interval for PPV(0.05): 1,000-resample bootstrap over strips, clustered by page/generator
```

A detector is **gating** only if the lower bound of the bootstrap 95% interval on `PPV(0.05)` is ≥ 0.85 and `AUROC ≥ 0.85` on the frozen 1,200-strip set; otherwise it is **advisory** (reported, not used in pass/fail). The operating point is pre-specified (95% specificity), not the point that maximises PPV on the same strips used to compute the bound; max-then-bound is not a 95% statement. With only 400 clean model strips, the FPR that supports `PPV(0.05) ≥ 0.85` at `Se = 0.9` is ≈0.75%, which is a zero-FP knife-edge in 400 strips; if the interval cannot clear the bar, the detector is advisory, not gating. This rule prevents the benchmark from disqualifying models on the strength of a detector nobody has validated. If no detector clears the bar, the benchmark says so: the gating hallucination claim is not available, and the human study (§12) becomes the only authority. That is an acceptable outcome; pretending otherwise is not.

**Synthetic injection is not validation.** Injected hallucinations have sharp, known boundaries and are easier than real ones. They are used to measure detector *recall* and to debug, never to set the precision threshold. The threshold comes from human labels on model outputs.

### 5.5 Restraint without ground truth

The no-GT restraint decision is: *given the known band, is paper the right answer?* This is a run-time decision, not a metric, but it can be scored on the STOP subset because GT exists there.

Two approaches are specified:

1. **Known-band paper classifier.** Compute `near_white` share, paper-consistency, ink coverage and the distance of the last known row from paper. If the known band within 8 px of the seam is >98% paper, the correct strip is paper. B9 then measures whether the output respected it. This is the v1 confidence feature family, extended; it is allowed because it uses known pixels only.
2. **Generation-consistency gate.** Compare the model's strip to a deterministic paper fill. If the model's output is not closer to paper than to its own continuation prior on a known-paper edge, reject. This is a run-time gate feature, not a metric.

The benchmark's restraint metrics (B1/B2/B7/B9) are computed from GT and are therefore *evaluation*, not run-time features. A submission's confidence gate may use only the allowed feature namespace; it may not read the STOP label.

---

## 6. Structure-continuation metric in detail

### 6.1 What must be measured

A rule, border, text baseline or horizon that crosses the trim must continue on the other side at the same **angle**, **offset**, **width** and **colour**. v1's `boundary_gradient_error` measures a magnitude mismatch at the seam; it is blind to a line that continues at 5° off, or a 2 px offset, or a line that is the right colour but half the width. The structure-continuation score (SCS) is a per-line matching estimator.

### 6.2 Detection

Run on the Lab L* channel, at the scored resolution:

1. **Segments:** LSD (line segment detector) on the known band and on the strip separately, plus a probabilistic Hough transform for long thin rules. Minimum length 12 px, minimum contrast 3 levels.
2. **Edges:** Canny with hysteresis (low 20, high 60 levels) for non-straight structure; used for the edge-match metrics, not for SCS.
3. **Text:** OCR line boxes on known band and strip; each box provides a baseline angle, cap height, x-height and mean colour.

A segment is a **known line** if one endpoint is within 3 px of the seam and the segment has at least 8 px on the known side. A segment is a **generated line** if it has at least 8 px on the unknown side. Segments shorter than 8 px on either side are ignored (they cannot be matched reliably).

### 6.3 Matching

For each known line, extend its ray into the strip. A generated line matches if all of:

```text
angle     |Δθ| ≤ 5°          (undirected; wrap at 90° for lines)
offset    perpendicular distance between the two lines at the seam ≤ 3 px
gap       distance along the ray between the known endpoint and generated start ≤ 3 px
overlap   projected overlap length ≥ max(8 px, 0.25 × known-line length)
```

Match greedily by a cost `cost = (Δθ/5)² + (offset/3)² + (gap/3)²`; each generated line matches at most one known line. Unmatched known lines are **missed continuations**; unmatched generated lines near the seam are **unsupported edges** (C6/B3).

### 6.4 Scoring

For each matched pair:

```text
angle_err   = |Δθ|                                      [deg, 0–90]
offset_err  = perpendicular offset at seam              [px, 0–∞]
width_ratio = width_generated / width_known             [ratio, 0–∞]
width_err   = |ln(width_ratio)|                          [nats]
colour_err  = ΔE00(mean Lab of the line core known side, mean Lab of line core generated side)
                [0–100]

SCS_line = exp( −(angle_err/3)² − (offset_err/2)² − (width_err/0.35)² − (colour_err/2)² )   ∈ (0,1]

SCS        = mean over matched lines of SCS_line
             (defined as 1.0 by convention when no known line reaches the seam, but C4 is n/a)
match_rate = matched known lines / known lines reaching the seam
```

Width is estimated from the full-width-at-half-maximum of the gradient profile perpendicular to the line, averaged over five sample positions on each side. Colour is the mean of the central 60% of the line's cross-section, so anti-aliasing does not dominate. For text, `TCS` replaces width with cap-height ratio and colour with the text's mean ink colour:

```text
capheight_err = |cap_height_generated / cap_height_known − 1|        [relative, 0–∞]
TCS_line = exp( −(angle_err/3)² − (offset_err/2)² − (capheight_err/0.20)² − (colour_err/2)² )
```

**Pass/fail — per-line tolerances are the operative rule.** A matched line fails if `angle_err > 3°`, `offset_err > 2 px`, `width_ratio ∉ [0.75, 1.33]`, or `colour_err > 2.0`. A tile **passes C4** if `match_rate ≥ 0.90` and no matched line fails; it **fails C4** if any matched line fails or `match_rate < 0.90`. `SCS` is a continuous ranking score, not a pass rule; it is reported but does not gate. The old `SCS < 0.80` and `SCS < 0.20` thresholds are withdrawn because a line can be within every per-line tolerance and still score low once several small errors combine. C5 uses the same structure with `TCS`, `capheight_err > 0.20` (20%), and `match_rate`. Tiles with no known line/text line are `n/a` and excluded from the denominator; `line_coverage` / `text_coverage` are reported. Per-line errors are reported in the CSV (`angle_err_deg`, `offset_px`, `width_ratio`, `line_dE`) so a failure can be diagnosed without re-running.

**Measurability floors.** SCS requires rule width ≥ 0.75 pt (≥3.1 px at 300 DPI) and TCS requires type size ≥ 6 pt (cap height ≥17 px at 300 DPI). Below those floors the line is not scored and is counted in the coverage denominator as `unmeasurable`; this prevents a 1 px rule or 4 pt type from producing a confident but meaningless continuation score.

### 6.5 What this metric does not capture

- **Soft structure:** gradient fields, blurred horizons and texture flow have no straight segment; they are covered by B3/C6 and A1, not SCS.
- **Curved structure:** circles, arcs and logos at the trim are not matched by a line model. They are covered by edge agreement (B7) and the object detector (B5).
- **Colour gradients along the line:** the mean colour comparison misses a line that changes hue along its length while keeping the mean.
- **Occlusion:** a line that legitimately stops at the trim (e.g., a rule that ends at a panel boundary), or a known line whose ray is legitimately occluded by a foreground object just outside the trim, looks like a missed continuation. STOP/NO_INK edges are excluded. In addition, a known line whose projected ray crosses a detected foreground boundary is moved to `excluded_occluded` and not counted as a missed continuation. **The occluder is detected on the GT image and frozen, never on the model output**; otherwise a model could paint a contrasting edge to convert a miss into an exclusion. The exclusion rate is capped at 10% of known lines and reported (`occlusion_exclusion_rate`); a cap breach makes C4 advisory for that tile, not passing.
- **The estimator itself:** LSD/Hough/OCR have false positives and misses; they are validated on Tier A, where lines and text are known by construction, and C4/C5 are accepted only if synthetic recall ≥0.95 at the stated thresholds. If not, they are advisory.

## 7. Aggregation

### 7.1 Units and weights

| Unit | What it is | Primary use |
|---|---|---|
| Tile | one tile × one orientation | metric computation, cost |
| Edge | all tiles on one page edge | edge-type effects, restraint class |
| Page | all sampled tiles of one page | production decision, routing |
| Family | all pages sharing content/template | confidence intervals, resampling |
| Class | material / hidden-bleed / content class | stratified claims |

Every aggregate names its unit and its denominator. Means over tiles are never presented as page-level claims without the page aggregate; the v1 habit of quoting a tile mean as “the result” is prohibited.

**Production weights (normative).** The production-weighted aggregate uses page-type weights derived from the census mix: quiet 0.500, image-at-trim 0.289, flat/vector 0.145, clipped art 0.050, pattern 0.013, text/stroke 0.003. Within each page type, edges are weighted by their hidden-bleed class in the proportions measured on that tier. The unweighted aggregate is always reported beside it; the difference between the two is itself a result.

**Public test oversampling.** Texture is oversampled 2× in the public test manifest. Aggregate weights undo this; the stratified (unweighted) table is also published because class-specific claims need it.

### 7.2 Tile-level aggregation

For each tile: all metrics (§4), `severe` (oracle-relative, frozen reference oracle), `AF` (absolute fail), `abs_fail_reason` (one of the A6 rules), `scored_mask_hash`, `orientation`, `content_class`, `bleed_class`, `material_class`, `runtime_ms`, `confidence`, `accepted`.

A tile may be `invalid_for_tile` (e.g., placement does not fit a small page); invalid tiles are excluded from denominators and counted in the attrition table.

**Class labels vs class features.** All class-stratified *scoring* (A5, A6, B, C, the class tables) uses `label_content_class`, assigned from the complete page at data creation. `content_class` / `feat_content_class` is the run-time feature computed from the known band within 64 px; it is allowed in gates and diagnostics, but it is not the scoring label. The two are correlated and not identical (a 64 px band can mislead on a mixed page); the harness reports their confusion matrix so a class claim cannot silently depend on which one was used.

### 7.3 Edge-level aggregation

For each edge: the median of fidelity metrics over its tiles (A1, A2, A3, C1–C3), the **worst** (max) of safety flags (severe, AF, B1/B2, trim violation), and the fraction of tiles with AF. Edge class = the edge's hidden-bleed class (NO_INK/STOP/FULL/AMBIGUOUS) and material class. Edges are the unit for B1/B2/B9 and for F.

### 7.4 Page-level aggregation — why “worst tile” is only half the answer

A page is rejected for print if **any** strip on it is visibly wrong; that argues for worst-tile. But worst-tile MAE is dominated by the single hardest texture tile, not by the worst visual defect, and v1 shows the mean/median gap is 3–6×. v2 therefore uses a two-number page score:

```text
page_safety(p)  = 1 if any tile of p has severe=1, AF=1, B1/B2 violation on a STOP edge, trim violation,
                  or C4/C5 failure on a tile where the metric applies; else 0          ← worst tile, by design
page_fidelity(p) = quantile_0.90 of tile MAE over p's tiles     ← robust to one hard tile
page_dE(p)       = quantile_0.90 of tile dE00 over p's tiles
page_corner(p)   = min over corner tiles of corner pass (J1/J3/J4)
```

`page_safety` is the production-relevant page event and is used for the private page-level acceptance set (§3.3) and for reporting, not for the benchmark's Gate A/B (which are tile-level, §7.6). `page_fidelity` is the continuous quantity used for SystemGain and ranking, because a single texture tile should not define a page's average quality. The p90 is chosen over the mean because tile errors are heavy-tailed (v1: median 1.9–4.7 vs mean 11.5–17.4) and over the max because max is not stable across tile placement. **This is a deliberate disagreement with “page score is the worst tile”**: worst-tile is retained for safety and for the page event, but rejected as the page fidelity score because it measures tile difficulty more than model quality. Both numbers are always reported; the routing decision uses page safety and page fidelity together.

For pages with fewer than 5 sampled tiles, `page_fidelity = max(tile MAE)` and the page is flagged `sparse`.

### 7.5 Family- and class-level aggregation

Family scores are the **equal-weighted mean of its page scores**; families are the resampling unit for all intervals. Classes are reported two ways: stratified (each class separately, unweighted within class) and production-weighted (§7.1). No class is allowed to be reported from fewer than 30 pages or 20 families; below that the cell is marked `insufficient` and only the pooled number is shown.

### 7.6 The headline: SystemGain and the routing gate

The benchmark's primary number answers the production question: *if this model is placed behind its own confidence gate, with edge repeat as fallback, how much page error does the benchmark save?* It is defined **once, at page level**, using `page_fidelity` from §7.4:

```text
page_fidelity(m, p) = quantile_0.90 of tile MAE over page p's tiles
accepted(p)         = 1 if every sampled tile t of p has confidence(t) ≥ τ
page_system(p)      = accepted(p) ? page_fidelity(m, p) : page_fidelity(ref, p)
SystemGain          = Σ_p w_p · [page_fidelity(ref,p) − page_system(p)] / Σ_p w_p
coverage            = Σ_p w_p · accepted(p) / Σ_p w_p
```

`w_p` are the production page weights (§7.1). There is no tile-weighted SystemGain variant; the per-tile deltas are reported as diagnostics (A1/A2), not as the headline. `MAE_page` in §0 means exactly `page_fidelity`.

- **Reject-all scores zero, not a win.** A model that cannot certify a gate may submit ungated (`accepted = 1` for all pages); its SystemGain can still be positive, but its page severe rate is then raw.
- **The gate is calibrated by the harness, not chosen by the submitter.** The submitter provides `confidence` per tile computed only from allowed input features. The harness evaluates the submitted gate on a calibration half, selects `τ` (maximum coverage) such that the one-sided 95% upper bound on accepted-tile severe is ≤1.0% (Gate A) or ≤3.35% (Gate B), then **certifies the selected threshold on a disjoint calibration half** (§7.7). If certification fails, the gate is invalid and the entry is scored ungated.
- **Why tile-level severe for the gate.** v1's safety number is a tile rate, and a zero-event 1% bound needs 299 *effective* accepted tiles; because tiles cluster in pages, the required accepted count is `299 × DE_tile` (≈703 at the design effect of 2.35) — feasible on every tier. The private page-level ≤1% claim uses `page_safety` on the 350-page acceptance set and needs `299 × DE_page` accepted pages (≈332 at DE 1.11). The two are not conflated.
- **Cost is shown next to gain.** The leaderboard row is `(SystemGain, coverage, accepted_severe, page_runtime)`, not a weighted sum. A model with a large gain at 2 s/page and a model with half the gain at 20 ms/page are different products; the table shows both and the reader decides.
- **Why not a weighted composite.** Any weights over A–J encode a deployment's tolerance for invention vs colour drift vs cost. Those tolerances differ between a packaging printer and a photo-book printer. The benchmark publishes the vector; SystemGain is the one number that corresponds to a real production decision (route or fallback), so it is the primary sort key. It is never the only output.

**Leaderboard ordering.** (1) Eligibility gates (§13.4). (2) Highest SystemGain at a certified Gate A or Gate B, with a family-bootstrap 95% CI that excludes zero required for a positive claim. (3) Higher coverage. (4) Lower accepted severe. (5) Lower page runtime. Ties are broken by A1/A2 on FULL edges. The full A–J table is displayed for every entry regardless of rank.

### 7.7 Gate calibration and certification protocol

1. The submission declares `confidence` per tile, the feature list (only `feat_*` names, §13.1/B.4), the gate code hash, and the gate type (per-tile; page acceptance = all tiles accepted).
2. On the **calibration split only**, split the calibrations **by family 50/50 into selection and certification halves**. The harness evaluates the submitted confidence (it does not compute features) on the selection half, scans `τ ∈ {0, 0.005, …, 0.995, 1.0}`, and records coverage/severe for each.
3. Gate A: choose max coverage subject to a design-effect-adjusted Clopper-Pearson one-sided 95% upper bound on accepted-tile severe ≤0.01 with `n_eff ≥ 299`, where `n_eff = accepted_tiles / DE_tile`; at the pre-freeze `DE_tile = 2.35` this requires ≥703 accepted tiles. Gate B: same with ≤0.0335 and `n_eff ≥ 89` (≥210 accepted tiles at DE 2.35). If the calibration-estimated `DE_tile` exceeds 2.35, the required accepted count scales with it; the harness records both the raw and effective counts. This design-effect-adjusted CP is an approximation, not a hierarchical model; the cluster bootstrap is reported beside it, and the certificate is labelled `CP-DE`.
4. Recompute the chosen `τ`'s bound on the **certification half**; if the bound does not meet the target there, the gate is invalid. This prevents selecting the best of 201 thresholds and quoting its in-sample bound.
5. Freeze `τ`, gate code hash and feature list in the submission record. Apply unchanged to validation and sealed test.
6. Report the full coverage–severe curve on the test split (not used for selection) so the frontier is visible.
7. A gate that uses any label column, any GT-derived quantity, case id, family id, split, page text, or model output statistics computed on GT is disqualified. The audit is code review plus a feature-provenance test: the harness perturbs GT and checks that confidence is unchanged.

### 7.8 What is not aggregated

No aggregate may combine tiers (A/B/C), native-CMYK and RGB-proxy entries, prompted and unprompted entries, or tile and whole-page modes into one mean. Those are separate tables. The private tier is the only production claim; the public tiers are labelled “public synthetic” and “public real” in every table.

### 7.9 Reporting rule: paired deltas, never a bare mean

Every headline table that compares methods MUST include the `edge_repeat` row and a **paired delta** column:

```text
Δ_m(t) = metric_m(t) − metric_ref(t)          per tile, same page/tile/orientation
Δ̄_m    = weighted mean of Δ_m, with 95% family-cluster bootstrap CI
```

If the CI includes zero, the only permitted statement is “no difference at this sample size”; a point estimate is never reported as a win on its own. The ten axes are reported separately first; `SystemGain` is computed only after that vector exists, and it never replaces it. This rule exists because v1's headlines are unpaired means, and a 0.1 MAE difference between two classical fills is not a ranking.

---

## 8. Tracks

| Track | Name | Required for | Pages / tiles | Axes | Cost (per model, 100 ms/tile class) |
|---|---|---|---|---|---|
| **T0** | Sanity | harness builders | 20 analytic + 400 frozen stratified tiles | A, C, D | minutes |
| **T1** | Standard tile | leaderboard | 160 test pages × 4 orientations × 28 tiles = 17,920 tile-runs at 512; 40 pages at 1024 (20 tiles × 4 orientations) | A, C, D, G, J | 1–17 GPU-h |
| **T2** | Whole page | leaderboard | 200 pages (test + validation) | A, B, C, G, J | 0.1–2 GPU-h |
| **T3** | Restraint / hallucination | leaderboard | all NO_INK/STOP edges of the 160-page test split (≈80 quiet pages + STOP edges on the 80 inked pages) + 200 strips from the §5.4 validation set | B, C6 | 0.2–1 GPU-h |
| **T4** | Robustness | production-router badge | 760 page-variants from the 200-page robustness manifest: 5 trim conditions (δ=+1,+2,+4,−1,−2) × 120 pages + 3 crop-mark offsets (0/9/38) × 40 pages + 40 partial-bleed pages | F | 0.3–2 GPU-h |
| **T5** | Colour | leaderboard | 48 CMYK + 6 spot + 8 rich-black + 16 near-white + 8 Adobe RGB test pages (categories are nested; synthetic supplements for rare colour classes) | E | 0.2–1 GPU-h |
| **T6** | Cost | leaderboard | 100 timed tiles + 20 pages (after 20-tile warm-up) | H | minutes |
| **T7** | Scale | general-purpose badge | 150/300/600 DPI × 40 pages, 60 px × 40 pages, 1024 × 40 pages, long-thin pages × 20 | I | 1–6 GPU-h |
| **T8** | Prompt diagnostic | optional, not ranked | 100 pages, unprompted + GT-caption | A | 0.2–1 GPU-h |
| **T9** | Legacy v1 | regression only | v1 manifest (1,730 dev + 292 sealed, six-method oracle) | A, C | minutes–hours |

**T1 detail:** 160 test pages × 28 tiles × 4 orientations = 17,920 tile-runs at 512. The 1024 subset is 40 pages × 20 tiles × 4 orientations = 3,200 tile-runs. **T2** samples 200 whole pages from the 320 test+validation pages. **T3's 200 hallucination strips are a subset of the 1,200-strip validation set**, not a new set.

**Minimum entry:** T1, T2, T3, T5, T6 + determinism (G1/G2) + D1/D1b. **Production router candidate:** the above + T4, Gate A or B certified, D2 = 0 or D6 pass, and cost under the declared cap (H1 ≤ 100 ms/tile at 512, or a written justification accepted by the maintainers). **General-purpose badge:** the above + T7. T8 is never part of a rank. T9 is not part of the leaderboard; it exists so a harness built from this spec can reproduce v1 within tolerance.

**Lite manifest.** For iteration, a fixed 25% subsample of T1 (4,480 tile-runs, one orientation) and 40 whole pages is published as `lite.json`. Lite results are labelled “lite” and are not valid leaderboard entries; the manifest and its seed are public and frozen.

---

## 9. Baselines and numbers to beat

### 9.1 Required baselines

Every submission's table is shown with the same baseline rows. The classical six plus LaMa are the **frozen reference oracle set**; adding a new method to the oracle would silently re-label every historical `severe`, so the oracle file is versioned and never extended without a protocol major version.

| ID | Baseline | Implementation notes | Reference role |
|---|---|---|---|
| BL0 | `gt_copy` | fills `U` with GT | sanity / upper bound |
| BL1 | `paper_fill` | fills every unknown pixel with the estimated paper colour | restraint sanity |
| BL2 | `edge_repeat` | repeats the nearest known row/column into the strip; v1's `edge_repeat` | **primary reference** |
| BL3 | `stretch` | stretches the last known band into the strip | cheap classical |
| BL4 | `mirror` | reflects the known band across the seam | classical |
| BL5 | `telea` | OpenCV `INPAINT_TELEA`, radius 3 | classical |
| BL6 | `ns` | OpenCV `INPAINT_NS`, radius 3 | classical |
| BL7 | `linear_extrapolation` | per-channel linear fit to the last 8 known rows, extrapolated | classical |
| BL8 | `patchmatch` | PatchMatch inpainting, subset only (cost) | classical, slow |
| BL9 | `lama` | big-LaMa, pinned checkpoint hash | strong classical/CNN reference |
| BL10 | `flux_fill` | FLUX.1 Fill dev, pinned weights hash, fixed sampler, no prompt | primary DiT baseline |
| BL11 | `sd3_mmdit` | SD3-class MMDiT inpainting pipeline: a named SD3.5 checkpoint + declared inpainting adapter/ControlNet derivation, pinned weights hash, no prompt (a constructed pipeline, not an official single artifact; the exact derivation is part of the submission; at freeze the adapter/ControlNet name, source and weights hash are recorded in `expected_baselines.json`, and BL11 is omitted from the numbers to beat if unnamed) | second transformer family |
| BL12 | `mae_vit` | MAE-style ViT-L inpainter trained on Tier A train only | masked-image-modelling baseline |
| BL13 | `sd2_raw` / `sd2_refine` | SD2 inpainting, empty prompt / over edge-repeat prefill, strength 0.6 | v1 legacy comparison |

All learned baselines use the same `meta` (orientation, geometry, profile), the same seed derivation, and batch 1. A baseline that needs a prompt is excluded from the main table and shown in T8 only. The `mae_vit` baseline is deliberately trained on public synthetic only; it is the control for “can a masked-image model compete when it has not seen real print pages”.

**Oracle-set note.** v2's frozen severe oracle is the seven-method reference set (six classical fills + LaMa), because LaMa is a strong, cheap, widely available reference and because a six-method oracle would let a LaMa-class method redefine its own `severe` threshold. v1's published severe rates came from a six-method oracle; therefore v2 severe rates are a **new baseline**, not a continuation. `legacy_v1` mode recomputes the six-method oracle and must reproduce Appendix B.5; any claim that a method “beats v1's severe rate” is valid only in that mode.

### 9.2 Expected numbers on the public synthetic set

These are **expected ranges**, not frozen targets: the generator does not exist yet, and inventing three-significant-figure numbers for it would be false precision. At protocol freeze the reference harness runs each baseline on the frozen **400-tile stratified check set** (≥40 tiles per content class) and writes `expected_baselines.json`; that file becomes the reproduction target with ±30% tolerance and a required Spearman rank correlation ≥0.90 between a new harness's baseline table and the frozen one. The analytic checks in §9.3 are exact and must pass before any range is trusted.

| Baseline | Flat MAE | Gradient MAE | Structure MAE | Texture MAE | Overall MAE (fill pages, census-weighted) | Severe % | Cost/tile (quiet, 512) |
|---|---|---|---|---|---|---|---|
| `gt_copy` | 0 | 0 | 0 | 0 | 0 | 0 | — |
| `paper_fill` | 3–8 | 5–12 | 15–30 | 30–55 | 12–20 | 50–80 | <1 ms |
| `edge_repeat` | 0.0–0.5 | 2–6 | 8–18 | 25–40 | 5–8 | 2–6 | ~0.5 ms |
| `stretch` | 0–1 | 2–5 | 10–20 | 28–45 | 5–8 | 4–10 | ~0.5 ms |
| `mirror` | 1–3 | 4–8 | 12–22 | 30–50 | 7–10 | 8–15 | ~0.5 ms |
| `telea` | 3–6 | 6–10 | 15–28 | 30–50 | 9–14 | 30–45 | ~80 ms |
| `ns` | 2–5 | 5–9 | 14–26 | 30–48 | 9–13 | 15–25 | ~80 ms |
| `linear_extrapolation` | 2–5 | 5–9 | 15–28 | 32–50 | 10–15 | 20–35 | ~9 ms |
| `patchmatch` | 1–4 | 5–10 | 12–26 | 25–45 | 8–13 | 10–20 | ~45 s |
| `lama` | 4–7 | 6–10 | 14–26 | 30–42 | 9–16 | 20–35 | ~75 ms |
| `flux_fill` | 1.5–4 | 2–5 | 8–18 | 15–30 | 6–11 | 8–20 | 800–2,500 ms |
| `sd3_mmdit` | 2–5 | 3–6 | 10–22 | 20–38 | 8–14 | 12–28 | 1,000–3,000 ms |
| `mae_vit` | 2–5 | 6–12 | 18–32 | 30–50 | 12–20 | 20–40 | 20–60 ms |
| `sd2_raw` | 20–40 | 30–50 | 40–70 | 50–90 | 30–55 | 70–90 | ~1,900 ms |
| `sd2_refine` | 4–8 | 6–12 | 12–25 | 25–40 | 8–14 | 15–30 | ~1,300 ms |

The “overall” column is the census-weighted mean over **fill pages only** (quiet/NO_INK pages score 0 for most fills and are reported separately), computed from the four class columns at weights 0.39/0.23/0.33/0.05; it is a consistency check on the table, not an independent measurement. **How to read the table.** Flat MAE is the absolute-drift test (telea and LaMa should be visibly worse than edge repeat); texture is the only class where a strong generative model may beat edge repeat, and even there GT texture is a rendering convention. A baseline row that violates the ordering by more than the tolerance (`gt_copy` not 0; `edge_repeat` not the best **classical** method on flat; `paper_fill` not near 0 on B1) indicates a harness bug, not a discovery.

### 9.3 Analytic harness self-tests (exact)

These are computed from a synthetic primitive's closed form, not from a reference run. They are the checks a new harness must pass before it may score a model.

| Test | Expected |
|---|---|
| Solid page, any fill that copies the solid | MAE = 0, dE = 0, B8 = 0 |
| Solid page, `gt_copy` | all fidelity metrics 0, C4 = n/a (no known line), B1 = 0 |
| Linear vertical gradient of slope `s` levels/px, `edge_repeat` | MAE = `19.5·s` for b=38 (mean distance 1..38), independent of page height |
| Linear horizontal gradient, rotated 90° tile, `edge_repeat` | same MAE as unrotated (rotation equivariance of the baseline) |
| Paper page (NO_INK), `paper_fill` | MAE = 0, B1 = 0, B9 = 1 |
| Paper page (NO_INK), `edge_repeat` on an inked trim in STOP page | MAE = mean ink mass copied into ring; B1 > 0 by construction |
| A 2 px white margin injected outward, `paper_fill` vs `gt_copy` | `gt_copy` unchanged; `paper_fill` MAE rises by the margin's ink deficit |
| Same tile, two identical runs of `edge_repeat` | bit-identical, G1 = true |
| Text line crossing seam at known angle, `gt_copy` | TCS = 1.0 and C5 pass; OCR invented = 0 |
| A line rotated by 4° in the strip, control | C4 fails; matched line angle error = 4° |
| A pasted logo into a GT strip, control | B5 = 1000 − FPR_det (≈1000 for one detection in one tile), B7 > 0, B4 ≥ 1 if logo has text |
| 2×2 red/blue checkerboard, `gt_copy` | A1/A2 = 0, SSIM = 1 even though the image is "unnatural" |

The first nine rows are closed-form or fully specified. The last three (text, 4° line, pasted logo) depend on the OCR/LSD/object detectors; they are **detector smoke tests** with tolerances (±1 detected line/character, ±1 detection), not exact identities, and a harness failure there is investigated before the detector is trusted.

### 9.4 Numbers to beat on real 300 DPI jobs (dev set, private tier)

These are the v1 routing conditions restated as v2 gates. They are evaluated on the private dev set (calibration + validation), with the sealed test read once. The reference is edge repeat.

| # | Condition | v2 operationalisation | Status if failed |
|---|---|---|---|
| R1 | Texture-class MAE lower than LaMa's margin (LaMa 44.29 vs edge_repeat 45.96) with family-bootstrap CI excluding zero | `ΔMAE_texture = MAE_edge_repeat − MAE_model`, 95% family CI > 0 and point estimate > 1.67 | not a texture win; no routing claim on texture |
| R2 | Flat-class severe rate < 5% (LaMa 59%) | `severe_rate_flat` with design-effect-adjusted exact upper bound ≤5%; unit = flat tiles; `n_eff = flat_tiles/DE_tile` | fails flat safety |
| R3 | Overall severe rate ≤ edge repeat's v2 rate (pre-freeze placeholder 3.35%), or a gate achieving it on accepted tiles | Gate B accepted-tile severe ≤ edge-repeat v2 severe rate (95% UB), or ungated rate ≤ it | fails safety; fallback only |
| R4 | Zero known pixels changed pre-clamp, or clamp seam no worse than edge repeat's v2 BGE (placeholder 3.78) | D2 = 0, or D6 ≤ 1.5 and C3 ≤ edge-repeat v2 BGE | fails known-pixel integrity |
| R5 | < 100 ms per 512 px tile on one consumer GPU, measured quiet, or justified | H1 p50 ≤ 100 ms, or written justification accepted by maintainers | not cost-eligible; can still be reported |
| R6 | Captures a good share of the oracle headroom | On tiles where edge repeat loses (`oracle_mae ≤ edge_mae − 1`): `HeadroomGain = Σ (edge_mae − MAE_m)` over those tiles; require `HeadroomGain ≥ 0.5 × Σ (edge_mae − oracle_mae)` with family CI > 0 | no routing value |
| R7 | SystemGain positive with family-bootstrap 95% CI excluding zero | `SystemGain > 0`, CI lower bound > 0, at a certified Gate A or Gate B | no production router candidacy |
| R8 | Restraint non-inferiority | `B9 ≥ 0.98` on NO_INK edges; `B1 = 0` on NO_INK edges (v2.1, DD84: STOP edges are missing bleed and are not restraint tests) | fails restraint; cannot route on mixed jobs |

**Oracle headroom.** v1 measured 2.5–2.9 MAE per tile of headroom over edge repeat. R6 is deliberately demanding: a transformer that recovers less than half of the available headroom on the tiles where the baseline loses is not worth a 100 ms budget, let alone a 2 s one. The headroom calculation uses the **frozen reference oracle**, not a per-submission oracle, so it cannot be inflated by including the submission itself.

**v1-derived targets.** The numbers 3.35%, 59% and 3.78 in R2–R4 are v1 measurements, quoted because they are the decision thresholds the production team already uses. v2's severe rule and geometry differ (seven-method oracle, 48 px band), so at protocol freeze the reference harness recomputes edge repeat's v2 severe rate and BGE on the v2 manifest. R3 then reads “≤ edge repeat's v2 severe rate (pre-freeze placeholder 3.35%)”, and R4 reads “≤ edge repeat's v2 BGE (pre-freeze placeholder 3.78)”. A submission cannot claim R3/R4 against the v1 number without the `legacy_v1` mode.

**R1/R2 provenance.** The R1 figures (LaMa 44.29, edge repeat 45.96, margin 1.67) and the R2 figure (LaMa 59% flat severe) are v1 aggregates and are `provisional-until-freeze`. At freeze they are replaced by, or reconciled against, the frozen private aggregate file, cited by file name and SHA-256 in `expected_baselines.json`; until then R1/R2 results are reported but not used for a pass/fail routing claim.

**What “beats v1” means.** v1's `sd_refine` matched edge repeat at 2,600× cost. Under v2, a transformer must beat R1–R8 simultaneously; a model that only matches MAE but fails R2/R4/R5 is a regression in production terms even if its mean MAE is lower. The 2.5–2.9 MAE headroom is the bar, not the 0.1 MAE difference between two classical fills.

### 9.5 First C0 dev table (v2.1, pilot)

Real-GT FULL and NO_INK edges of the calibration and validation families (73 pages / 14 families with scored edges; 1,962 orientation-0 tiles, four orientations scored). Frozen 7-method oracle (`oracle_c0.json`, SHA in `aggregates/dev_c0.json`), frozen before any trained model existed. Intervals are 95% family-cluster bootstrap and are **few-cluster** (14 families). Runtimes here are fidelity-run timings under load; quiet batch-1 cost is in `aggregates/cost_c0.json`.

| Method | Mean MAE | Median | p90 | Severe | ΔMAE vs edge repeat (95% CI) | Ungated SystemGain (95% CI) |
|---|---|---|---|---|---|---|
| `edge_repeat` | 10.74 | 1.00 | 41.9 | 3.5% (CP-DE UB 5.0%) | — | — |
| `ns` | 11.03 | 1.33 | 43.5 | 6.7% | +0.29 [0.00, 0.41] | −0.01 [−0.38, 0.37] |
| `stretch` | 11.51 | 1.17 | 42.9 | 4.1% | +0.77 [−0.17, 3.52] | −1.96 [−8.84, 0.61] |
| `telea` | 11.70 | 3.36 | 39.8 | 27.5% | +0.97 [0.49, 1.41] | −0.26 [−1.12, 0.11] |
| `lama` | 12.22 | 3.60 | 41.1 | 25.3% | +1.48 [0.51, 1.89] | −2.36 [−3.58, 1.68] |
| `mirror` | 12.62 | 1.69 | 37.0 | 8.8% | +1.88 [−0.08, 7.58] | −3.52 [−18.8, 2.36] |
| `linear_extrapolation` | 13.46 | 2.08 | 45.3 | 23.1% | +2.72 [−1.68, 4.32] | −3.61 [−6.28, 4.12] |
| `lama_ft_c0` (trained, not oracle) | 10.81 | 1.91 | 37.5 | 6.5% | +0.07 [−0.54, 1.69] | +0.21 [−3.48, 2.87] |
| `strip_unet_mix` (trained, not oracle) | 10.74 | 1.00 | 41.9 | 3.5% | 0.00 (output identical to edge repeat) | 0.00 |

**Trained models (P6).** Both were trained only on `train_fit` (bleedgen v0 synthetic + pseudo-GT pages), selected on `train_dev`, and never saw a real-GT family. `strip_unet_mix` (15.1 M-parameter residual over edge repeat) converged to a zero residual: its dev output is bit-identical to edge repeat, so the Tier A / pseudo-only ablations were not run. `lama_ft_c0` (big-LaMa fine-tuned 3,000 steps) is the first method that **ties** edge repeat on real GT: mean ΔMAE +0.07 and SystemGain +0.21, both intervals spanning zero. It removes most of LaMa's flat-colour drift (flat class MAE 0.79, vs 2.45 for LaMa and 0.30 for edge repeat) and wins on structure (24.9 vs 26.1), but its severe rate is still twice edge repeat's (6.5% vs 3.5%), driven by flat and gradient tiles. On pseudo pages it beats edge repeat clearly (7.58 vs 8.79, orientation 0); on real GT the same comparison is 10.55 vs 10.74. The pseudo gain mostly does not transfer. Quiet batch-1 cost: 92 ms/tile p50 vs 16 ms for edge repeat (`cost_c0.json`, `clocks_locked=false`). No gate (A or B) is selectable for either model on `cal_sel`, for the same sample-size reason as LaMa.

**Reading.** On real print jobs edge repeat is not just a strong baseline, it is the best method measured: median ring error 1 level, the lowest severe rate, and no method's paired delta or SystemGain interval lies on the winning side of zero. LaMa reproduces v1's finding — it drifts on flat colour (class MAE 2.45 vs 0.30) — and on C0 it does not win on texture either (58.3 vs 56.4; 14 pages, insufficient). Its raw output rewrites trim pixels on every tile (D2 > 0), which v2.1 reports but does not disqualify (DD83). The v1 numbers this replicates: edge repeat 11.50 mean / 3.35% severe (v1, 6-method oracle) vs 10.74 / 3.5% here (7-method oracle; O14: adding LaMa to the oracle moves severe rates by ≤ 0.9 pp).

**Gates.** No gate for LaMa can be selected on `cal_sel` at either level: at the measured `DE_tile` = 12.9, Gate B (target = edge repeat's own severe rate on the same half, 1.8%) needs ≥ 1,148 accepted orientation-0 tiles; the half does not contain that many scored tiles. Entries are therefore reported ungated. This is the size statement C0 exists to produce: certification needs the Tier C collection.

**Transfer (T10, O15).** On pseudo pages of the same dev families the ten methods (eight frozen plus the two trained models) rank almost identically to real GT (Spearman 0.95; 0.90 for the eight frozen methods alone), but absolute errors differ (edge repeat 8.2 pseudo vs 10.7 real). Pseudo GT is a usable ranking and training signal, not a substitute for real-GT scores, and a pseudo-GT win is not evidence of a real-GT win (`lama_ft_c0` above).

**Synthetic transfer (O13).** Tier A (bleedgen v0, 128 held-out pages, orientation 0) vs C0 dev ranks nine methods with Spearman 0.64. That is below the 0.8 target, but with nine methods it is low power. Tier A errors are about half of real ones (edge repeat 4.38 vs 10.74), and Tier A penalises LaMa much harder (8.40) than real jobs do. bleedgen v0 is not yet a faithful proxy for ranking.

---

## 10. Statistical reporting

### 10.1 Units, clustering and bootstrap

The **family** is the independent unit. Pages within a family share template, brand, photographer and often the same background artwork; tiles within a page share content. Treating 17,920 tiles as independent would understate every interval by roughly `sqrt(design effect)`. All intervals use a **family-cluster bootstrap**:

```text
for b in 1..B (B = 1000):
    resample families with replacement, stratified by split and page type
    include all tiles/pages of each sampled family
    compute the statistic (mean, median, delta, severe rate, SystemGain)
    store
CI = 2.5th and 97.5th percentiles; B = 1000; seed = hash(protocol_version, statistic, split)
```

- Paired deltas resample **the same families** for both methods (paired bootstrap), not independent resamples.
- The bootstrap is stratified by split and page type so the production weights are preserved in every resample.
- Clustering is reported at two levels: `ICC_page` (between pages in a family) and `ICC_tile` (between tiles in a page). Their design effects are `DE_page = 1 + (m_page−1)·ICC_page` and `DE_tile = 1 + (m_tile−1)·ICC_tile`, where `m` is the average number of units per cluster. `n_eff = n / DE` at the relevant level; `n_eff`, not the raw count, is quoted next to every interval and used in every gate bound. The pre-freeze planning values are `ICC_page = 0.05, m_page = 3.25 → DE_page = 1.11` and `ICC_tile = 0.05, m_tile = 28 → DE_tile = 2.35`; both are re-estimated from calibration data and reported.
- Percentile CIs are used; BCa is reported as a sensitivity check when the bootstrap distribution is skewed (severe rates, tail metrics). With fewer than 30 clusters, percentile CIs are labelled `few-cluster` and a t-percentile/BCa interval is used instead.
- For a zero-event rate the exact Clopper-Pearson bound is computed on `n_eff`, not on the raw count: `UB = 1 − 0.05^(1/n_eff)`. A percentile bootstrap of a zero-event rate is degenerate (every resample has zero events, so its upper bound is zero) and is never used as the gate bound. The design-effect-adjusted CP bound is the gate bound; it is an approximation, not a hierarchical model, and every certificate carrying it is labelled `CP-DE`. The cluster bootstrap is reported beside it as a sensitivity check (aggregate JSON field `accepted_severe_ub95_bootstrap`).

### 10.2 Exact one-sided bounds and sample sizes

Zero-event 95% upper bound: `1 − 0.05^(1/n_eff)`, where `n_eff = n / DE` at the relevant clustering level.

| Raw accepted units `n` | Effective `n_eff` | 0-event 95% UB | What it certifies |
|---|---|---|---|
| 11 | 11 (no correction) | 23.8% | v1 sealed test: nothing about 1% |
| 48 | 48 | 6.05% | v1 confidence result: nothing about 1% |
| 80 | 80 | 3.68% | cannot certify 3.35% |
| 89 | 89 | 3.31% | Gate B at DE=1 (the 88-tile minimum is 3.35%) |
| 160 | 160 | 1.85% | public test page-level CI is still wide |
| 292 | 292 | 1.02% | just misses 1% |
| 299 | 299 | 1.00% | **minimum effective size for a zero-event 1% claim** |
| 320 | 320 | 0.93% | only if effectively independent |
| 703 | 299 | 1.00% | Gate A at `DE_tile = 2.35` |
| 210 | 89 | 3.31% | Gate B at `DE_tile = 2.35` |
| 332 | 299 | 1.00% | page-level 1% at `DE_page = 1.11` |
| 350 | 315 | 0.95% | private acceptance set at DE 1.11 |
| 1,000 | 1,000 | 0.30% | comfortable only if independent |
| 1,300 | 1,171 (5% attrition, DE 1.11) | 0.26% | private annual set (rate bound is a separate calculation) |

Proportion CI half-widths (95%, normal approximation, for planning only): 3.35% at n=160 → ±2.8 pp; n=640 → ±1.39 pp; n=1,244 → ±1.0 pp; n=1,300 → ±0.98 pp (at DE=1). With `DE_page = 1.11`, the 1,300-page annual set gives **±1.03 pp** (no attrition) to **±1.06 pp** (5% attrition), and the 350-page acceptance set gives **±1.99 pp**; a strict ±1.0 pp claim needs 1,244 analysable pages at DE=1 (≈1,381 at DE 1.11, ≈1,804 at DE 1.45). The benchmark reports the computed interval, never the nominal target.

Two-proportion sample sizes (80% power, two-sided 5%): 1% vs 2% → **2,319 per group**; 2% vs 3% → **3,826**; 3.35% vs 4.35% → **5,810**. These are page-level and clustered; they are the reason the benchmark does **not** claim to detect 1 pp severe-rate differences on 160–640 page public sets.

### 10.3 Why 1,300 pages and 400 families

- The private severe-rate target is edge repeat's 3.35%. At `DE_page = 1` that is 1,244 analysable pages; with 5% attrition the planning target is 1,310. The annual set is **1,300 pages**, which supports **±1.03–1.06 pp at DE 1.11** and **±1.21 pp at DE 1.45** — not ±1.0 pp in the worst case. The report quotes the achieved interval; O5 tracks whether the ICC is low enough to tighten it.
- A zero-event 1% accepted-page claim needs 299 **effective** accepted pages, i.e. 332 raw accepted pages at `DE_page = 1.11`. The **350-page acceptance set** leaves 18 pages of gate-rejection headroom (350 accepted = 0.95% bound at DE 1.11) and is therefore the correct size; a 300-page set cannot certify 1% at DE 1.11 (300/1.11 = 270 effective → 1.10%) and is retained only as an ungated regression set.
- Family clustering: at 3–4 pages/family, 1,300 pages is ~350–400 families. If `ICC_page = 0.05` and `m_page ≈ 3.25`, `DE_page = 1.11`; at ICC 0.2 it is 1.45. The 400-family target provides margin for the unknown ICC. Families, not pages, are the bootstrap unit.
- **Families for a 1% severe bound.** The bound is on accepted pages/tiles, not families: zero events in 299 effective units is the minimum. At ~3.25 pages/family, 299 effective pages is ~92 families before clustering; with a conservative ICC allowance the private target is 400 families.
- Public synthetic: 640 eval pages / 64 families is enough for model development and rank correlation, not for a 1% claim. Public real: 300 / 100 is enough for cross-domain generalisation and a ±2.0 pp severe CI at a 3.35% rate (±5.7 pp worst case at p=0.5), not for production.
- **Gate certification sample sizes.** At `DE_tile = 2.35`, Gate A needs ≥703 accepted tiles (299 effective) and Gate B ≥210 (89 effective). These are the numbers the harness uses, not the raw 299/89.

### 10.4 Minimum sample size per claim

| Claim | Unit | Minimum | Basis |
|---|---|---|---|
| Mean MAE within a class, ±0.5 | tiles | ~8,100 (σ=15) to ~14,400 (σ=20) clustered | `(1.96σ/0.5)² × 2.35` |
| Class ΔMAE = 2.5, 80% power | tiles | ~500 unclustered; ~1,180 clustered | `7.85σ²/δ²`; σ≈20 |
| Texture ΔMAE = 1.7, 80% power | texture tiles | ~610 unclustered; ~1,440 clustered; ≥55 texture pages (≈1,540 tiles) | σ_texture is **measured at calibration** (planning value 15–20); the required n is recomputed from the measured σ and reported; R1 uses the 1,300-page annual set (65 texture pages) |
| Severe rate ±1 pp | pages | 1,244 at DE=1; 1,381 at DE 1.11; 1,804 at DE 1.45 | binomial × design effect |
| Zero-event 1% | effective accepted pages or tiles | 299 effective; 332 raw pages at DE 1.11; 703 raw tiles at DE 2.35 | Clopper-Pearson on `n_eff` |
| Zero-event 3.35% | effective accepted tiles | 89 effective; 210 raw at DE 2.35 | Clopper-Pearson on `n_eff` |
| Corner MAE ratio ±10% | corner tiles | 400 | paired within page |
| Cost p50 ±10% | timed tiles | 100 timed (after warm-up) | timing variance |
| Human preference 65/35 ±5 pp | pairwise judgments | 300 independent; ≈450 if clustered by page/rater | binomial at p=0.65, DE 1.5 |
| Human-vs-metric rank ρ≥0.8 | methods | 8–12 methods, 300 pairs | rank correlation power |

A table cell that does not meet its minimum is marked `insufficient`; it is not silently averaged into a headline. The private tier is the only one that can carry R1–R8 at the stated precision. `R1` is evaluated on the full 1,300-page annual set (not the 975-page dev subset), where 65 texture pages × ~28 tiles ≈ 1,820 texture tiles exceed the 1,440 clustered requirement.

### 10.5 Multiple comparisons and pre-registration

The four primary comparative endpoints are pre-registered: SystemGain, texture-class ΔMAE, flat-class severe rate, accepted-tile severe rate. Comparative endpoints are tested with Holm–Bonferroni at family-wise α = 0.05; unadjusted p-values and CIs are shown beside adjusted decisions. **Gate certification is a decision rule, not one of the four hypothesis tests**: Gate A/B use one-sided 95% CP bounds and are reported separately; they are not Holm-adjusted, because a gate either certifies at its stated confidence or does not. Secondary endpoints (all class-level metrics, B/C/E/F/I) are reported with 95% CIs and labelled exploratory; a claim that a method is better on a secondary metric requires either a pre-registered replication on the sealed test or a Holm correction across the secondary family. The sealed test is opened once; any analysis not pre-registered before that opening is labelled exploratory.

### 10.6 Missing data and attrition

Every split reports: pages in, pages valid, edges excluded with reasons, tiles invalid, and the fraction of the ring actually scored. A method that fails to produce output on a tile gets `scored = false`, is counted in attrition, and is **not** silently given the reference fill unless its declared fallback is “edge repeat”; the fallback rate is reported. Attrition above 5% for any class invalidates that class's claim. v1's lesson is that attrition is a result, not housekeeping: 27% of “bleed” pages were not full-bleed and were invisible in the headline.

---

## 11. Reproducibility

### 11.1 Seed derivation

Every random choice is derived from the case id and a protocol salt; no time-based seeds, no `random()` without an argument, no per-run environment entropy.

```text
h = SHA256(protocol_version || case_id || track || tile_id || orientation || purpose)
seed = uint32(h[0:4])                       # harness placement, perturbations
model_seed = declared by the submission     # must be derived the same way or fixed
```

The harness's `seed` column records what was used. A submission that needs a different model seed per tile must declare the derivation; a submission that uses a fixed seed for all tiles declares that. Either is acceptable; changing it between tracks is not.

### 11.2 Model and harness pinning

A submission records: model name and version; weights SHA-256 (all files); code commit / container digest; inference framework and version; CUDA, cuDNN, driver; attention backend; quantization; sampler, steps, guidance, scheduler; tokenizer/CLIP if any (unprompted uses the null prompt); input resolution and any internal tiling; colour conversion library and ICC hashes. The harness records: `bleedbench` commit and container digest; renderer name/version; TIFF/PNG encoder; Python/NumPy/OpenCV/scikit-image versions; font list; calibration files and their hashes.

### 11.3 Quiet timing protocol

The cost track is only valid if measured quiet:

1. Dedicated GPU of the declared model (consumer: RTX 4090 24 GB or declared equivalent; datacenter entries declare GPU and are listed separately).
2. No other job on the GPU; `nvidia-smi` utilisation <2% before starting; no display attached to the GPU if possible.
3. Application clocks locked (`nvidia-smi -lgc`); power limit declared; temperature recorded; if clocks throttle, the run is invalid.
4. 20 warm-up tiles discarded; then ≥100 tiles, batch size 1; 3 repetitions; median of the per-run medians; p50/p90/p99 reported.
5. `gpu_ms` excludes disk I/O and colour conversion; `e2e_ms` includes input conversion, model, output conversion and clamp. Both are reported; H1/H2 use `e2e_ms`.
6. Record GPU model, VRAM, driver, CUDA, power limit, clocks, ambient/temperature, host CPU/RAM, and whether MIG/virtualisation was used.
7. A second, independent quiet run on a different day is required for a leaderboard entry; the larger p50 is used if they differ by >10%.

v1's timings were taken under load from 12 tiles; they are useful as historical context and are not eligible for H comparisons.

### 11.4 Determinism rerun

Every submission runs a determinism check as part of evaluation:

- Same seed, 10% of test tiles, twice, in separate processes: outputs must be bit-identical (G1) for a deterministic entry.
- Five seeds on a 100-tile subset: G2 metric spread.
- Batch sizes 1/4/8 and a shuffled order on 100 tiles: G4.
- If any of G1/G4 fails, the entry is marked `nondeterministic`; its metrics are reported as the mean over 5 seeds and it is ineligible for the production-candidate badge.

Portability is not required by this spec (a model may be deterministic only on the declared backend), but the declaration must say so.

### 11.5 Reproducible harness and reference implementation

The benchmark ships:

- a container image with pinned renderer, metrics, baselines and self-tests;
- `bleedbench verify`, which runs the §9.3 analytic tests, the §9.2 frozen baseline check set and the schema validator;
- the frozen manifests (`splits.json`, `test_manifest.json`, `synthetic_manifest.json`, `lite.json`, `robustness_manifest.json`, `oracle.json`, `expected_baselines.json`) with SHA-256s;
- a `reproduce.sh` that regenerates the baseline table from the public synthetic set.

A submission is reproducible if a third party can re-run `evaluate` with the submitted container and get the same per-tile CSV within the determinism rules. The submission artifact must include code, config, environment lock, weights hash (weights themselves may be downloaded from a pinned URL with hash verification), and the gate code. No pickled objects from untrusted sources; no network access during inference.

---

## 12. Human study

### 12.1 Purpose

Validate that the automatic metrics rank strips the way a prepress operator would reject them, validate the **direction** of the absolute failure thresholds (A6, B1) on a small set, and produce the human labels that validate the hallucination detectors. The numbers themselves are set by the press study (O6). This is a **small, cheap, repeated** study, not a one-off beauty contest.

### 12.2 Design

- **Stimuli:** **60** page-level strip crops (whole ring segment, 6 in wide) selected from the private calibration set: 20 obvious passes, 20 obvious failures, 20 near the decision boundary, spread across the four content classes. Each rendered as a print-size PNG on a colour-managed display, seam marked with a thin neutral guide that can be toggled off, 64 px of known context above/below.
- **Per-strip judgment:** each rater marks every strip **accept / reject / unsure** for print (assuming the rest of the page is correct). This is the response variable for threshold calibration; pairwise preference alone cannot provide it.
- **Pairs:** 300 pairwise comparisons per rater, all three raters see the **same** 300 pairs (needed for rater-effect estimation). Pairs are sampled **independently of the automatic metric difference** (random method pairs per page, then balanced across pages), so the study is not biased toward pairs the metrics already separate. Pairs are randomized, balanced for left/right position, and blind to method.
- **Raters:** 3 prepress operators (not the benchmark authors), each with ≥2 years of print production experience. Training: 10 practice pairs plus 5 practice strips with feedback on the task definition.
- **Task:** accept/reject/unsure per strip; choose the better strip in each pair; optionally label the dominant defect (step, colour drift, wrong structure, invented object/text, noise, paper/restraint, other).
- **Display:** calibrated display at 120 cd/m², D65 white point, neutral grey surround, no sharpening; **print-size view is `zoom = display_PPI / 300`** (≈33% at 100 PPI), not “100% zoom”, plus a 2–4× loupe view for 1 px seams. CMYK pages are soft-proofed through the page ICC. A printed proof of 10 pairs under D50 is used to sanity-check the display; if the proof and display rankings disagree on >1 pair, recalibrate. The study acknowledges that sub-0.1 mm defects are judged at loupe scale, not at print size.
- **Duration:** 60 strips × 10 s + 300 pairs × 15 s ≈ 85 min per rater, plus 15 min training; about **1 h 40 min per rater, ≈5 rater-hours total**, split into two sessions. Cost is a few hundred dollars/euros at prepress rates.

### 12.3 Sample size and analysis

- 300 pairs give a 95% CI of about ±5.4 pp on a 65% preference under independence; pages appear in many pairs, so the effective interval is wider. Report a page-clustered bootstrap interval (planning DE ≈1.5 → ≈±6.6 pp) and treat the study as ranking evidence, not a precise effect estimate. Three raters allow a Bradley–Terry model with rater effects. Inter-rater agreement target: Krippendorff's α ≥ 0.60 (ordinal) or ≥ 0.70 (binary accept/reject); below 0.60 the task definition is revised before the numbers are used.
- Fit Bradley–Terry scores per method; compare their ranking with SystemGain and with each axis metric using Spearman ρ. Pre-registered success: ρ ≥ 0.80 between human preference and SystemGain across methods, and AUC ≥ 0.75 for the binary defect-category detectors.
- **Threshold calibration is global and directional, not per class.** The human “reject” boundary is estimated by logistic regression of the accept/reject label on A1/A2/B1 across all 60 strips; the threshold is set where predicted reject probability crosses 0.5. With 60 strips this cannot calibrate class-conditional thresholds or resolve one print-tolerance step; those are set by the press study (O6), and the human study validates their direction. Any automatic threshold changed on the basis of 60 strips is labelled provisional.
- Validation of hallucination detectors (§5.4) uses the same rater pool but the separate 1,200-strip set; it is a different task (binary invention judgment) and is powered separately.

### 12.4 What the study cannot do

It cannot validate spot-colour or substrate-specific appearance without press proofs; it cannot cover every content class at 60 strips (20 per pass/fail/boundary, spread thin across classes); and it is not a legal acceptance test. It validates ranking and the direction of thresholds, not the underlying colour science. The press-proof study for flat drift and rich black is open question O6, and it — not this study — sets the final A6/B1 numeric values.

---

## 13. Leaderboard and submission format

### 13.1 Per-tile CSV schema

One row per `(submission, split, page, tile, orientation, track)`. The v1 columns are **kept unchanged** for comparability; new columns are additive. The full header is normative; a missing required column fails validation.

```csv
submission_id,protocol,track,mode,split,case_id,family_id,page_id,edge_id,corner_id,tile_id,edge,orientation,
seed,dpi,bleed_px,apron_px,band_px,tile_px,canvas_w,canvas_h,position_x,position_y,trim_error_px,cropmark_offset_px,
model_version,weights_sha256,color_space,profile_sha256,native_space,latent_stride,mask_policy,
method,mae,mse,psnr,delta_e,ssim,boundary_gradient_error,delta_e_page,seam_step,seam_dE,clamp_seam_dE,
preclamp_changed,preclamp_changed_frac,preclamp_changed_max,regen_trim_px,
regen_trim_px_left,regen_trim_px_top,regen_trim_px_right,regen_trim_px_bottom,
halluc_ppm,unsupported_edge_ratio,ocr_invented,object_hits,judge_fake,invented_area,
stop_false_ink,stop_blob_px,stop_accept,solid_drift,flat_drift_L,flat_drift_a,flat_drift_b,
flat_drift_C,flat_drift_M,flat_drift_Y,flat_drift_K,rich_black_dK,rich_black_dTAC,rich_black_dE,
near_white_leak,cmyk_roundtrip_dE,roundtrip_floor,gamut_handling,spot_tint_err,
line_cont_score,line_match_rate,line_coverage,text_cont_score,text_coverage,occlusion_exclusion_rate,
angle_err_deg,offset_px,width_ratio,line_dE,
tile_seam_disagree,ring_gap,corner_arm_disagree,corner_miter_dE,corner_pass,
runtime_ms,gpu_ms,e2e_ms,peak_vram_mb,confidence,accepted,severe,abs_fail,abs_fail_reason,
final_trim_identity,paper_confidence,paper_source_code,
oracle_method,oracle_mae,oracle_win,regret,system_mae,page_mae,content_class,class_weight,
feat_grad_mean,feat_color_var,feat_edge_density,feat_near_white,feat_mirror_disagree,
feat_paper_score,feat_local_entropy,feat_mask_edge_dist,
label_gt_near_white,label_bleed_class,label_depth_px,label_material,label_content_class,
label_severe,label_abs_fail,label_paper_rgb,label_ring_hash,
grad_mean,color_var,edge_density,near_white,gt_near_white
```

The last five columns are **v1 compatibility aliases**: `grad_mean`, `color_var`, `edge_density`, `near_white` are exact copies of `feat_grad_mean`, `feat_color_var`, `feat_edge_density`, `feat_near_white`; `gt_near_white` is an exact copy of `label_gt_near_white`. They exist so v1 tooling and reports keep working. The authoritative side of each is the namespaced column; a gate that reads `gt_near_white` is disqualified for the same reason as one that reads `label_gt_near_white`. `content_class` is also a v1 name and is a feature (known-band only), aliased to `feat_content_class`.

| Group | Columns | Side |
|---|---|---|
| Identity / geometry | `submission_id … mask_policy` | meta |
| v1 metric names | `mae, delta_e, ssim, boundary_gradient_error, runtime_ms, preclamp_changed` | metric |
| New metrics | `mse … corner_pass` | metric |
| Outcome | `confidence, accepted, severe, abs_fail, abs_fail_reason, oracle_method, oracle_mae, regret, system_mae, page_mae` | evaluation |
| Features | all `feat_*`; legacy aliases `grad_mean, color_var, edge_density, near_white, content_class` | **input-only**, allowed in gates |
| Labels | all `label_*`; legacy `gt_near_white` | **GT-derived**, forbidden in gates |

**Feature/label separation is enforced by name and by schema.** A gate that references a `label_*` column, or a legacy label alias, is disqualified. `content_class` is a feature (computed from the known band only) and is aliased to `feat_content_class`; that ambiguity in v1 is why v2 makes the namespace explicit.

**Derived outcome columns.** `page_mae` is `page_fidelity` for the page (§7.4: q90 of the page's tile MAE). `system_mae` is the MAE used in SystemGain for that page: `page_mae` if the page is accepted, else the edge-repeat page value. `system_mae` is therefore identical to `page_mae` on rejected pages and is the field that makes the headline auditable from the CSV alone.

### 13.2 Aggregate JSON

```json
{
  "protocol": "bleedbench-v2.0",
  "spec_sha256": "...",
  "submission": {
    "id": "...", "model_version": "...", "weights_sha256": "...",
    "container_digest": "...", "stochastic": false, "native_space": "srgb",
    "trained_on": ["tier_a_train"], "declared_hardware": "RTX 4090 24GB",
    "gate": {"type": "per_tile", "features": ["feat_mirror_disagree", "feat_near_white"],
             "code_sha256": "..."}
  },
  "scores": {
    "system_gain": 1.42, "system_gain_ci95": [0.61, 2.18],
    "coverage": 0.37, "accepted_severe": 0.006, "accepted_severe_ub95": 0.0097,
    "certificate": "CP-DE", "accepted_severe_ub95_bootstrap": 0.0102,
    "gate": "A", "gate_threshold_frozen_by_harness": 0.665,
    "page_runtime_s": 2.63, "tile_runtime_p50_ms": 94
  },
  "axes": {"A": {...}, "B": {...}, "C": {...}, "D": {...}, "E": {...},
           "F": {...}, "G": {...}, "H": {...}, "I": {...}, "J": {...}},
  "classes": {"flat": {...}, "gradient": {...}, "structure": {...}, "texture": {...},
              "bleed": {"NO_INK": {...}, "STOP": {...}, "FULL": {...}}},
  "pages": {"n": 160, "families": 16, "safety_event_rate": 0.019, "fidelity_p90": 6.2},
  "checks": {"trim_identity": true, "same_seed": true, "required_tracks": true,
             "feature_label_audit": true, "canary": "clean"},
  "environment": {"gpu": "...", "driver": "...", "cuda": "...", "torch": "..."},
  "files": {"tiles_csv_sha256": "...", "manifest_sha256": "..."}
}
```

Every aggregate carries `n`, `families`, `ci95`, and `estimator`. The JSON is validated against a schema; free-text fields are limited to a model card.

### 13.3 Submission package

```text
submission/
  model_card.json          # architecture, training data, limitations, licence
  environment.lock         # exact versions and container digest
  weights.sha256           # hashes; weights fetched from a pinned URL or included
  code/                    # inference entry point, determinism flags
  gate.py                  # run-time confidence gate; feature list in model_card
  track_config.json        # which tracks, tile sizes, batch, seeds, passes_per_page (1 or 4; 4 => C8 n/a)
  REPRODUCE.md             # one-command reproduction
```

The harness runs the code in a network-disabled container with the GT store unmounted; the submission sees only `tile`, `unknown`, `meta`. Predictions are not accepted as files for the leaderboard (only for the private tier's offline mode, where the harness records the input hash and verifies it).

### 13.4 Disqualification checks (every submission)

| # | Check | Rule |
|---|---|---|
| DQ1 | Trim identity | **raw pre-clamp** output has no trim pixel changed, and final output trim is bit-identical; any violation → DQ |
| DQ2 | Shape/range | output shape, channel count, dtype, value range, no NaN/Inf → otherwise DQ |
| DQ3 | Colour space | declared page/model space and ICC hash respected → mismatch DQ |
| DQ4 | Same-seed determinism | G1 true for deterministic entries → otherwise DQ (stochastic entries go to the stochastic table) |
| DQ5 | Required tracks | T1, T2, T3, T5, T6 + determinism + D1/D1b present → otherwise not ranked |
| DQ6 | Split integrity | no family appears in more than one split; declared training data does not include sealed test; near-duplicate check |
| DQ7 | Gate provenance | gate uses only `feat_*`; GT perturbation leaves confidence unchanged; no case/family/split/page text; code audit |
| DQ8 | Weights/config | weights hash matches, config matches the run, no per-track model swapping without declaration |
| DQ9 | Sandbox | no network, no GT/label read, no writes outside the output dir; violations DQ |
| DQ10 | Runtime cap | a tile exceeding 10 min or a page exceeding 10 min is DQ (cost is reported, not gamed by timeout) |
| DQ11 | Prompt/caption | main track uses no caption, OCR of the page, or page text; detector run on `meta` and inputs |
| DQ12 | Mask integrity | no writes outside `unknown`; harness clamps and records, but a raw write is DQ |
| DQ13 | Canary | canary reproduction indicates test-set training → audit, not automatic DQ |
| DQ14 | Legacy claim | any “beats v1” claim must be on `legacy_v1` mode with the v1 manifest; otherwise not comparable |

**Trim identity is the one gate that cannot be traded.** A model that changes trim pixels is not a worse model; it is an invalid production component. The benchmark reports it as DQ, not as a low score.

---

## 14. Open questions

Each question has the experiment that would settle it, and what would change in v2.1.

**Status after C0 (v2.1).** O1 partially settled (P(FULL | image edge) 26%, CI 9–73%, 17 families — direction clear, precision not); O4 measured (99.3% of pages unrotated; 24% landscape); O5 measured (`ICC_tile` 0.46 → `DE_tile` 12.9 on orientation-0 tiles; `ICC_page` and `DE_page` in `aggregates/dev_c0.json`) — the v2.0 planning values were optimistic; O13 measured (Tier A vs C0 dev Spearman 0.64 over nine methods, below the 0.8 target, low power) and O14 measured (oracle change ≤ 0.9 pp). New: O15–O17.

**O1 — What is the joint distribution of material and hidden-bleed class?** The census gives marginals (58% image, 29% flat, etc.) but not the joint; the synthetic generator assumes 50/50 hidden bleed on image edges (`ASM-A1`). *Experiment:* raster+vector audit of 1,000 real pages, classifying every inked edge by material × depth. *Changes:* generator joint, production weights, and the R1/R2 sampling plan.

**O2 — Does the 10 px apron help or hurt model quality?** The apron is added for latent alignment; it asks the model for 48 px instead of 38. *Experiment:* A/B FLUX Fill and an MAE/ViT baseline at `B=38` (unaligned) vs `B=48` (aligned), same tiles, same prompts, measuring A1/A2/C2/D6. *Changes:* if aligned-38 is not worse, v2.1 may drop the apron and keep 16-aligned tiles.

**O3 — Can any no-GT hallucination detector reach the gating precision bar?** §5.4 sets the bar; the answer may be no. *Experiment:* the 1,200-strip human-labelled set, leave-one-generator-out judge validation, prevalence-adjusted `PPV(0.05)` with a CP lower bound, sensitivity/specificity. *Changes:* if none passes, hallucination remains advisory and the human study becomes the only authority; R3/R6 are unchanged.

**O4 — Is canonicalisation enough?** Production can rotate an edge to the top; if so, orientation robustness matters less than whole-page consistency. *Experiment:* measure the distribution of actual edge orientations in the private corpus and the orientation gap (G3) on the same content. *Changes:* if canonicalisation is universal, four-orientation evaluation can be reduced to two for cost.

**O5 — What are the family and page ICCs?** The 1,300-page target supports ±1.03–1.06 pp only if `DE_page ≤ 1.11` (`ICC_page ≤ 0.05` at 3.25 pages/family); a strict ±1.0 pp needs `ICC_page ≤ 0.02`. *Experiment:* estimate `ICC_page` and `ICC_tile` from v1's 80 pages and from the first private v2 run; refit both design effects. *Changes:* if ICC is higher, increase the private set or report the wider interval the data supports.

**O6 — What flat drift is visible on press?** A6's 1.5-level flat threshold is a display-space estimate. *Experiment:* print a 0/1/2/3/4-level step ladder on coated and uncoated stock under D50, judge with 10 prepress operators. *Changes:* A6, B8 and R2 thresholds.

**O7 — Does a caption help?** Prompted models may do better with a content description that production does not have. *Experiment:* T8 caption-oracle upper bound vs unprompted, on 100 pages, scored A–C. *Changes:* none to the main track; it quantifies the cost of being caption-free.

**O8 — Is a CMYK-native model better than an RGB proxy?** The round-trip floor may dominate. *Experiment:* score a native-CMYK model and the same model via RGB proxy on the same CMYK pages; compare E1/E5 net of floor. *Changes:* colour-track default, and whether native entries get a separate leaderboard.

**O9 — Should corners be generated jointly or independently?** J2 only exists for independent tiles; whole-page methods may be better. *Experiment:* same model in tile mode vs whole-page mode on the 4-corner subset. *Changes:* whether T1 corners are scored separately or T2 becomes the only corner claim.

**O10 — What is the right tile overlap for C7?** v1 did not measure it; v2 uses a fixed 25% jitter, which may leave gaps. *Experiment:* sweep overlap 0/16/32/64 px on 100 pages, measure C7 and coverage. *Changes:* tile placement, C7 denominator.

**O11 — Is 8-bit enough, or does 16-bit change colour conclusions?** CMYK round-trip dE below 1 may require 16-bit. *Experiment:* run the colour track at 8 and 16 bit; measure E2 floor. *Changes:* required bit depth for E.

**O12 — How should spot-colour tint ramps be extended?** A spot recipe is a solid ink at a tint; extrapolating a tint ramp across the trim is not the same as extending a CMYK image. *Experiment:* 100 spot pages with known ramps, compare nearest-tint vs continuous-tint scoring. *Changes:* E7 definition, spot pages in the colour track.

**O13 — Does the benchmark's synthetic generator transfer to real jobs?** The public set may reward texture synthesis rather than print continuation. *Experiment:* rank correlation of methods between Tier A test and Tier C dev; target ρ ≥0.8. *Changes:* generator mix, or a transfer correction in the public leaderboard.

**O15 — How large is the pseudo→real transfer gap? (v2.1)** Track P scores a page's own margin. *Experiment:* the same frozen methods on pseudo pages and real-GT pages of the same dev families (T10); rank agreement and per-method gap. *Changes:* whether pseudo-trained models need real-GT fine-tuning before routing.

**O16 — How different is the deployment population from the real-GT population? (v2.1)** Real-GT pages are designer exports that already have a BleedBox; the pages that need generated bleed mostly do not. *Experiment:* compare class, material and size distributions of the two C0 censuses; importance-weight dev results by deployment covariates. *Changes:* production weights (DD78) and Tier C sampling.

**O17 — Is the half-pixel column beyond a 37.5 px BleedBox ever artwork? (v2.1)** *Experiment:* count edges where the 38th column carries ink unlike column 37. *Changes:* whether V12 rounds down or the renderer supersamples that column.

**O14 — How large is the severe-rule oracle bias?** The severe rule depends on the frozen seven-method oracle; a strong new method may make historical methods look worse. *Experiment:* recompute v1 severe rates under several plausible oracle sets. *Changes:* whether severe stays relative or becomes absolute-only.

---

## Appendix A — decision log

Every design decision, with its one-line reason. Metric IDs are in §4; `DD` numbers are design decisions.

| # | Decision | One-line reason |
|---|---|---|
| DD1 | Whole-page ring is a required track | Tiles cannot reveal ring quilting, corner joins or cross-edge agreement. |
| DD2 | Unknown band is `B = b + a`, `a = (−b) mod 16` | Puts the seam on a multiple of 16 so no latent cell straddles the trim line. |
| DD3 | Apron is generated but unscored | It is the price of latent exactness and must not reward or punish content outside production's 38 px. |
| DD4 | Whole-page right/bottom margins absorb `(−W) mod 16` so the **canvas** is 16-aligned; the right/bottom **seam** remains off-grid and is measured by D5/D6 | A seam cannot be moved by margin padding; claiming otherwise makes D5 false-fail compliant models. |
| DD5 | Official mask is pixel-resolution | Lets any model be evaluated without adopting a particular latent convention. |
| DD6 | Effective latent mask and `regen_trim_px` are audited | Makes the latent quantisation cost visible instead of hiding it behind the clamp. |
| DD7 | Hard clamp after inference, plus clamp-seam metric | The trim is immutable, but clamping creates a seam that must be scored. |
| DD8 | Four orientations for every standard tile | Rotation sensitivity is otherwise unmeasured and whole-page inference cannot canonicalise all edges. |
| DD9 | Canonical top/left orientation for tile generation | Keeps the tile definition unambiguous while still testing all four rotations. |
| DD10 | Score in page space, not sRGB | The page's own space is what goes to press. |
| DD11 | RGB proxy default; native CMYK entries allowed and separately ranked | Production is mostly RGB-rendered but a CMYK-native model must not be excluded. |
| DD12 | Relative colorimetric intent with BPC, declared once | The intent changes the round-trip floor and must be identical for model and floor. |
| DD13 | Publish `roundtrip_gt` floor | Without it, a CMYK dE cannot be attributed to the model. |
| DD14 | Classify STOP/NO_INK instead of dropping | The ~35% of v1 pages where paper is correct (43/124: 10 blank + 33 short) are the restraint test, not invalid data. |
| DD15 | Ink test uses ΔE00 relative to paper | v1's 200/245 thresholds miss pale tints and coloured paper. |
| DD16 | Depth p90, classes at ≤1 / 2–`full_min` / ≥`full_min`, with `full_min = max(2, round(0.8·s))` | Matches the measured bimodality and holds out the empty middle class; the threshold tracks DPI through the scored ring (V12) instead of a fixed 30 px that 150 DPI pages can never reach. |
| DD17 | No drop for “art stops short of full bleed” | That is the production case the benchmark exists to score. |
| DD18 | Family-level 50/25/25 splits | Page/tile splits leak content and overstate significance. |
| DD19 | Public synthetic train split | Public baselines need training data that is disjoint from evaluation. |
| DD20 | Synthetic mix matches census marginals, not uniform | A uniform generator would optimise classes that barely occur in production. |
| DD21 | 640 eval pages / 64 families public synthetic | Enough for ranking and model development; not enough for a 1% claim, which is stated. |
| DD22 | Public real 300 / 100 target, 120 / 40 minimum | Licence-clean real pages are scarce; the minimum is the smallest usable cross-domain set. |
| DD23 | Private 1,300 pages / 400 families | 3.35% ±1.03–1.06 pp at DE 1.11 needs ~1,300; families absorb clustering. |
| DD24 | HMAC-hashed ids with per-company salt | Aggregates can leave the building without enabling re-identification. |
| DD25 | k-anonymity floor of 5 families | Suppresses cells that could identify a single job. |
| DD26 | Frozen seven-method reference oracle | Severe must not change when a new submission enters the table. |
| DD27 | Keep the v1 severe rule | It is comparable, robust to hard GT, and already understood by reviewers. |
| DD28 | Add absolute per-class failure rules | A relative rule cannot fail a method when every candidate is bad. |
| DD29 | SystemGain is the primary number | It is the actual production decision (route or fall back), not a weighted quality index. |
| DD30 | Harness calibrates the gate threshold | Letting submitters choose it makes “accepted severe” incomparable. |
| DD31 | Gate A 1%, Gate B 3.35% accepted-tile severe | One is a stretch safety target, the other is non-inferiority to edge repeat. |
| DD32 | Tile-level severe for the gate; page-level for private acceptance | A zero-event 1% bound needs 299 units; tiles are plentiful, pages are not. |
| DD33 | Page fidelity is p90, page safety is worst tile | A single texture tile should not define page quality; one visible defect should still stop the page. |
| DD34 | Production weights derived from the census | The benchmark's average should reflect the pages a printer actually sees. |
| DD35 | Texture oversampled in public test, reweighted | 32 texture pages are too few for a class claim, but production texture is 5%. |
| DD36 | MAE reported but not the headline | v1's mean/median gap shows it is dominated by a hard minority. |
| DD37 | SSIM kept as a secondary metric | Comparability with v1, but it is luminance-only and insensitive to hue. |
| DD38 | Hallucination detectors gate only after human validation | An unvalidated detector would disqualify models on its own bias. |
| DD39 | Four independent hallucination detectors | No single no-GT detector covers text, objects, structure and holistic plausibility. |
| DD40 | 1,200-strip human-labelled validation set | Precision cannot be estimated from synthetic injections alone. |
| DD41 | SCS thresholds: 3°, 2 px, width 0.75–1.33, dE 2 | These are the print-visible tolerances for a continued rule or baseline. |
| DD42 | Corners scored separately with arm consistency | Two edges must agree; corner content is structurally harder than edge content. |
| DD43 | Quiet timing protocol with locked clocks, batch 1 | v1's under-load timings are not comparable across methods. |
| DD44 | 1024 tile on a 25% subset | Full 1024 × four orientations is too expensive for a leaderboard entry. |
| DD45 | Robustness defects are injected, not collected | Clean causal attribution; real trim errors are rare and confounded. |
| DD46 | Keep a legacy v1 mode | Preserves historical comparability while v2 geometry changes the headline. |
| DD47 | No FID/KID as primary | The task is per-page fidelity and restraint, not distribution matching. |
| DD48 | Unprompted track primary; caption-oracle diagnostic only | Production has no caption; the diagnostic measures the cost of that constraint. |
| DD49 | 1,000 family-bootstrap resamples | Standard, stable enough for 95% percentile intervals. |
| DD50 | Exact Clopper-Pearson bounds for gates | Zero-event gates cannot be certified by a normal approximation. |
| DD51 | Trim identity is a DQ, not a penalty | A changed trim pixel is not a production-valid output. |
| DD52 | Canary pages in public test | Makes undetected test-set training less likely and auditable. |
| DD53 | Thresholds provisional until calibration, then frozen | Prevents post-hoc threshold tuning on the sealed test. |
| DD54 | 6 edge tiles/edge at 512, 4 at 1024, 4 corners | Matches v1 sampling density at 512 and avoids heavy overlap at 1024. |
| DD55 | 350-page private acceptance set | 299 effective accepted pages at DE 1.11 plus gate-rejection headroom. |
| DD56 | No captions, OCR or page text in `meta` | Production has no caption; using page text is a different task. |
| DD57 | 8-bit default, 16-bit declared | Most print pipelines are 8-bit, but colour floors may need 16-bit; declared, never mixed. |
| DD58 | Tile-seam and ring-consistency metrics | A model can be locally good and globally inconsistent. |
| DD59 | A6 thresholds stricter than edge repeat on flat | A 3-level step on a solid is a defect even when it is the best available. |
| DD60 | 60-strip accept/reject + 300-pair human study with 3 raters | Cheap enough to repeat, powered for ranking and directional threshold checks. |
| DD61 | V11 render region: BleedBox + apron, clipped to MediaBox, paper-padded and unscored | Real pages can lack pixels beyond the MediaBox; padding must not become GT. `padded_px` lives in the label store, so the 133-column CSV is unchanged. |
| DD62 | C8 is `n/a` for four-pass whole-page models; C7 only | There is no single-pass arm to compare against; empty `ring_gap` is the existing n/a convention. |
| DD63 | σ_texture measured at calibration, not assumed | The 15–20 planning range drives n; the measured value replaces it. |
| DD64 | R1/R2 v1 figures are `provisional-until-freeze` | They come from v1 aggregates; the frozen private aggregate file is cited by SHA-256 at freeze. |
| DD65 | BL11 omitted from numbers-to-beat unless its derivation is named and hashed | A constructed pipeline is not reproducible without its adapter identity. |
| DD66 | Gate certificates labelled `CP-DE`, bootstrap UB reported beside | The design-effect CP bound is an approximation; the label prevents over-reading it. A1 is recorded as `ASM-A1`. |
| DD67 | Tier C0 is a pilot: calibration, dev, training and design-effect estimation, never a production certificate | 34 real-GT families cannot bound a 1% rate; claiming otherwise repeats v1's C13. |
| DD68 | Pseudo-GT (track P) is training and transfer-diagnostic data only | A page's outer margin is not real bleed; the gap is measured (T10), not assumed. |
| DD69 | A family lives in exactly one partition; real-GT families never train | Near-duplicate versions inside a family would otherwise leak across the boundary. |
| DD70 | Train is partitioned `train_fit` / `train_dev` / `gate_fit` | Checkpoint selection and gate fitting must not see inpainter training data. |
| DD71 | `cal_cert` is touched only by certification | Thresholds, class rules and τ are fitted on `cal_sel` or train partitions. |
| DD72 | Families by multi-signal union-find with hub suppression; date-named and >20-file folders are not family evidence; merge when uncertain | Measured: folder-only linking merged 412/455 files through a preview portfolio and print-batch folders. |
| DD73 | V12 scored ring `min(b, floor(bleed_pt·dpi/72))` | 0.125 in at 300 DPI is 37.5 px; the half pixel is not GT. |
| DD74 | Gate selection/certification units are orientation-0 tiles; DE measured on those units | Rotations of a tile are near-copies; counting them inflates `n` four-fold. |
| DD75 | Corpus-trained submissions declare a training manifest (page keys, template ranges, splits SHA); the harness audits it | The only way to make "no eval data in training" checkable. |
| DD76 | Generator priors come from non-test families; public generator assets are CC0/OFL only | Prior leakage is training leakage by another route. |
| DD77 | A census cell replaces a v2.0 assumption only if its 95% family-bootstrap CI half-width ≤ 10 pp; otherwise the generator shrinks halfway toward the measurement and both are reported | Measured cells are wide (few families); replacing outright would trade one assumption for noise. |
| DD78 | Production weights are recomputed from the deployment census at Tier C freeze, not from C0 | C0's deployment census is one shop; weights are a population claim. |
| DD79 | `inferred_trim` pages (no TrimBox, media = standard + 0.25 in) are scored only after per-page human verification, as their own stratum | The trim is inferred, not declared. |
| DD80 | Imposed sheets and sub-240-DPI rasters are not GT (kept as family-link evidence) | They duplicate other pages or carry upsampled pixels. |
| DD81 | C0 stores are 8-bit PNG | The renderer is 8-bit; 16-bit remains normative for Tier A. |
| DD82 | Cost runs declare GPU and `clocks_locked`; unlocked runs are ineligible for H comparisons | Clock locking needs admin rights; the flag keeps the result honest. |
| DD83 | D1 on the returned output (DQ); D2–D4/D6 on the exposed network output (reported) | Removes the v2.0 contradiction that disqualified every full-image model. |
| DD84 | STOP = missing bleed: no fidelity GT, separate table; restraint on NO_INK | Art touching the trim without extension is a prepress defect; "paper" is not the desired output. |
| DD85 | Weights are never unpickled at evaluation: restricted-unpickler conversion to safetensors, SHA-256 pinned | Arbitrary-code execution risk in legacy checkpoints. |
| DD86 | A6 seam rule (C1 > 2) applies to flat and gradient only | Keeps §4.1's rule that the reference passes its own absolute thresholds. |

---

## Appendix B — constants, profiles and formats

### B.1 Geometry constants

| DPI | Bleed | `b` | `a` | `B` | 512 known | 1024 known |
|---|---|---|---|---|---|---|
| 150 | 0.125 in | 19 | 13 | 32 | 480 | 992 |
| 300 | 0.125 in | 38 | 10 | 48 | 464 | 976 |
| 300 | 5 mm | 60 | 4 | 64 | 448 | 960 |
| 600 | 0.125 in | 75 | 5 | 80 | 432 | 944 |

`b = ceil(physical_mm / 25.4 × dpi)`; `a = (−b) mod 16`; `B = b + a`. Tile sizes 512 and 1024 are both multiples of 16.

### B.2 Colour profiles and intent

| Space | Profile | Use |
|---|---|---|
| sRGB | IEC 61966-2-1 | default RGB page space |
| Adobe RGB | Adobe RGB (1998) | wide-gamut RGB pages |
| CMYK coated | FOGRA39 / ISO Coated v2 | default CMYK |
| CMYK US | GRACoL2013 / SWOP2013 | US print pages |
| Gray | Gray Gamma 2.2 | gray pages |
| Spot | recipe table in page metadata | spot pages |

Intent: relative colorimetric, black-point compensation on, no dithering, 8-bit default, 16-bit declared. The profile hash (`profile_sha256`) is part of every row; a page whose profile is missing is rendered with the declared default and flagged `profile_default=true`.

### B.3 File formats and pins

- GT and input: 16-bit PNG (lossless) plus a `.json` sidecar; no JPEG anywhere in the GT path.
- Page renders: 16-bit PNG, page space, with the ICC profile name in the sidecar (not embedded, to keep hashes stable).
- Metrics: computed in float64 after decoding to page space; 8-bit outputs are expanded with the exact inverse transfer function.
- Renderer: pinned Cairo/MuPDF version; anti-aliasing on; no hinting changes between splits.
- Fonts: open licences only (OFL/Apache); font list and hashes in the manifest.
- Photos: CC0 sources only in Tier A; source URL + SHA-256 + licence evidence per image.
- Containers: `bleedbench-eval` image digest; `bleedbench-gen` image digest for Tier A generation.

### B.4 Allowed run-time features (`feat_*`)

`feat_grad_mean`, `feat_color_var`, `feat_edge_density`, `feat_near_white`, `feat_mirror_disagree`, `feat_paper_score`, `feat_local_entropy`, `feat_local_contrast`, `feat_mask_edge_dist`, plus any model-internal uncertainty computed **only** from the input tile and mask. The list is closed: a new feature requires a protocol minor version and a re-audit. A gate may use a subset; it may not use a feature computed from the output and GT jointly, from another method's result, or from page metadata beyond geometry/colour.

### B.5 Reference numbers for v1 compatibility (legacy mode)

These are v1's published dev-set results, to be reproduced in `legacy_v1` mode (38 px unknown, 474 known, top orientation only, sRGB) within ±5%, except methods marked subset:

| Method | MAE | dE00 | SSIM | BGE | Severe % |
|---|---|---|---|---|---|
| edge_repeat | 11.50 | 4.01 | 0.87 | 3.78 | 3.35 |
| stretch | 12.86 | 4.56 | 0.86 | 3.78 | 4.51 |
| ns | 11.96 | 4.19 | 0.89 | 4.01 | 7.40 |
| telea | 12.63 | 4.50 | 0.87 | 4.45 | 39.5 |
| mirror | 17.37 | 6.11 | 0.82 | 4.40 | 12.9 |
| linear_extrapolation | 13.66 | 5.12 | 0.79 | 3.97 | 20.0 |
| lama | 14.06 | 4.94 | 0.84 | 4.94 | 35.9 |
| patchmatch (subset 480) | 16.50 | — | — | — | 8.75 |
| sd_inpaint (subset 730) | 78.37 | — | — | — | 88.9 |
| sd_refine | 12.60 | — | — | — | 20.6 |

A harness that cannot reproduce edge repeat's 11.50 ±5% on the legacy manifest is not ready to score v2. The v2 geometry is expected to move these numbers; only the legacy table is a regression target.













