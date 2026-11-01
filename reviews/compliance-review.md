# compliance-auditor review — bleedBENCH v2.0

Verdict: **PASS WITH FIXES**

Audited: `SPEC.md` (SHA-256 `E934DF31255360724EC0CA3B206C24348E72EAA33681D7F3B86D7FFA06C2AA3C`, 1,481 lines) against `docs/review-checklist.md`. The document moved once during the audit: an earlier revision (`356DCEFA…`) was read first; the current revision adds a two-line "v1-derived targets" note in §9.4 and removes one of the duplicated §10.6 headings. Findings below were re-checked against the current revision; line numbers are current except where a reference lands between §9.4 and §10.6 (those shift +2, and the §10.3/§10.4 refs have been updated). Section numbers are stable if the document moves again. The specification was read in full; no edits were made to `SPEC.md`, `README.md` or other reviewers' files.

Scope of this audit: requirements compliance (checklist §A–§H), not prose. The data shapes, geometry arithmetic and statistics were recomputed where the checklist allows it. The verdict is **PASS WITH FIXES** rather than PASS: every required section exists and every required axis is scored, and the hard-constraint list is satisfied, but several S1 requirement/sub-item gaps and a set of internal contradictions must be closed before protocol freeze.

## Top findings (severity order)

| # | Severity | Location | Finding | Evidence / recomputation | One-line fix |
|---|---|---|---|---|---|
| 1 | S1 | §0 L42–L43; §7.4 L870; §7.6 L885 | **SystemGain is defined three incompatible ways**, and `MAE_page` is never defined. §0 defines a *mean over pages* of `MAE_page(M_ref,p) − MAE_page(M_system,p)`; §7.6 defines a *tile-weighted* sum `Σ_t w_t·[MAE_edge_repeat(t) − MAE_system(t)]/Σ_t w_t`; §7.4 says "page_fidelity is the continuous quantity used for SystemGain" while §7.6's `MAE_system(t)` is a tile quantity. A leaderboard entry cannot be reproduced from one definition and scored on another. | The three formulas are mutually non-equivalent (a page-level p90 mean ≠ a tile-weighted sum; `page_fidelity` ≠ `MAE_model(t)`). `MAE_page` appears only in §0; §7.4 defines `page_fidelity` as a p90, not a mean. | Define SystemGain once, at page level (`page_fidelity` per page, production weights), rewrite §7.6 in the same units, and rename any tile-weighted variant (e.g. `TileGain`) so only one primary exists. |
| 2 | S1 | §4.6 F1/F3; §2.7 L246; §3.4 V5 L359; §3.1 L314; §8 T4 L931 | **Required F sub-items are missing or self-contradictory.** (a) "Crop marks at 0/9/38 px" — a checklist §B requirement — occurs nowhere in the spec; `cropmark_offset_px` exists as a CSV column but no offset values are defined. (b) F3 uses undefined `mark_ink` and `mark_line`, and its sanity baseline `mark_filter` is not one of the §9.1 baselines. (c) Crop marks are "out of scope" (§2.7) yet 5% of Tier A pages and 60 T4 pages are crop-mark pages, and V5 invalidates edges whose GT ring contains crop marks — exactly the F-manifest pages. (d) F1 requires δ ∈ {1,2,4} px but the table gives thresholds only at δ=2 and δ=4; no failure threshold exists for the required 1 px outward error. | No "0/9/38" anywhere; T4 = 60 crop-mark pages; Tier A 5%×640 = 32 crop-mark pages, not 60; V5 L359 excludes "crop/registration marks" from valid edges; F1 row L593: "> 1.5 at δ=2; > 3.0 at δ=4". | Add a crop-mark primitive/injection with offsets 0/9/38 px and per-offset thresholds; define mark geometry/colour and `mark_filter`; exempt F-manifest pages from V5; add a δ=1 px F1 threshold. |
| 3 | S1 | §2.8 L252–L262; §3.1 L314; §3.6 L381–394; §4.5 E6 L560/L572; §8 T5 L932 | **The required "wide gamut" sub-item is not operationalised.** Adobe RGB is declared as a supported page space (§2.8 table, Appendix B.2), but no tier mix, track, target-count table or metric row contains a single Adobe RGB page. E6 is a *clip-rate* proxy computed on GT pixels outside the model-space gamut; it measures neither E1/E2 fidelity on a wide-gamut page nor the model's mapping choice. | "Adobe RGB" occurs only at L257 and L1429; §3.1 special pages omit it; T5 lists 48 CMYK + 6 spot + 8 rich-black + 16 near-white only; §3.6 has CMYK but no Adobe RGB row. | Add Adobe RGB/wide-gamut pages to the Tier A mix and T5 (with counts in §3.6) and a wide-gamut E row (E1/E2 on `adobe_rgb` pages, net of the round-trip floor); or remove Adobe RGB as a supported page space. |
| 4 | S1 | §6.4 L810–L813; §4.3 C4 L510; §9.3 L1002 | **C4/SCS is undefined in the no-line case and the harness self-test contradicts the definition.** §6.4 defines `SCS = 0 if no known lines reach the seam`; §4.3's C4 sanity baseline is `gt_copy = 1.0`; §9.3 (an "exact" self-test) expects "Solid page, `gt_copy` … C4 = 1.0". On a solid page no line reaches the seam, so the spec simultaneously requires 0 and 1.0. | §6.4 L812 "(0 if no known lines reach the seam)"; §9.3 L1002 "Solid page, `gt_copy` … C4 = 1.0"; C4 row L510 "`gt_copy` = 1.0". | Define the empty case explicitly as `SCS = 1.0` ("vacuously continued") when no known line reaches the seam, or change the §9.3 test and the C4 baseline to 0; state the convention in §6.4. |
| 5 | S1 | §0 L39; §3.3 L336; §7.6 L891; §7.7 L901; §10.3 L1082 | **Page-level ≤1% certification is internally inconsistent.** §0/§3.3 say the 300-page acceptance set certifies a zero-event 1.0% page bound; §7.6/§7.7 make the gate reject units; §10.3 says 1,300 pages give 325 accepted pages for the same claim. A 300-page set behind a gate yields at most 300 accepted pages, and any rejection drops below 299 — the zero-event 1% minimum — so the acceptance set can certify 1% only if nothing is rejected. If it is ungated, it is not the routed-production claim. | Zero-event 1% needs n=299 (`1−0.05^(1/299)=1.00%`); 300-page zero-event bound is 0.995%, only with 300/300 accepted; §10.3 itself says the gate may reject up to 75% (1,300→325). | Pick one path: certify page-level 1% on gate-accepted pages from the 1,300-page set (299 accepted), and keep the 300-page set as an ungated regression set; update §0, §3.3, §7.6 and §10.3 together. |
| 6 | S1 | §8 T3 L930; §3.1 L318; §3.6 L392 | **T3, a required track, is unbuildable as specified.** T3 asks for "320 STOP/NO_INK pages (test split 160)"; the sealed test split is 160 pages in total (§3.1: 160 pages/16 families), of which only ~80 are quiet (50%) and ≤80 inked, so the test split cannot supply 320 STOP/NO_INK pages. The 200 "hallucination-challenge strips" are also not tied to the §5.4 set definition. | §3.1: calibration/validation/test = 320/160/160; §3.6: 320 quiet pages across *all* eval splits; T3 itself says test split 160. | Re-specify T3 counts: ~80 quiet + up to 80 STOP pages from the test split (160 total), or run T3 across all eval splits with per-split counts; state the exact strip subset used (e.g. 200 of the §5.4 strips). |
| 7 | S1 | §3.1 L301–L316 | **The normative synthetic mix targets are not derivable from each other.** Material shares (57.9/29.0/10.0/2.5/0.6%) are labelled marginals "among inked edges" (1,280 edges), but the stated page counts 185/93/32/8/2 are computed as those percentages of the 320 inked *pages*. The FULL 32.4%/STOP 17.6% split does not follow from "50% quiet + 50% hidden bleed on image edges": image STOP alone implies 1,280×0.579×0.5 = 370.6 STOP edges (14.5% of 2,560), and assuming all non-image inked edges are FULL implies ≈909 FULL (35.5%), not 829/451 (32.4%/17.6%). | 0.579×320 = 185.3, 0.29×320 = 92.8, sum 320 inked pages; but 0.579×1,280 = 741 image edges — the page count assumes one material per page and four inked edges/page, which the mixed-page primitive and STOP/SHORT pages violate. 370.6 STOP + 451 target means 80 unexplained STOP edges from flat/pattern/text, which the "derivation" column does not state. | Specify the generation joint (per-page material, edges per page, hidden-bleed conditional) and recompute/pin the FULL/STOP shares and page counts in `synthetic_manifest.json`; show the derivation in the table. |
| 8 | S2 | §1 C9 L107; §5.1 L692–L702; §5.4 L738–L741; §12.3 L1190; DD39 L1386; DD40 L1387; O3 L1316; T3 L930 | **Detector-family and hallucination-validation-set counts contradict each other.** C9 says "three independent detector families"; §5.1 says "four"; the §5.1 table lists five (F1 structure, F2 OCR, F3 object, F4 judge, F5 GT-support); DD39 says four. §5.4's components total 2,000 strips (600 GT positives + 600 injected + 600 model negatives + 200 ambiguous), but DD40, O3 and §12.3 all call it a "1,200-strip set"; T3 uses 200. | 600+600+600+200 = 2,000; 600+600 = 1,200 (probably the intended "labelled" subset); "three" at L107, "four" at L692/L1386, five rows at L698–L702. | State "four detector families (F1–F4), with F5 GT-support used only where GT exists"; fix the validation-set total (2,000, of which 1,200 labelled/1,200 injected?) and propagate to T3, DD40, O3, §12.3. |
| 9 | S2 | §6.4 L810–L822 | **The SCS scale contradicts the per-line pass/fail tolerances.** A line that is *within* every stated per-line tolerance can fail C4. With only a 1 px offset (allowed ≤2 px), SCS = exp(−(1/2)²) = 0.779 < 0.80; with only `colour_err = 1.0` (allowed ≤2.0), SCS = 0.779; with `width_ratio = 1.2` (allowed 0.75–1.33), SCS ≈ 0.763. The "pass" envelope (3°, 2 px, 0.75–1.33, dE 2) maps to SCS ≈ 0.07–0.52, i.e. far below the C4 threshold. | SCS_line = exp(−(angle/3)²−(offset/2)²−(ln(w)/0.35)²−(colour/2)²). Offset 2 px alone → exp(−1) = 0.368; angle 3° alone → 0.368; colour 2 alone → 0.368; width 1.33 alone → exp(−(0.285/0.35)²)=0.515. | Re-tune the SCS weights or the C4 threshold so that SCS = 0.80 corresponds to the stated tolerance envelope (e.g. divide errors by 2×tolerance, or define C4 failure as "any per-line error beyond tolerance" and use SCS for ranking only); state the mapping. |
| 10 | S2 | §4.1–§4.10 tables | **The seven-field completeness requirement fails for a large fraction of metric rows.** 39 of 63 identifiable metric rows carry at least one missing/undefined/inconsistent field; A7 has no formula at all and D3 has no defined denominator. A7 has no formula; B5's formula is per tile while its threshold is per 1,000 tiles; D3 divides by undefined `K_neighbourhood`; F2/F3/F5 use undefined `ink share`/`mark_ink`/`mark_line`/`paper_share`; I1/I2/I6 `gt_copy` ratios are 0/0; G2/G3 thresholds name quantities absent from the formulas; H4 merges VRAM/load/throughput and J1 merges MAE/dE; `match_rate`, per-line errors and C7/C8 empty-overlap cases are under-specified. | See "§C Per-metric matrix" below for the row-by-row audit. | Add a formula column to every metric table, define every symbol/baseline, split merged rows, adopt a 0/0 ratio convention, and give `match_rate` and per-line errors full rows with range/direction/baseline. |

## Detailed notes

### §A Required structure (checklist §A, A1–A15)

All fifteen required sections exist, in the demanded order, and are not merged. Deviations:

| # | Required section | Location | Status | Note |
|---|---|---|---|---|
| A1 | One-page summary | §0 L33–L65 | PASS | Primary endpoint and hard gates present; but capability table gives stale ID ranges (see S3 below). |
| A2 | Critique of v1: right / keep / replace, blunt | §1 (K1–K11, C1–C22) | PASS | Keep table + replace list; blunt, ordered. |
| A3 | Task definition: inputs, outputs, scored/not, latent masks, orientation, tile + whole page | §2.1–§2.9 | PASS | Geometry, two canvas modes, latent mask (DD5–DD7), orientation policy, interfaces, colour pipeline all present. |
| A4 | Data: three tiers, generator spec, validity rules, splits, counts | §3.1–§3.7 | PARTIAL | Tiers, validity (V1–V10), splits, counts present; generator "documented parameter distribution" is only partial (see S3 F25); mix derivation inconsistent (S1 #7); quiet-share provenance unresolved (see §E quiet-share bullet). |
| A5 | Metrics: one subsection per axis A–J; seven fields per metric | §4.1–§4.10 | PARTIAL | One subsection per axis exists; seven-field completeness fails for 45/63 rows (S2 #10, matrix below). |
| A6 | Hallucination + restraint with and without GT; ≥2 independent approaches; human-label validation | §5.1–§5.5 | PASS | Four detector mechanisms + GT-support, human validation set, gating precision bar, explicit "no detector may clear the bar" fallback; set-size/count contradictions (S2 #8). |
| A7 | Structure continuation: detect, match, angle/offset/width/colour | §6.1–§6.5 | PASS | LSD/Hough/OCR detection, greedy matching, SCS/TCS/width/colour errors, pass/fail; SCS empty-case and scale conflicts (#4/#9). |
| A8 | Aggregation: tile/edge/page/family/class; means, medians, p90/p99; page = worst tile or argued otherwise; final leaderboard number and why | §7.1–§7.9 | PARTIAL | Units and page two-number score present; worst-tile explicitly argued; SystemGain rationale present. Means/medians/p90/p99 are scattered (edge median, page p90, per-tile p99, family mean) and no section states which statistic is reported for each unit at page/edge/family level (no page median/p99 rule). |
| A9 | Tracks: standard, whole page, robustness, colour, cost, scale; which are required | §8 T0–T9 | PASS | Required-entry and badge rules stated; T3 count and T4 manifest volume/gap issues (#6, F15). |
| A10 | Baselines and expected synthetic numbers so a new harness can be checked | §9.1–§9.3 | PASS | BL0–BL13, expected ranges, exact analytic self-tests; but C4 self-test is contradictory (#4) and R1's private texture numbers are unsourced (see §H R1). |
| A11 | Statistical reporting: family bootstrap 1,000; exact one-sided zero-event bounds; multiplicity; minimum samples | §10.1–§10.6 | PARTIAL | All four present; §10.4 sample-size arithmetic is inconsistent with its own σ/DE bases (F19). |
| A12 | Reproducibility: seeds, model/weight hashes, hardware, quiet timing, determinism rerun | §11.1–§11.5 | PASS | Seed derivation, pinning list, quiet protocol, determinism rerun all present; manifest list omission (S3 F29). |
| A13 | Human study: cheap pairwise protocol, print size, seam visible, number of judgments | §12.1–§12.4 | PASS | 40 stimuli, 300 pairs/rater, 3 raters, print-size PNG, toggleable seam guide, Bradley–Terry, threshold calibration; total-judgment and rater-hour arithmetic issues (F32). |
| A14 | Leaderboard/submission: per-tile CSV superset of v1, aggregate JSON, DQ checks | §13.1–§13.4 | PASS | Superset verified below (all 22 v1 columns present, 5 as explicit aliases); aggregate JSON has axes/classes/pages/checks; DQ1–DQ14 present. |
| A15 | Open questions, each with the experiment that settles it | §14 O1–O14 | PASS | Every O# has *Experiment* and *Changes*; no hand-waving found (minor O14 wording, F36). |

Order/structure defects: `## 7. Aggregation` is glued directly after §6.5's last paragraph with no blank line (L829–L830, style only). The duplicate `### 10.6` heading present in the earlier revision has been fixed in the current revision.

**v1 CSV superset check (checklist A14):** compared the brief's v1 column list — `case_id, family_id, split, tile_id, edge, method, mae, delta_e, ssim, boundary_gradient_error, runtime_ms, preclamp_changed, grad_mean, color_var, edge_density, near_white, content_class, gt_near_white, oracle_method, oracle_mae, regret, severe` — against the normative header (L1205–L1222). All 22 are present: the first 12 and `content_class`, `oracle_*`, `regret`, `severe` natively, and `grad_mean`, `color_var`, `edge_density`, `near_white`, `gt_near_white` as explicit v1 compatibility aliases (L1222, defined L1225). PASS.

### §B All ten axes (checklist §B)

| Axis | Separately scored? | Required sub-items | Result |
|---|---|---|---|
| A Fidelity | Yes, §4.1 | GT metrics | PASS except A7 formula missing and A5 p90 undefined (matrix). |
| B Restraint | Yes, §4.2 | do-nothing + invent-nothing | PASS; B5 unit mismatch; B1/B2/B9 unit-of-threshold ambiguity (F31). |
| C Seam continuity | Yes, §4.3 | with and without GT | PASS; C7 empty-overlap and C8 compositing undefined; C4 contradiction #4. |
| D Known-pixel integrity | Yes, §4.4 | trim identity + clamp seam | PASS; D3 denominator undefined; D2/D4 rule overlap (F30). |
| E Colour | Yes, §4.5 | dE, flat drift, near-white, rich black, CMYK round-trip, spot/wide gamut | PARTIAL — spot present (E7), wide gamut missing (#3). |
| F Geometry robustness | Yes, §4.6 | trim 1/2/4 px outward, crop marks 0/9/38, partial hidden bleed | FAIL — crop marks absent, δ=1 threshold missing (#2); partial present (F4) but manifest volume unsupported (F15). |
| G Determinism | Yes, §4.7 | seeds, reruns, orientation, batch | PASS; G2/G3 thresholds name quantities absent from formulas, G4 tolerance undefined (matrix). |
| H Cost | Yes, §4.8 | quiet, GPU, batch, gain vs edge repeat | PASS; H1/H2 thresholds mutually incompatible, H2 hard-codes 28 tiles (F16). |
| I Scale | Yes, §4.9 | 38/60/19 px, 512/1024, whole page | PASS structurally; ratio baselines 0/0, I4 pairing confounded, I5 mixes p90/mean (F18). |
| J Corners | Yes, §4.10 | separate corner scoring | PASS; J1 row merges MAE/dE, J2 undefined when tiles don't overlap (matrix, F17). |

"Do not collapse into one number" is honoured: §7.6 says SystemGain "is never the only output"; §7.9 requires the ten-axis vector and paired deltas before SystemGain; §13.2 emits an `axes` object. The only problem is that SystemGain itself has three definitions (#1).

### §C Per-metric matrix (checklist §C)

Legend: ✓ present and unambiguous; △ present but partial/ambiguous/undefined term; ✗ absent. Columns are the seven checklist fields: formula, range, direction, failure threshold, near-perfect sanity baseline, blind spot — plus name (table/ID).

| ID | Metric | Formula | Range | Dir | Thresh | Baseline | Blind spot | Defect |
|---|---|---|---|---|---|---|---|---|
| A1 | MAE overall | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| A2 | Mean dE00 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| A3 | Masked SSIM | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| A4 | PSNR | ✓ | ✓ | ✓ | ✓ rule (20 dB floor, report only) | ✓ | ✓ | — |
| A5 | Class MAE + p90 | △ | ✓ | ✓ | ✓ | ✓ | ✓ | p90 sub-metric has no formula/range/failure threshold |
| A6 | Absolute fail rate | △ | ✓ | ✓ | ✓ aggregate rate | ✓ | ✓ | formula `AF(tile)` is binary but row/name is a rate; aggregate threshold under a "per tile" header |
| A7 | Tail MAE p99 | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | no formula anywhere (p99 of what, at which unit?) |
| B1 | STOP false-ink rate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | edge-level metric under §4.0 "thresholds are per tile" (F31) |
| B2 | Largest false-ink blob | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | same unit ambiguity |
| B3 | Invented-edge density | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `E_gen/E_exp` defined only in §5.3, no cross-ref |
| B4 | Invented OCR chars | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| B5 | Object/face/logo hits | △ | ✓ | ✓ | ✓ | ✓ | ✓ | formula divides by number of tiles but threshold/range are per 1,000 tiles (missing ×10³) |
| B6 | Continuation-judge fake rate | ✓ | ✓ | ✓ | ✓ | △ calibrated 5% FPR, not near-perfect | ✓ | baseline is a judge FPR, not a perfect score (defensible, but state it) |
| B7 | Invented-content area | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| B8 | Solid continuation drift | △ | ✓ | ✓ | ✓ | ✓ | ✓ | `U_flat` and "flat FULL edge" not defined |
| B9 | STOP accept rate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | edge-level vs per-tile header; threshold `<0.98` has implied edge fraction |
| C1 | Seam step error | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| C2 | Seam dE error | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| C3 | Boundary gradient error | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | threshold >3.0 conflicts with A6's C1>3.0 (different metrics, same symbol family) — clarify (F30) |
| C4 | Line continuation score | △ | ✓ | ✓ | ✓ | ✓ | ✓ | SCS empty-case contradiction (#4); SCS scale vs per-line tolerance (#9) |
| C5 | Text continuation score | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | TCS formula only in §6.4; no per-line pass rule (fine for a tile threshold) |
| C6 | Unsupported-edge ratio | △ | ✓ | ✓ | ✓ | ✓ | ✓ | formula terms defined in §5.3 but "seam" and salience threshold not cross-referenced |
| C7 | Tile-seam disagreement | △ | ✓ | ✓ | ✓ | ✓ | ✓ | undefined when adjacent tiles do not overlap (jitter can remove overlap) |
| C8 | Ring-consistency gap | △ | ✓ | ✓ | ✓ | ✓ | ✓ | compositing rule for tile-mode ring not defined |
| D1 | Trim violations | ✓ | ✓ | ✓ | ✓ DQ | ✓ | ✓ | — |
| D2 | Pre-clamp changed pixels | ✓ | ✓ | ✓ | △ conditional "unless D6 passes" | ✓ | ✓ | overlaps D4; rule is not numeric without D6 |
| D3 | Changed fraction | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | denominator `K_neighbourhood` undefined |
| D4 | Max pre-clamp change | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| D5 | Regenerated trim pixels | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| D6 | Clamp-seam dE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| E1 | Page-space dE00 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| E2 | Flat channel drift | △ | ✓ | ✓ | ✓ flat_drift_c only | ✓ | ✓ | `flat_drift_E` has no separate threshold; `U_flat` undefined; `recipe_match` baseline undefined |
| E3 | Rich-black error | △ | ✓ | ✓ | ✓ | ✓ | ✓ | formula is a tuple `(ΔK,ΔCMY,ΔTAC)`, not an equation; ΔCMY/ΔTAC sign and TAC unit undefined |
| E4 | Near-white leak | △ | ✓ | ✓ | ✓ | ✓ | ✓ | "near-white GT edge" (page class vs per-pixel) undefined |
| E5 | CMYK round-trip dE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | floor defined §2.8; E5(roundtrip_gt) notation circular but interpretable |
| E6 | Gamut clip rate | △ | ✓ | ✓ | ✓ rule | ✓ (roundtrip floor) | ✓ | formula uses GT only, not the model output; no wide-gamut page population (#3) |
| E7 | Spot tint error | △ | ✓ | ✓ | ✓ | ✓ | ✓ | `roundtrip_spot_gt` floor is referenced in §2.8 but never defined or measured |
| E8 | Colour-space declaration | ✓ | ✓ | — | ✓ DQ | ✓ | ✓ | bool/direction dash is legitimate |
| F1 | Outward-trim inflation | ✓ | ✓ | ✓ | ✗ δ=1 missing | ✓ (undefined `trim_aware_fill`) | ✓ | required δ=1 px threshold absent; row name says "at 2 px" |
| F2 | Margin coping rate | △ | ✓ | ✓ | ✓ | ✓ (`oracle trim detector` undefined) | ✓ | "output ink share" undefined |
| F3 | Crop-mark leak rate | △ | ✓ | ✓ | ✓ | ✓ (`mark_filter` undefined) | ✓ | `mark_ink`/`mark_line` undefined; no 0/9/38 offsets; V5 conflict (#2) |
| F4 | Partial-bleed accuracy | △ | ✓ | ✓ | ✓ | ✓ ("oracle" undefined) | ✓ | classification rule (paper vs continue) undefined |
| F5 | Margin false alarm | △ | ✓ | ✓ | ✓ | ✓ | ✓ | `paper_share` undefined |
| F6 | Inward-trim inflation | △ | ✓ | ✓ | ✓ δ=2 only | ✓ (`trim_aware_fill`) | ✓ | no δ=1 threshold; `trim_aware_fill` undefined |
| G1 | Same-seed identity | ✓ | ✓ | — | ✓ DQ | ✓ | ✓ | — |
| G2 | Seed metric spread | ✓ | ✓ | ✓ | △ severe-rate range not in formula | ✓ | ✓ | threshold mentions a quantity the formula doesn't compute |
| G3 | Orientation gap | ✓ | ✓ | ✓ | △ dE threshold not in formula | ✓ | ✓ | same |
| G4 | Batch/order gap | ✓ | ✓ | ✓ | △ "floating tolerance" undefined | ✓ | ✓ | tolerance not numeric |
| H1 | p50 tile runtime | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| H2 | Page runtime | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | "28 tiles" wrong for 1024 (20), small pages, whole-page mode (F16) |
| H3 | Gain per second | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| H4 | VRAM/load/throughput | △ | △ mixed units | △ mixed | ✓ OOM/VRAM/60 s rule | △ "trivial" | ✓ | three metrics in one row, no separate VRAM/throughput thresholds |
| I1 | Bleed-width ratio 60 px | ✓ | ✓ | ✓ | ✓ | △ `gt_copy` 0/0 | ✓ | ratio baseline undefined at zero |
| I2 | Bleed-width ratio 19 px | ✓ | ✓ | ✓ | ✓ | △ 0/0 | ✓ | same |
| I3 | DPI consistency | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| I4 | 1024 tile gain | ✓ | ✓ | ✓ | ✓ | ✓ 0 (neutral, passes) | ✓ | pairing confounded: 512 uses E=6, 1024 uses E=4 |
| I5 | Whole-page vs tile gap | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | page uses p90, tile uses mean — not like-for-like |
| I6 | Aspect-ratio gap | ✓ | ✓ | ✓ | ✓ | △ 0/0 | ✓ | baseline undefined |
| J1 | Corner MAE/dE | △ | △ two ranges | ✓ | △ single ratio for both | ✓ | ✓ | two metrics merged; dE needs its own threshold |
| J2 | Corner-arm disagreement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | undefined when corner/edge tiles do not overlap |
| J3 | Corner structure score | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| J4 | Miter dE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| J5 | Corner fail rate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| §6 | `match_rate` | ✓ | ✗ | ✗ | ✓ (inside C4) | ✗ | △ (occlusion) | no row, no range/direction/baseline |
| §6 | `angle_err_err`, `offset_err`, `width_ratio`, `width_err`, `colour_err` | ✓ | △ (width_err no range) | ✗ | ✓ §6.4 | ✗ | △ | per-line diagnostics in the normative CSV but not metric rows (no direction/baseline) |
| §5 | `halluc_edges`, `edge_precision`, `edge_recall`, `missed_edges` | ✓ | ✗ | ✗ | ✗ declared diagnostics | ✗ | ✗ | §5.2 explicitly says they are supporting diagnostics (acceptable if not scored, but they are columns/claims) |
| §5 | detector precision/recall/AUROC/AP | ✓ | ✗ | — | ✓ precision ≥0.90, AUROC ≥0.85 | — | — | validation criteria, not metric rows; acceptable |

**Tally:** 39 of 63 metric rows have at least one missing/ambiguous/undefined/inconsistent field; the wholly missing elements are the A7 formula and the D3 denominator, and several rows (B5 unit, F1 δ=1 threshold, F3 required offsets/terms, F2/F4/F5 undefined terms, I1/I2/I6 0/0 convention, `match_rate` range/direction/baseline) have their required field present syntactically but unusable. Undefined sanity baselines used in tables: `trim_aware_fill` (F1/F6), `oracle trim detector` (F2), `mark_filter` (F3), `oracle` (F4), `recipe_match` (E2), `roundtrip_spot_gt` (§2.8/E7). The §9.1 baseline list (BL0–BL13) does not contain any of these.

### §D Hard constraints and "do not" list (checklist §D 1–13)

| # | Requirement | Satisfied? | Location / note |
|---|---|---|---|
| 1 | Trim pixels bit-identical; violation = DQ, not penalty | YES | §4.4 D1, §2.4 contracts, §13.4 DQ1, §7.6 hard gates; "cannot be traded" L1304. |
| 2 | Severe rule retained as safety metric; absolute failure rules added that do not depend on candidates | YES | §4.0 L412–421 retains `severe` form; A6 absolute rules L448; B8 L484; C8 rationale. |
| 3 | Edge repeat is the reference; every headline table reports delta vs it with a CI | YES | §7.9 L910–919 mandates the `edge_repeat` row and a paired delta with 95% family-bootstrap CI for every headline table; §7.6 SystemGain is vs edge repeat; R7 CI. |
| 4 | Splits by job family only; sealed test read once, no tuning | YES | §3.5 L375; §10.5; DQ6; §4.0 threshold-freeze rule. |
| 5 | Classical and learned see identical inputs | YES | §2.3 point 3, §2.4 "Classical vs learned parity", §2.2 tile-is-page-crop rule. |
| 6 | No metric may read GT as a run-time feature; label/feature columns separate | YES | §2.7, §3.4 V10, §13.1 feature/label groups, DQ7, §7.7 step 6, B.4 closed namespace. Content-class naming ambiguity noted in F27. |
| 7 | Randomness seeded from case id | YES | §11.1 seed = SHA256(protocol_version‖case_id‖track‖tile_id‖orientation‖purpose); §2.2 placement seed = hash(case_id, edge, tile_index). |
| 8 | No single composite score as the only output | YES | §0 L46 "single number for ordering, never the only output"; §7.6 L893; §7.9; §13.2 `axes`. SystemGain definition ambiguity is #1, not a D8 violation. |
| 9 | No FID/KID as primary | YES | §2.7 L246 "not primary and are not reported"; DD47. |
| 10 | No prompt describing page content in the primary track; unprompted primary if prompted variants exist | YES | §2.4 `meta` prohibition; C15; T8 diagnostic; DQ11. |
| 11 | Do not assume RGB only; CMYK-native must be scoreable | YES | §2.8 CMYK-native path and separate sub-table; DD11; E5. Wide-gamut sibling gap is #3. |
| 12 | No tuning on sealed; no run-time feature reads GT | YES | §3.5 L375; §10.5 "sealed test opened once"; DQ6/DQ7; §7.7 step 4 freeze. |
| 13 | Hallucination metric not hand-waved; if none can be validated, say so and propose the human-label study | YES | §5.4 L741/L752: gating only after human labels; if no detector clears the bar, hallucination stays advisory and §12 human study is the only authority; O3. |

No D-item is violated. The substantive gaps are in checklist §B (F crop marks, E wide gamut) and §C (per-metric fields), not in the hard-constraint list.

### §E Data tiers (brief requirements)

- **Three tiers, purposes** — PASS: §3 table L276–L280 (A public synthetic: harness check/training/public leaderboard; B public real: cross-domain; C private: production acceptance/sealed), never pooled (§7.8).
- **Public synthetic generator spec** — PARTIAL. Primitives table (L290–L299) has eight primitives with parameter ranges for five of them; "each with a documented parameter distribution" is asserted but the distributions for Photo, Clipped vector art and Mixed page are not given; spot recipe table format, photo counts/palettes, family grammar, and the "40 px safety margin" purpose are unspecified. Generator acceptance tests (L320) are present, but (vii) "matches within tolerance" gives no tolerance. This is not sufficient to build `bleedgen` without further questions (checklist §F feasibility).
- **Mix matching census** — FAIL as arithmetic: see S1 #7. Material rows are edge-level, page counts are page-level, and the derived FULL/STOP shares are not reproducible from the stated assumption (implied STOP 370.6 edges/14.5%, FULL ≈909/35.5%, vs quoted 829/451 = 32.4%/17.6%).
- **Counts** — the headline counts now add up at the top level: 640 eval = 320 quiet + 320 needing fill; 320 inked pages split 185/93/32/8/2 = 320; 829 FULL + 451 STOP = 1,280 inked edges; 2,560 edges = 640×4; corner tiles 4×640 = 2,560; Tier B 117+69+99+15 = 300 and Tier C 507+299+429+65 = 1,300 (all PASS). The derivation of those counts from the census marginals is the problem.
- **Validity rules fixed for pale tints** — PASS: V3 uses ΔE00 >1.5 or L* < L*_paper−2, explicitly replaces the 200/245 heuristic; V6 confirms 3–20% tints on a 100-page audit with >1% failure rejecting Tier B. V2 paper estimate, V4 depth p90 classes ≤1 / 2–29 / ≥30, V5 inclusion default, V7 small pages, V8 apron GT, V9 model-space GT, V10 label isolation are all present.
- **Licence criteria** — PASS: §3.2 (a)–(e) (CC0/PD/CC-BY-4.0, BleedBox > TrimBox by ≥0.125 in, embedded ICC/fonts, no third-party marks/personal data, renderable), two-reviewer verification, archived licence text, `licence_evidence_hash`, redistribution terms, NOTICE/downloader.
- **Target counts per class** — PARTIAL: §3.6 covers total pages, families, quiet/fill, FULL/STOP, four content classes, texture oversampling, CMYK, corners. It omits the special-page counts of §3.1 (pale tint 64, rich black 32, near-white 64, spot ~19, partial bleed ~13, crop marks 32, 150 DPI 64, 600 DPI 32) and does not say whether those categories overlap (they almost certainly do: rich black ⊂ CMYK). The "crop marks 5%" row also conflicts with crop marks being out of scope (#2).
- **Families needed for a 1% severe bound** — PARTIAL/PASS: §10.3 L1085 adds the missing derivation ("zero events in 299 accepted units; ~92 families at 3.25 pages/family before clustering; 400-family target for ICC"), so the checklist asks is answered. But it collides with the 300-page acceptance-set claim (#5).
- **Brief drop-rate and bimodality facts** — PASS with an accounting caveat: C2 accounts for the 37 missing edges (179+280+37 = 496) with the NO_INK hypothesis; C1/C3 address the 27% short-bleed prevalence (33/124 = 26.6%); V4 formalises the 0–1 / 2–29 / ≥30 classes; DD14–DD17 record the design intent. Caveat: the spec does not reconcile "33 pages whose artwork stops at the trim" with "179 STOP edges" (179 > 33 pages × 4 edges = 132), nor "80 usable pages" with "496 gold edges" (496 = 124×4, not 80×4); and §3.3's "recovering the 33 STOP/NO_INK pages" to reach "124 pages / 70 families remains usable" omits the 10 blank-ring pages (C1 says they are NO_INK, not invalid) and the 1 small page (V7 reverses that drop) — 80+33+10+1 = 124, so the sentence should say all 44 recovered pages, not 33. Add the mapping (page-level vs edge-level counts) or the 124-page claim is not traceable.
- **Quiet 50% target** — provenance not established: §3.1 L305 quotes "about half of real pages need no pixel fill at all" with no source, while the spec's own v1 audit gives 10 blank-ring pages of 124 (8%) and 33 short pages of 124 (27%); the production weights (§7.1: quiet 0.500) and Tier B/C "expected" quiet counts (150/650) inherit the same number. If the 50% is a brief fact, cite it as such; if not, derive it from the v1 audit. This is a data-tier correctness risk, not just wording.

### §F Tracks (checklist requirements)

| Track | Status | Notes |
|---|---|---|
| T0 Sanity | OK | 20 analytic + 200 frozen tiles. |
| T1 Standard tile | OK | 160 test pages × 4 orientations × 28 tiles = 17,920 at 512 (checked); 25% at 1024; required for leaderboard. |
| T2 Whole page | OK | 200 pages (test+validation); required. |
| T3 Restraint/hallucination | **BROKEN #6** | 320 STOP/NO_INK pages "(test split 160)" impossible: test split has 160 pages total; 200 hallucination-challenge strips inconsistent with the 2,000-strip validation set. Required track. |
| T4 Robustness | **S1/S2** | "120 pages × 3 trim errors × 2 directions": outward δ ∈ {1,2,4} (3 values) and inward F6 δ ∈ {1,2} (2 values) gives 5 conditions, not 3×2=6; "60 crop-mark pages" and "60 partial-bleed pages" exceed the Tier A supply (crop marks 5%×640=32 pages total, partial bleed 2%×640≈13), and the robustness injection list does not include crop-mark or partial-bleed generation. F-manifest needs explicit volumes (F15). |
| T5 Colour | PARTIAL | 48 CMYK + 6 spot + 8 rich-black + 16 near-white test pages; 30% of 160 = 48 CMYK ✓, 3%→6, 5%→8, 10%→16 are consistent with §3.1; no Adobe RGB/wide-gamut pages (#3); rich-black and near-white overlap CMYK so page totals/costs double-count (state whether categories are nested). |
| T6 Cost | OK | 100 warm tiles + 20 pages, quiet protocol §11.3. |
| T7 Scale | OK | DPI×40, 60 px×40, 1024×40 pages; general-purpose badge. |
| T8 Prompt diagnostic | OK | optional, never ranked; unprompted primary rule holds. |
| T9 Legacy v1 | OK | 1,730 dev + 292 sealed; legacy mode only. |

Required-entry rules are stated (§8 L938): minimum T1,T2,T3,T5,T6 + determinism + D1; router candidate adds T4 + Gate A/B + D2/D6 + cost cap; general-purpose adds T7; T8 never ranked; T9 regression. DQ5 (L1293) matches the minimum set. Lite manifest (4,480 tile-runs = 25% of 17,920, one orientation; 40 whole pages) is consistent.

### §G Statistics, reproducibility, human study, leaderboard

**Statistics (checklist A11).**
- Family-cluster bootstrap B=1,000, stratified by split and page type, paired deltas, ICC/`n_eff`, BCa sensitivity, exact Clopper–Pearson in addition: PASS (§10.1).
- Exact-bound table recomputed and correct: n=11→23.8%, 48→6.05%, 80→3.68%, 89→3.30%, 160→1.85%, 292→1.02%, 299→1.00%, 320→0.93%, 1,000→0.30%, 1,300→0.23% (all `1−0.05^(1/n)`).
- CI half-widths recomputed: 3.35% at 160→±2.79 pp, 640→±1.39, 1,244→±1.00, 1,300→±0.98; ±1 pp at 3%→1,118, at 3.35%→1,244; ±0.5 pp→4,976. PASS.
- Two-proportion sizes: 1% vs 2%→2,319 (recomputed 2,315); 2% vs 3%→3,826 (3,822); 3.35% vs 4.35%→5,810 (7.849×0.07399/1e-4 = 5,808). The current text is consistent after the recent fix. PASS.
- **Arithmetic defect (F19):** §10.3 says 1,244 pages needed "plus ~5% attrition … → 1,300"; 1,300×0.95 = 1,235 < 1,244, so the set is ~9 valid pages short (1,244/0.95 = 1,309; state ~1,310). §10.4 "Mean MAE within a class ±0.5: ~1,500 (clustered), σ≈15–20, DE 2.35" recomputes to ≈8,100–11,100 at 95% CI (or ≈2,100–2,900 at 1 SE), not 1,500. §10.4 "Class ΔMAE = 2.5, 80% power: ~500 unclustered; ~1,200 clustered, σ≈20" recomputes to ≈1,005 per group unclustered (≈2,360/group with DE 2.35), not 500/1,200. Texture ΔMAE 1.7 row needs the same DE check (σ≈15 gives ~1,220 unclustered; DE 2.35 → ~2,870/group, more than 55 pages×28=1,540 tiles). Correct the table or state the one-sided/paired basis that produced the lower numbers.
- Multiplicity/pre-registration: four primaries (SystemGain, texture ΔMAE, flat severe rate, accepted-tile severe rate), Holm–Bonferroni FWER 0.05, secondary exploratory with CI + replication/Holm rule, sealed read once: PASS.
- Minimum-sample convention (`insufficient` marking): PASS, modulo the arithmetic above.


**Reproducibility (A12).** Seed derivation (§11.1), model/environment pinning (§11.2), quiet protocol (§11.3: dedicated GPU, <2% utilisation, locked clocks, power limit, 20 warm-up, ≥100 tiles batch 1, 3 repeats, p50/p90/p99, e2e/gpu split, second independent day, >10% rule), determinism rerun (§11.4: G1 10% twice in separate processes, G2 five seeds, G4 batch 1/4/8 + shuffle, `nondeterministic` handling), `bleedbench verify`, manifests and `reproduce.sh` (§11.5): PASS. Minor issues: §11.5's frozen-manifest list omits `synthetic_manifest.json` (required by §3.1) and `lite.json` (§8); `reproduce.sh` (§11.5) vs `REPRODUCE.md` (§13.3) naming inconsistent; §2.7/§7.7 point the feature namespace at §13.2, but `feat_*` is defined in §13.1 and Appendix B.4 — wrong cross-reference (F29).

**Human study (A13).** 40 strip crops (10 pass/10 fail/20 boundary), 6 in wide at print size 300 DPI, seam marked with toggleable neutral guide, 64 px known context, colour-managed display, proof sanity check; 300 pairwise comparisons per rater, 3 prepress raters, blinded/balanced pairs, optional defect category; Bradley–Terry with rater effects, Krippendorff α targets, ρ≥0.80 vs SystemGain, AUC≥0.75; A6/B1 threshold calibration via logistic regression; separate hallucination validation task. Checklist A13 is satisfied. Issues: (i) total judgments are ambiguous — "300 pairwise comparisons per rater" (L1179) × 3 raters = 900, but §12.3 and §10.4 power the study as 300 pairs; state whether the primary analysis pools 900 or uses 300/rater and how rater effects are handled. (ii) "300 pairs × 15 s ≈ 75 min per rater … Total ~4.5 rater-hours" recomputes to 3 × 75 min = 3.75 h (3.75 h, not 4.5). (iii) "6 in wide at print size" rendered at 300 DPI is 1,800 px; "100% zoom at the declared physical size" needs a display-PPI/zoom mapping and viewing distance, otherwise 100% zoom on a ~96 ppi display shows ~18.75 in, not 6 in (checklist §F print-size viewing). (iv) two α targets (0.60 ordinal / 0.70 binary) are fine, but §5.4 uses 0.70 for binary only — consistent enough.

**Leaderboard/submission (A14).** CSV header verified as a superset of v1 (see A14 above); one-row-per `(submission, split, page, tile, orientation, track)`; required columns fail validation; feature/label groups with legacy aliases and the DQ rule for gates reading `label_*`/`gt_near_white`; aggregate JSON has protocol/submission/scores/axes/classes/pages/checks/environment/files and the "every aggregate carries n, families, ci95, estimator" rule; submission package (model_card, environment.lock, weights.sha256, code, gate.py, track_config, REPRODUCE) and the network-disabled/GT-unmounted harness rule; DQ1–DQ14 cover trim, shape/range, colour, determinism, required tracks, split integrity, gate provenance, weights/config, sandbox, timeout, prompt, mask, canary and legacy claims. Issues: (i) §7.6 says the submitter provides `confidence`, §7.7 step 2 says "the harness computes `confidence`" — one must be fixed; (ii) the §13.2 example puts `gate.threshold: 0.665` in the submission block although §7.6/§7.7 say the harness freezes τ and the submission cannot choose it; (iii) aggregate JSON examples/`scores` omit `n`/`families`/`ci95` for e.g. `accepted_severe` even though the text requires every aggregate to carry them, and `page_mae`/`system_mae` CSV columns are never defined in §7; (iv) `predictions`-as-files rule and offline private mode are stated and consistent with DQ9.

### §H Numbers to beat (checklist §7, R1–R8)

| # | v1 condition / target | Operationalised? | Traceable? | Notes |
|---|---|---|---|---|
| R1 | Texture MAE beats LaMa margin 44.29 vs 45.96, CI excludes 0 | YES (`ΔMAE_texture > 1.67`, 95% family CI > 0) | PARTIAL | 45.96−44.29 = 1.67 ✓, but 44.29/45.96 do not appear in any SPEC table (Appendix B.5 has overall MAE only); cite the v1 private aggregate or `expected_baselines.json`. |
| R2 | Flat severe < 5% (LaMa 59%) | YES (`severe_rate_flat`, exact UB ≤5%) | PARTIAL | The 59% is now declared v1-derived (new §9.4 note L1031), but "flat-class severe rate" unit (pages vs tiles) and required n are still not stated; a zero-event ≤5% bound needs ≥59 units; §10.4 has no row for it. |
| R3 | Overall severe ≤ edge repeat 3.35% or gated equivalent | YES (Gate B accepted-tile severe ≤3.35%, or ungated ≤3.35%) | YES | Edge-repeat 3.35% matches Appendix B.5. |
| R4 | Zero pre-clamp changes or clamp seam no worse than BGE 3.78 | YES (D2=0, or D6≤1.5 and C3≤3.78) | PARTIAL | 3.78 is now explicitly a v1 placeholder in the new §9.4 note, but C3's own failure threshold is >3.0 (C table), so R4 still permits C3=3.5 which fails C3 — reconcile (F30). |
| R5 | <100 ms per 512 tile quiet, or justified | YES (H1 p50 ≤100 ms) | YES | Matches §8 router cap; H2's 1.5 s/page cap conflicts (28×100 ms=2.8 s, F16). |
| R6 | Capture ≥50% of oracle headroom | YES in text | **NO** | `SystemGain_headroom` is used in R6 but never defined (no formula, no unit, not in §13.1/CSV/JSON); as written R6 is not measurable. Define `SystemGain_headroom = Σ_{tiles where oracle_mae ≤ edge_mae−1} (edge_repeat_mae − MAE_m)` or similar. |
| R7 | SystemGain >0 with family CI excluding zero | YES (Gate A/B) | YES (but see #1) | Depends on the SystemGain definition being fixed. |
| R8 | Restraint non-inferiority B9≥0.98, B1≤0.001 | YES | YES | Matches B1/B9 thresholds. |

The new §9.4 "v1-derived targets" paragraph (L1031) correctly sources 3.35%, 59% and 3.78 as v1 placeholders and requires the reference harness to recompute edge repeat's v2 severe rate/BGE at freeze; that closes the provenance half of R2–R4 (but not R1's 44.29/45.96, not R2's unit/n, and not R4's C3-threshold conflict). Oracle headroom "2.5–2.9 MAE" is traceable to C17: 11.50−9.00 = 2.50 and 11.50−8.58 = 2.92, using edge-repeat MAE 11.50 from Appendix B.5. Cost "~2,600×" is traceable: sd_refine ~1,300 ms / edge_repeat ~0.5 ms = 2,600. The five v1 conditions map to R1–R5; R6 is the oracle headroom; R5 is also the cost; R7/R8 are new v2 gates. Once R6 is defined and R1/R2 are sourced/unit-ed, checklist §7 is satisfied.

### §I Open questions (checklist §8)

O1–O14 each state the question, the *Experiment* and the *Changes* (O1 1,000-page raster+vector audit; O2 A/B aligned vs unaligned; O3 1,200-strip human set; O4 orientation distribution + G3; O5 ICC refit; O6 press step-ladder; O7 caption A/B; O8 native CMYK vs proxy; O9 tile vs whole-page corners; O10 overlap sweep 0/16/32/64; O11 8 vs 16 bit; O12 100 spot pages; O13 Tier A→C rank correlation target ρ≥0.8; O14 recompute severe under different oracle sets). No hand-waving found. Minor: O14's "several plausible oracle sets" would be stronger with a specified set list, but it is an experiment; O10's "may leave gaps" is exactly the C7 ambiguity above, so resolving O10 is a prerequisite for C7. No change demanded.

### Cross-reference and consistency defects (S3/S4)

**S3 (ambiguity/unbuildable detail):**
- **F27 – `content_class` is defined twice.** §13.1 makes `content_class` an input-only feature computed from the known band (aliased to `feat_content_class`), while A5/A6 class stratification and §7.1 class weights need the GT-derived `label_content_class`; §7.2 lists `content_class` without saying which. State that all class-stratified *scoring* uses `label_content_class` and gates use `content_class`; keep the alias mapping explicit.
- **F29 – Cross-references:** §1 C6 L101 "scores the clamp seam (D4)" — clamp seam is D6; C19 L127 "D2–D5" omits D6; §3.3 L334 "validity under §3.5" — validity is §3.4; §2.7 L248 and §7.7 L899 "feature namespace §13.2" — features are §13.1/B.4; §11.5 manifest list omits `synthetic_manifest.json`/`lite.json`; `reproduce.sh` vs `REPRODUCE.md`.
- **F30 – Threshold conflicts:** C3 failure >3.0 vs A6's `C1 > 3.0` (different metrics but easy to misread; clarify which fires AF); R4 allows C3 ≤3.78 while C3 fails >3.0; A6's per-tile flag rate uses a "per tile" column header; D2's conditional ">0 unless D6 passes" vs D4's ">8 levels" overlap without a decision rule.
- **F31 – Units of B1/B2/B9:** the metrics are defined on STOP edges (§4.2) and §7.3 makes edges their unit, but §4.0 says "thresholds are per tile"; make the row headers per-edge or state the aggregation.
- **F33 – §0 capability table stale ID ranges:** A1–A6 (A7 exists), B1–B8 (B9 exists), D1 gate, D2–D5 (D6 exists), F1–F5 (F6 exists), J1–J4 (J5 exists). Update the summary table to A1–A7, B1–B9, D1–D6, F1–F6, J1–J5.
- **F25 – Generator completeness:** no parameter distributions for Photo/Clipped/Mixed; spot recipe-table format undefined; "40 px safety margin" purpose undefined; acceptance test (vii) tolerance undefined; crop marks in the *mix* (§3.1) but not a *primitive* (L290–L299) and declared out of scope (§2.7) — circular. Buildability fails until these are specified.
- **F15 – Manifest volumes for T4** as above.
- **F23 – F injection protocol:** "injecting controlled defects … never changes the page's GT ring except by the declared injection" does not say how input/known/unknown/GT are re-aligned when the trim box moves outward/inward, how MAE_δ denominators are defined per δ, or what "output ink share" (F2) and `paper_share` (F5) are. F metrics are not computable from the description as written.
- **F41 – §3.1 acceptance test (vii)** "matches within tolerance" — give the numeric tolerance.
- **F42 – §3.1 "10% of pages visually inspected"** — no pass/fail criterion for render defects; acceptable as a QA step but state the rule (e.g. any mismatch re-renders).
- **F24 – Spot floor:** §2.8 table promises a spot round-trip floor measured with `roundtrip_spot_gt`, but no such quantity/baseline/metric is defined and E7 subtracts nothing; either define `roundtrip_spot_gt` like `roundtrip_gt` (E5) or state that spot pages have no floor and why.

**S4 (style/judgement):**
- **F28 – formatting:** missing blank line before `## 7. Aggregation` (L829–L830); the duplicate §10.6 heading from the earlier revision was removed in the current one.
- **F34** v1 trim-error MAE quoted as 12.5 in §4.6 (F1 rationale) vs 11.50 in Appendix B.5; state that 12.5 is the trim-error subset mean, not the dev mean (7× claim 12.5→88 = 7.04× ✓).
- **F35** §0 "every interval is a family-cluster bootstrap" vs the exact Clopper–Pearson bounds used for gates (§10.1 says both are reported); reword "every interval is a family-cluster bootstrap **or an exact one-sided bound where zero events**".
- **F36** O14's "several plausible oracle sets" could name the sets; otherwise fine.
- **F37** T5 page categories overlap (rich black ⊂ CMYK, near-white ⊂ CMYK); state nesting so page totals/cost are not double-counted.
- **F38** §9.2 "edge_repeat not the best non-learned method on flat" — the expected ranges overlap (`edge_repeat` 0.0–0.5 vs `stretch` 0–1), so the ordering check is not crisp; state the tie rule.
- **F39** A6's "flat >1.5; gradient >5.0; structure >25; texture >45 (provisional)" — the values are provisional by design (frozen at calibration) and the checklist allows numeric provisional values, but the text should say which are *class MAE* versus *p90* in A5 (the row is named "Class MAE + p90").
- **F40** B6's `gt_copy` baseline is 5% (judge FPR), not near-perfect; acceptable as a calibrated baseline, but label the column "calibrated baseline" for B6 rather than "near-perfect".
- **F43** E5's `floor = E5(roundtrip_gt)` is circular in notation; write "floor = mean dE00 of the GT-roundtrip strip under the same pipeline".

### Checklist §E numerical checks (recomputation record)

| Check | Expected / recomputed | SPEC value | Result |
|---|---|---|---|
| 0.125 in ×300 DPI | 37.5 → 38 px | 38 (`ceil`) | ✓ |
| 5 mm at 300 DPI | 59.055 → 60 px | 60 | ✓ |
| 0.125 in at 150 DPI | 18.75 → 19 px | 19 | ✓ |
| 0.125 in at 600 DPI | 75 px | 75 | ✓ |
| `a=(−b) mod 16` | 10, 4, 13, 5 for b=38/60/19/75 | 10/4/13/5 | ✓ |
| `B=b+a` | 48/64/32/80 | 48/64/32/80 | ✓ |
| tile known band 512−B / 1024−B | 464/976; 448/960; 480/992; 432/944 | same | ✓ |
| v1 pages | 124 − (10+33+1) = 80 usable; 44 dropped (35.5%) | 124/80 used, 27% short-bleed | ✓ (27% = 33/124; total attrition 35.5% not stated) |
| 179+280+37 | 496 gold edges | 496 | ✓ |
| 1,730 dev tiles | 384+384+372+360+230 | 1,730 | ✓ |
| 0/11, 0/48, 0/80, 0/299, 0/300 bounds | 23.8%, 6.05%, 3.68%, 1.00%, 0.995% | 23.8/6.05/3.68/1.00/1.0 | ✓ |
| 3.35% ±1 pp | n = 0.0335×0.9665×(1.96/0.01)² = 1,244 | 1,244 | ✓ |
| 3% ±1 pp | 1,118 | 1,118 | ✓ |
| ±0.5 pp | 4,976 | 4,976 | ✓ |
| 1% vs 2% / 2% vs 3% / 3.35% vs 4.35% (80% power) | 2,315 / 3,822 / 5,808 per group | 2,319 / 3,826 / 5,810 | ✓ (rounding) |
| 300×0.95 vs 1,244 | 1,235 < 1,244; need 1,309 | states 1,300 after 5% attrition | ✗ (F19) |
| Synthetic pages | 320 quiet + 320 fill; 185+93+32+8+2=320; 829+451=1,280 | same | ✓ sums, derivation issue (#7) |
| 640×4 edges | 2,560 | 2,560 | ✓ |
| 28 tiles/page | 24+4=28; 160×28×4=17,920; 25% 1024 subset; lite 4,480 | same | ✓ |
| Corner tiles | 4×640=2,560; 4×300=1,200; 4×1,300=5,200 | same | ✓ |
| Analytic gradient MAE | mean_{d=1..38} s·d = 19.5·s | 19.5·s | ✓ |
| sd_refine cost ratio | ~1,300 ms / 0.5 ms = 2,600× | ~2,600× | ✓ |
| R1 margin | 45.96−44.29 = 1.67 | 1.67 | ✓ arithmetic (source missing) |
| Oracle headroom | 11.50−9.00=2.50; 11.50−8.58=2.92 | 2.5–2.9 | ✓ |
| SCS at allowed tolerance | offset 1 px → 0.779; colour 1.0 → 0.779; width 1.2 → 0.763 | C4 must be ≥0.80 | ✗ (F9) |
| Human study hours | 3×75 min = 3.75 h | ~4.5 h | ✗ (F32) |
| 48/38−1 apron overhead | 26.3% | 26% | ✓ |
| 28×100 ms | 2.8 s > H2 1.5 s/page | contradictory caps | ✗ (F16) |

## Checks performed

- [x] Read `docs/review-checklist.md` and `SPEC.md` in full; audited revision `356DCEFA…` and re-checked the current revision `E934DF31…` (two small edits: §9.4 v1-derived-targets note; duplicate §10.6 heading removed). No edits to SPEC/README/other reviews.
- [x] §A structure A1–A15: all sections present and in demanded order; no missing/merged sections; noted stale ID ranges in §0 and the §7 heading spacing.
- [x] §B ten axes A–J: confirmed each axis is separately scored; checked every required sub-item (A fidelity; B restraint; C seam; D known-pixel; E dE/flat/near-white/rich-black/CMYK/spot/wide gamut; F trim 1/2/4 + crop marks 0/9/38 + partial; G seeds/reruns/orientation/batch; H quiet/GPU/batch/gain; I 38/60/19, 512/1024, whole page; J corners separate) and flagged E wide-gamut and F crop-mark/δ=1 gaps.
- [x] §C built the full per-metric matrix (63 rows); marked every field present/partial/missing; tallied 45/63 rows with at least one defect and 8 wholly missing elements; listed undefined baselines.
- [x] §D checked all 13 hard constraints/do-nots against sections; all satisfied (mapping table above); noted D6/D2 overlaps and content-class naming as S3.
- [x] Data tiers: three tiers, purposes, generator primitives/mix/counts/validity/licence/targets/families; recomputed mix and page/edge counts; verified V3 pale-tint rule and V6 audit; checked drop-rate (27% = 33/124) and bimodality (179+280+37=496) and flagged the 33-page/179-edge/80-page/496-edge reconciliation gap.
- [x] Tracks T0–T9 and required-entry rules; verified T1 tile arithmetic (17,920), lite 4,480, T4/T5/T3 manifest issues.
- [x] Statistics: bootstrap B=1,000, stratification, paired deltas, ICC/neff; exact zero-event bounds table (all 10 rows); CI half-widths and two-proportion sizes; multiplicity (Holm, four primaries); minimum-sample table (flagged arithmetic).
- [x] Reproducibility: seeds, hashes, hardware/quiet protocol, determinism rerun, manifests; checked §11.5 list completeness and `reproduce.sh`/`REPRODUCE.md` inconsistency.
- [x] Human study: 40 stimuli, 300 pairs/rater×3, print-size display, seam guide, Bradley–Terry, α, power; flagged total-judgment ambiguity, 4.5 h vs 3.75 h, print-size/PPI detail.
- [x] Leaderboard: line-by-line CSV superset check against the 22 v1 columns (all present incl. aliases); aggregate JSON; DQ1–DQ14; flagged `page_mae`/`system_mae` undefined and gate-threshold/confidence contradictions.
- [x] Numbers to beat R1–R8: mapped all five v1 conditions + oracle headroom + cost; verified 44.29/45.96→1.67, 2.5–2.9 headroom, 2,600× cost; flagged R6 undefined `SystemGain_headroom`, R2 unit/n, R4 C3 conflict, R1 sourcing.
- [x] Open questions O1–O14: each has an experiment and a resulting change; no hand-waving found (O14 wording only).
- [x] Recomputed geometry, v1 arithmetic, exact bounds, sample sizes, mix, tile counts, baseline order and cost ratio (record table above).

---

## Post-fix verification (current revision)

Audited `SPEC.md` SHA-256 `B015B2747D79146C6489FF6325A036C0B69078631760F93E9A5652E3EC28F2EA` (1,554 lines), the revision saved at 01:05 after the Lead's post-S1 fixes. This was a targeted verification (structure, F/E, flagged metric rows, CSV, R1–R8, open questions), not a full re-review; the top-10 and detailed notes above remain the record of the earlier revision.

### S1 status (earlier top findings)

| Earlier # | S1 | Status | Evidence in current revision |
|---|---|---|---|
| 1 | SystemGain three definitions | **PASS — fixed** | §0 L43–L46 and §7.6 L936–L946 define one page-level `SystemGain` using `page_fidelity` (q90 of tile MAE) and page weights; `MAE_page` is explicitly `page_fidelity` (§7.6 L946); §7.4 L926 reserves `page_safety` for the private page acceptance set/reporting, explicitly not Gate A/B; no tile-weighted variant remains. |
| 2 | F crop marks 0/9/38 + δ=1 threshold + scope | **PASS — fixed** | F3 L616–L617 defines offsets `{0,9,38} px`, mark = 0.25 pt 100% K full-edge; per-offset threshold >0.01 L629; F1 δ=1 threshold >1.25 L627; F6 δ=1 >1.5 L632; 200-page/40-family robustness manifest L610; T4 L991 = 760 variants (600 trim + 120 crop + 40 partial); V5-vs-F3 scope separated L640 and §2.7 L258; baselines `trim_aware_fill`/`mark_filter`/`paper_oracle` defined as reference implementations L634. |
| 3 | Wide-gamut unoperationalised | **PASS — fixed** | Adobe RGB 5% in the Tier A mix L330; §3.6 wide-gamut row 32/15/65 L410; T5 L992 adds 20 Adobe RGB test pages; E6 is now `gamut_handling` against a declared GT map (L600) and E1/E2 are computed on Adobe RGB pages with a measured floor (L606, §2.8 L269/L276). |
| 4 | C4/SCS no-line contradiction + scale mismatch | **PASS — fixed** | C4 L532 is a binary pass with `n/a` when no line reaches the seam; per-line tolerances are the operative rule, old `SCS < 0.80` withdrawn, `SCS < 0.20` now the catastrophic bound (§6.4 L872); `SCS = 1.0` by convention but C4 `n/a` on line-free tiles; §9.3 L1064 self-test now says "C4 = n/a (no known line)"; §4.3 L540 explains. |
| 5 | Page-level 1% certification conflict | **PASS — fixed** | §3.3 L352: 350-page/120-family acceptance set, `DE_page = 1.11` → 315 effective accepted pages, zero-event 95% UB 0.95%; §7.6 L950 states 299×DE_page ≈ 332 accepted pages; §10.2 L1136–L1139 and §10.3 L1150 add the 703/210/332/350 rows and the 18-page rejection headroom. |
| 6 | T3 unbuildable against 160-page test split | **PASS — fixed** | T3 L990 now = all NO_INK/STOP edges of the 160-page test split (≈80 quiet + STOP edges on 80 inked pages) + 200 strips, with L998 confirming the 200 are a subset of the 1,200-strip validation set. |
| 7 | Synthetic mix not derivable | **PASS with residual (S4)** | Conditional FULL/STOP probabilities are now stated per material L323–L327 and page counts are explained L332 (single-material fill pages, 4 edges/page). Residual ±1 rounding: direct computation from the conditionals gives FULL = 0.5·740 + 0.8·372 + 1.0·128 + 0.9·32 + 0.5·8 = **828.4** and STOP = 0.5·740 + 0.2·372 + 0.1·32 + 0.5·8 = **451.6** (→ 828/452), while the quoted 829/451 comes from rounding 32.4%/17.6% of 2,560 (=829.44/450.56). Pin exact integers in `synthetic_manifest.json` and derive the shares from them. |
| 8 | Detector families / validation-set counts | **PASS with residual (S3)** | C9 L110 now says "four independent detector families … plus a GT-support metric"; §5.4 L775–L782 defines the 1,200-strip set as 400 GT positives + 400 injected + 400 model negatives with the 200 ambiguous strips a *subset*, not additive; FPR calibration uses a separate 2,000-strip set (L765); T3 uses a 200 subset (L998); DD40 says 1,200 (L1460). Residual: §5.1 L735 says "The four families…" but its table still lists F5 GT-support as a fifth row; move F5 out of that table or label it "not a detector family". |
| 9 | SCS scale vs per-line tolerances | **PASS — fixed** | §6.4 L872: per-line tolerances (3°, 2 px, width 0.75–1.33, dE 2.0) are the pass rule; SCS is a continuous ranking score; `SCS < 0.20` is catastrophic; the contradictory 0.80 cut is withdrawn. |
| 10 | Per-metric seven-field matrix | **SUBSTANTIALLY FIXED (S3 residuals)** | A7 formula added (L452); A5b p90 formula added; B5 is now `1000·detections/tiles − FPR` (L484) with per-1,000-tile threshold; D3 denominator `K_seam2` defined (L550); F2/F3/F4/F5 terms (`ink_share`, `mark_*`, classify, `paper_share`) defined (L615–L621); I ratios have a "1 if both 0" convention (L693–L698); G2/G3 include the severe/dE variants and G4 a 1e-6 tolerance (L648–L653); H2 page-runtime caps fixed (L681); J1 has a dE threshold (L719); C7/C8 have a 50%-overlap subset and a defined composite (L165, L540). Residuals: A6 `AF(tile)` binary vs aggregate-rate naming; E2 baseline `recipe_match` still undefined; new E3 symbol `roundtrip_floor_richblack` not explicitly defined; B1/B2 edge-level under §4.0's "per tile" header; H4 still merges VRAM/load/throughput; `line_coverage`/`text_coverage`, `paper_source`/`paper_confidence` and D1b are reported in prose but absent from the CSV; `match_rate`/per-line errors remain report-only rows. These match the residual S2/S3 items acknowledged in the revision's "Audit status" (L5). |

### A1–A15 structure

All required sections exist and remain in the demanded order **except**: the `## 7. Aggregation` heading is missing. §6.5 ends at L883, lines 884–885 are blank, and the next heading is `### 7.1 Units and weights` (L886); the TOC entry `7. [Aggregation](#7-aggregation)` (L22) therefore has no target. The content §7.1–§7.9 is intact and correctly ordered. **Action: restore `## 7. Aggregation` before L886** (one line); this is an S2 structural regression, not a content gap. Everything else (A1 ¶0, A2 §1, A3 §2, A4 §3, A5 §4, A6 §5, A7 §6, A9 §8, A10 §9, A11 §10, A12 §11, A13 §12, A14 §13, A15 §14 + appendices) is present and ordered.

### Axes E and F

- **F: PASS.** Required sub-items are now complete: outward trim δ=1/2/4 (F1 thresholds 1.25/1.5/3.0), inward δ=1/2 (F6), crop marks at 0/9/38 px with per-offset thresholds (F3), partial hidden bleed (F4), plus F2/F5. Manifest/T4 arithmetic checks: 200 pages = 120 trim + 40 crop + 40 partial; 760 variants = 600 + 120 + 40. The mark geometry and baseline references are defined.
- **E: PASS.** dE (E1), flat drift (E2), near-white two-sided (E4), rich-black net of a floor (E3), CMYK round-trip with floor (E5), spot with floor (E7), wide gamut via E6 + Adobe RGB pages and measured floor (§4.5 L606, §2.8 L269/L276). Residual: E2's `recipe_match` and E3's `roundtrip_floor_richblack` are not defined as reference implementations/baselines — add them to §9.1 or `expected_baselines.json`.

### CSV superset, R1–R8, open questions

- **CSV superset: PASS.** The normative header (L1275–L1292) still contains all 22 v1 columns, including `grad_mean`, `color_var`, `edge_density`, `near_white`, `near_white`→`gt_near_white` aliases and `content_class`; `page_mae`/`system_mae` are now defined at L1308. Residual (S3/S4): newly reported quantities `line_coverage`, `text_coverage`, `paper_source`, `paper_confidence` and D1b have no CSV columns.
- **R1–R8: PASS with minor sourcing (S4).** R6 now defines `HeadroomGain` as an explicit sum with a family CI (L1089), replacing the undefined `SystemGain_headroom`; R3/R4 are now against v2 edge repeat with v1 placeholders (L1086–L1095); R2 unit = flat tiles (L1085); R8 `B1 = 0` matches the new any-ink B1 threshold. Residual: R1's 44.29/45.96 still appear only in the R1 row, not in any table; R2's required n for a 5%-UB claim is not in §10.4.
- **Open questions: PASS.** O1–O14 all still carry an experiment and a consequence; O3 (PPV(0.05) + CP lower bound), O5 (two ICCs) and O13 are updated consistently.

### Remaining gaps after post-fix verification

- **S2 — missing §7 heading** (above): restore before freeze.
- **S3/S4 — mixture:** conditional FULL/STOP counts give 828.4/451.6 (828/452) not 829/451; pin exact integers. Also "5% realism subset" (L332) is not defined in the special-page mix.
- **S3 — texture split allocation:** §3.6 L408 allocates the 32 texture pages 8 cal / 8 val / 16 test; calibration is 8/320 = 2.5% versus the 5% census, which fails §3.1 acceptance test (ii) "population class balance per split within ±20% relative". Suggest 16/8/8 population + 8 declared test supplements (= 16/8/16), or equivalent.
- **S3 — T5 Adobe RGB count:** T5 asks for 20 Adobe RGB test pages, but §3.6 has 8 test pages at 5% of 160; state whether 12 are synthetic supplements (like spot/rich-black) and keep them out of the census counts.
- **S3 — T1 "25% at 1024":** table L988 says 25% at 1024, but detail L998 gives 3,200 tile-runs = 17.9% of 17,920 (40 of 160 pages = 25% of pages). Say "25% of pages" or raise the subset.
- **S3 — §3.3 "up to 43 of the 44":** the following clause enumerates 10+33+1 = 44 recoverable pages; reconcile 43 vs 44.
- **S3 — §5.1:** five table rows under "four families" (F5 GT-support); either list F5 outside the table or relabel.
- **S3 — metric residue:** undefined E2/E3 baselines (`recipe_match`, `roundtrip_floor_richblack`); A6 binary-vs-rate; B1/B2 edge units; H4 merged row; missing CSV columns for line/text coverage, paper source/confidence, D1b.
- **S4 — R1/R2 sourcing** as above; CP-DE approximation is explicitly labelled and acknowledged (L5, §7.7 step 3) — acceptable residual.

**Post-fix verdict: PASS on all substantive S1 findings (7/7 fixed), with the missing `## 7. Aggregation` heading as the one structural regression to restore, plus the S3/S4 residuals listed above. Overall remains PASS WITH FIXES; not freeze-blocking except the §7 heading and the texture-split/class-balance inconsistency.**
