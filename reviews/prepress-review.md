# prepress-auditor review — bleedBENCH v2.0

**Verdict: FAIL**

Audited snapshot: `SPEC.md` sha256 `d65746398c9585d0c5e0e7b95f1d04d4ff7f5b581adebde657b44305757410a0`
(1,481 lines; `LastWriteTime` 2026-11-01 00:42:32 local). `SPEC.md` was being edited *during* this audit
(139,713 → 143,721 chars across the session); line numbers below are from the snapshot above and should be
re-located by section heading if the file has moved. Section numbers are authoritative.

The document is well above the bar in structure and honesty, and most of the arithmetic in §2.3, §9.3 and §10.2
recomputes exactly. It fails as a protocol-freeze candidate for six concrete reasons: one normative geometry
claim is mathematically wrong (§2.3/DD4), one metric is defined so that the near-perfect baseline fails it
(C4/SCS), one validation-set count contradicts itself by 800 strips (§5.4 vs §12.3/O3), the human study cannot
produce the acceptance labels its own threshold calibration requires (§12), B5's formula and threshold differ by
1000×, and §0 and §7.6 define the headline in different units. All are locally fixable; none requires redesign.

**Revision note (post-audit).** `SPEC.md` was edited again after this audit; current head at re-check was sha256
`a1a7e68ff15f27dd248d417a431855cc013b2918cb9718d17583e594282658af` (1,481 lines, 00:50:52). Two findings in this
review were **fixed at that revision** and can be closed: #6 (§10.2 two-proportion 3.35% vs 4.35% is now
**5,810**, and 2,319/3,826 are within rounding of 2,316/3,822) and #30 (§3.1 now reads 185 photo pages and 1,280
inked edges / ~829 FULL / ~451 STOP, which closes the 641-page and 2,564-edge slips; remaining nit: 829+451=1,280
is now consistent). The other findings I re-checked at `a1a7e68` were still present: #1 (L182/DD4), #2 (L812,
C4 row L510), #3 (§5.4 table vs §12.3 L1190/O3/DD40), #5 (B5 L465), #7 (§0 L42 vs §7.6 L885), #8 (E6 L560),
#12 (A2 L441 vs E1 L567; R4 L1023), #14 (I1/I2 L652–653), #15 (§2.8 L257), #17 (E4 L558), #18–19 (§12.2–12.3
L1178–1190), #20 (§9.2 L973/L987, BL11 L963), #25 (§2.6 L236–240), #26–28 (D3/R_composited/F3–F5 L527/L502/
L585–587), #31 (no MediaBox line in the spec; renderer L1442), #32 (B1/B2/B9 rows). Line numbers are therefore
the ones at `a1a7e68` for those items.

## Top findings (severity order)

| # | Severity | Location | Finding | Evidence / recomputation | One-line fix |
|---|---|---|---|---|---|
| 1 | **S1** | §2.3 (L175–182), DD4 (L1351) | `δx = (−W) mod 16` added to the **right margin** makes the *canvas* a multiple of 16, but does **not** move the right/bottom **trim seam**; that seam stays at `x = B + W`. So "the right/bottom seams also land on the 16 grid" is false, and the whole-page claim "no trim pixel shares a latent cell with an unknown pixel" (L171, L234) is false for any page whose trim width is not a multiple of 16. | US Letter 8.5 in @300 → W=2550, δx=10, canvas=2656 (÷16 ✓), but right seam = 48+2550 = **2598 ≡ 6 (mod 16)** → the L=16 latent cell [2592,2607] contains 6 known trim columns and 10 unknown columns. A4 landscape/300 (W=2480, W%16=0) is a lucky case; arbitrary pages are not. Consequence: `regen_trim_px > 0` for declared L≤16 on every compliant model → D5 (L540) false-fails, and the "26% more strip" (L173) becomes up to 66% on the right/bottom band (63/38). | Either crop/offset the known interior by δ so the *seam* is on-grid, or restrict the alignment claim to left/top and route the right/bottom offset through D5/D6 explicitly. |
| 2 | **S1** | §6.4 (L812), §4.3 C4 (L510), §7.4 (L863), §9.3 (L1002), J3 (L680) | `SCS = … (0 if no known lines reach the seam)` makes any line-free tile score 0, so C4's `<0.80` failure fires on every flat/photo/texture tile. This contradicts (a) C4's own sanity baseline `gt_copy = 1.0`, (b) the §9.3 exact self-test "Solid page, `gt_copy` … C4 = 1.0", (c) §7.4 `page_safety`, which treats "C4/C5 structural failure" as a page-safety event (every page becomes unsafe), and (d) J3 `min(SCS_h, SCS_v)` (every line-free corner fails). | A solid page has no known lines → SCS=0 by the formula → C4 fails; the same §9.3 row asserts C4=1.0. Most of the 2560 real edges are image/flat, not rules. | Define `SCS = 1.0` (or `n/a`, excluded from pass/fail) when no known line reaches the seam, and compute C4 only on tiles with ≥1 known line. |
| 3 | **S1** | §5.4 table (L736–741) vs §12.3 (L1190), O3 (L1316), DD40 (L1387) | Hallucination validation set is defined as 600 GT + 600 injected + 600 model + 200 ambiguous = **2,000** strips, but §12.3/O3/DD40 all call it a **1,200**-strip set. | 600+600+600+200 = 2,000 vs "separate 1,200-strip set" and "the 1,200-strip human-labelled set". A 2,000-strip × 3-annotator set is also ~3–5× the annotation burden implied by "cheap, repeated" §12. | Pick one size and one table; state which components the "1,200" count covers. |
| 4 | **S1** | §12.1 (L1174), §12.3 (L1189) | The study is claimed to calibrate A6/B1 thresholds by "logistic regression of accept on A1/A2/B1", but the §12.2 protocol never collects an accept/reject label: the rater task is "choose the better strip" plus an optional defect category. Preference data cannot fit an accept model. | §12.2 task (L1181) = pairwise choice; no per-strip accept/reject, no "neither acceptable" option. §12.3 L1189 needs an accept response variable that does not exist in the design. | Add an explicit 3-way accept / reject / unsure judgment per strip (or per pair: "both acceptable / more / less"), and fit the threshold model on that. |
| 5 | **S1** | §4.2 B5 (L465, L478) | B5's formula is per **tile** (`hits / #tiles`, range "[count]") while its range and failure threshold are per **1,000 tiles** (">1 per 1,000 tiles"). Implemented literally, B5=1.5 means 1.5 hits *per tile* (absurdly lax); implemented as intended, the formula needs a ×1000 factor. | `B5 = (# detections)/ (# tiles)` has range 0–∞ per tile. Threshold ">1 per 1,000 tiles" = 0.001. The two cannot both be true of the same number. A 17,920-tile T1 manifest fails at >17.9 hits even with ≥99.9% detector specificity. | `B5 = 1000 · hits / #tiles`, and set the threshold from measured detector precision on the human set, as B6 does (a bare count threshold is not a validated gate). |
| 6 | **S1** | §10.2 (L1075) | Two-proportion sample size for 3.35% vs 4.35% is stated as **3,048** per group; the correct 80%-power, two-sided-5% figure is **5,807** per group. (1% vs 2% → 2,315 not 2,319; 2% vs 3% → 3,822 not 3,826; both rounding-level.) | n = (1.96+0.8416)²·[p₁(1−p₁)+p₂(1−p₂)]/(p₁−p₂)² = 7.849·0.07399/0.0001 = 5,807. The stated 3,048 is ~half the correct value. This row is cited as the reason the benchmark "does not claim to detect 1 pp differences", so the error is load-bearing. | Replace 3,048 with 5,807 (and 2,319/3,826 with 2,316/3,822 if exact rounding is wanted). |
| 7 | **S1** | §0 (L42–44) vs §7.6 (L882–887) and §7.4 (L870) | The headline is defined twice in different units: §0 `SystemGain = mean over test pages of [MAE_page(M_ref) − MAE_page(M_system)]` and gate on "accepted-**page** severe rate ≤1%"; §7.6 `SystemGain = Σ_t w_t·[MAE_edgeRepeat(t)−MAE_system(t)]/Σw_t` over **tiles** and Gate A/B on accepted-**tile** severe; §7.4 says `page_fidelity` "is the continuous quantity used for SystemGain". Three definitions, one number. | Page vs tile means differ by the 3–6× mean/median gap the document itself cites (§7.4 L860); the gate's exact bound has different n (299 pages vs 299 tiles) and different clustering. | Define SystemGain once (recommend page-level, per §0) and state that the gate is tile-level with a page-level acceptance check; delete the other two phrasings. |
| 8 | **S2** | §4.5 E6 (L560, L572) | `gamut_clip_rate = |{p ∈ U : G_page(p) outside model-space gamut}| / |U|` is computed **from GT only**, so it is a page property identical for every method and cannot score a model. The sanity baseline "`roundtrip_gt` = floor" is meaningless because gt_copy has the same value. | No R appears in the formula. Every entry sees the same E6 per page; it can never "fail" a submission for anything the submission did. | Score the model's *handling* of out-of-gamut GT pixels (clipping error / dE on that subset) or demote E6 to a page covariate reported in the manifest. |
| 9 | **S2** | §4.2 B3/B4/B5 (L476–478), C6 (L512), §4.0 (L410) | For no-GT detectors, the sanity baseline "`gt_copy` = 0" is not plausible and conflicts with §4.0's rule that a metric whose gt_copy is not ideal is a harness bug. A continuation prior/OCR/object detector run on GT strips has a nonzero FPR by construction (the prior cannot predict texture edges that do not extend from the known band; OCR fires on noise/patterns; detectors have false positives). Only B6 handles this correctly (baseline = judge FPR, calibrated 5%). | §5.3 L724 explicitly says the prior's "false-positive rate on real GT strips is low" — low, not zero. Thresholds are 20/10⁴ px (flat) and 100/10⁴ overall; a 1.5% FPR = 150/10⁴ already exceeds the overall threshold, so gt_copy would fail its own baseline. | For B3/B4/B5/C6, define the near-perfect baseline as the *measured detector FPR on GT* (frozen), report net = raw − FPR, and require a GT FPR calibration run at freeze. |
| 10 | **S2** | §5.4 (L734–754), §5.3 F4 (L730) | The human-label validation is not sound as specified: (a) the validation set is prevalence-enriched (600 injected positives of ~2,000 = 30% invented content vs a deployment prevalence that is much lower), and a **precision ≥0.90** target is prevalence-dependent — PPV at 30% prevalence is not PPV at production prevalence; (b) the judge's training negatives are "outputs from ≥5 baseline methods", i.e. the same methods that supply the human-labelled "model negatives", so the precision estimate is contaminated by train/test overlap; (c) leave-one-generator-out is not defined for a *submission* whose generator family was never in the judge's held-out set. | §5.4 requires precision ≥0.90 and AUROC ≥0.85 "on the frozen set" but never states the prevalence at which precision is measured. §5.3 F4 negatives (c) = baseline model outputs; §5.4 model negatives = outputs from ≥5 baseline methods. Same sources. | State operating prevalence, report PPV at that prevalence (plus specificity/FPR), validate on generators held out from judge training, and define the advisory fallback for unseen generators. |
| 11 | **S2** | §4.5 E3 (L557, L569), §2.8 (L257) | E3 rich-black error has no round-trip floor (unlike E5) and no aggregation rule for `ΔCMY`; with the default sRGB proxy, black generation is not invertible, so even a perfect copy of a rich black has a large ΔK/ΔTAC floor and an RGB-proxy entry can never pass `abs ΔK > 2%`. Separately, §2.8's Adobe RGB row states round-trip floor 0, which is only true if the model space is Adobe RGB; under the default sRGB proxy, wide-gamut Adobe RGB content is clipped and the floor is nonzero. | §2.8: "with naive sRGB conversion the seam error on a colorimetric model is up to 15 dE00; with recipe matching it is under 1" — the same argument applies to ΔK/TAC. A GT rich black C60M40Y40K100 (240% TAC) through sRGB→CMYK will generally return a different recipe. | Floor E3 with `roundtrip_gt` exactly as E5; define ΔCMY as a scalar (e.g. max |Δc| or ink-vector L2); make the Adobe RGB floor "0 only if model space = Adobe RGB, else measured". |
| 12 | **S2** | §4.3 C3 (L509), §9.4 R4 (L1023), A6 (L448), B8/A6 | Thresholds for the same quantity disagree across tables: C1 fails at >2.0 but A6 fires at C1 > 3.0; C3 fails at >3.0 but R4 accepts C3 ≤ 3.78 — and edge_repeat, the primary reference, is at BGE 3.78, i.e. the reference baseline fails C3's own pass rule; A2 flat fails at dE > 2.0 but E1 (the same mean page-space ΔE00 by §4.0) fails at >2.5 flat; B8 fails at >2 levels while A6 fails a flat tile at A1 > 1.5 (A1 ≥ |mean drift| = B8, so A6 is strictly stricter than the dedicated flat-drift metric). | Recompute: edge_repeat BGE 3.78 > C3 threshold 3.0 (Appendix B.5 L1457 vs §4.3 L509). Two thresholds for one quantity cannot both be normative. | Pick one canonical threshold per quantity, derive A6 and R4 from the §4 table, and let the reference baseline pass its own metrics. |
| 13 | **S2** | §4.8 H1 (L639) vs H2 (L640) | H1 permits ≤100 ms/tile, but H2 requires <1.5 s/page and defines page_runtime as "Σ runtime of the page's 28 tiles + assembly". 28 × 100 ms = **2.8 s**, so a model that satisfies H1 and H2's own tile count fails H2 by 1.9×. (Also at 1024 the page has 4·4+4 = 20 tiles, not 28.) | 28×0.100 = 2.8 s > 1.5 s. §8's badge text (L938) also uses H1 ≤ 100 ms as the cap. | Set H2 ≤ 28·H1 + assembly (e.g. ≤3.5 s at 512), and state the per-size tile count (28 at 512, 20 at 1024). |
| 14 | **S2** | §4.9 I1/I2 (L652–653), I6 (L657) | Sanity baseline "`gt_copy` ≈ 1.0" (I1/I2) and "= 0" (I6) are undefined because gt_copy has MAE = 0 at both widths, so `MAE(60)/MAE(38)` is 0/0 and `MAE(long)/MAE(normal) − 1` is 0/0. A harness following §4.0 would flag the correct harness as buggy. | 0/0 ≠ 1.0. I6 similarly 0/0. | Define the ratio as 1.0 (I6: 0) when both numerator and denominator are zero, or use `(n+ε)/(d+ε)`. |
| 15 | **S2** | §2.8 (L250–264), §4.0 (L406) | ΔE00 is computed in "page space" with sRGB→Lab **D65** but CMYK/spot→Lab via the ICC, whose PCS is **D50**. Comparing a D65 Lab with a D50 Lab in one ΔE00 without a declared chromatic adaptation (Bradford/CAT02) injects a white-point cast — precisely on the E1/E5/C2 metrics whose thresholds are 1.0–4.0 dE00. | ICC PCS = D50 by specification; sRGB is a D65 space. §2.8/B.2 never state the adaptation or a common reference white. | Declare one Lab reference white and adaptation for all page-space conversions (recommend ICC PCS D50 via Bradford), and compute all ΔE00 on that. |
| 16 | **S2** | §3.4 V2 (L346), V3/V4 (L348–357) | Paper colour is estimated, in order, from: declared background; **the mode of the outermost 2 px of the GT ring**; the brightest 5% of the known trim band. On a full-bleed page the outermost ring is *artwork*, so the mode is an artwork colour; the V3 ink test and V4 depth are then measured against the wrong "paper", flipping FULL pages to STOP/AMBIGUOUS. | For a photo that fills the bleed, the outermost 2 px are photo content (e.g. dark). ΔE00(pixel, "paper") then classifies most artwork as paper → `d(x)` collapses → `D_e ≤ 1` → STOP. This is the exact v1 failure mode v2 claims to fix. | Use ring-based estimation only when the ring is uniform/near-paper (NO_INK/STOP candidates); otherwise require the declared background or an in-trim paper region, and record `paper_estimate_source` + confidence. |
| 17 | **S2** | §4.5 E4 (L558, L570) | `near_white_leak` is one-sided (counts only `L*(R) < L*_paper − 2`): a model that paints **whiter than paper** (255 where paper is 245, or neutral white where paper is cream) produces a visible white halo and scores 0. Also, if "near-white GT edges" contain tints darker than paper−2, a perfect `gt_copy` scores >0, contradicting `gt_copy = 0`. | One inequality; no lower/upper band. `gt_copy` = GT, so on a near-white tint with L* < paper−2, R=G counts as leak. | Use a two-sided band `|ΔE00(R,paper)| > 2` (or `L*` outside paper ± 2) on GT-paper regions, and state that GT must be paper-identical for this metric. |
| 18 | **S2** | §12.2 (L1178, L1182) | Print-size viewing is not achievable as written: at "100% zoom" a 300 DPI image on a ~100 PPI display is displayed at ~3× print size; at true print size a 38 px strip is 3.18 mm and a 1–2 px seam (0.085–0.17 mm) is sub-screen-pixel on any desktop display. D50 print appearance is also judged on a D65 sRGB display without a soft proof, and CMYK pages are shown as an sRGB proxy of out-of-gamut content. | 38 px / 300 DPI = 0.1267 in = 3.18 mm; 1 px = 0.085 mm. A 0.27 mm/px display (≈94 PPI) shows the whole strip as ~1.2 mm at true size — no 1 px defect is resolvable; at 100% zoom the strip is ~9.7 mm (3× print), exaggerating it. | Specify zoom = display_PPI / image_DPI (≈33% for print size) *and* require a 2–4× loupe view for 1 px scale; soft-proof CMYK through the page ICC; state that sub-0.1 mm defects are judged by loupe, not print-size view. |
| 19 | **S2** | §12.2–§12.3 (L1178, L1187–1189), §10.4 (L1097) | The study is underpowered for its claims: 40 strips split across four content classes ≈ 10 per class cannot calibrate class-conditional A6 thresholds; 300 pairs are clustered by page and rater (each page appears in many pairs), so the ±5.4 pp figure is optimistic (design effect >1); with 8–12 methods, 300 pairs gives only ~6.7 judgments per method pair, and the pairs are sampled "from method pairs whose automatic scores differ", which biases Bradley–Terry toward discriminability. | ±5.4 pp = 1.96·√(.65·.35/300) ✓ arithmetically, but assumed independent; 10 strips/class is far below the ≥30 pages/family floor the document itself imposes elsewhere (§7.5). | Either enlarge (≥1,000 pairs, same pairs rated by all 3 raters, pre-registered per-class ≥30 strips) or relabel the study exploratory and drop the threshold-calibration claim. |
| 20 | **S2** | §9.2 (L973, L987) | The 200-tile frozen check set cannot validate per-class expected ranges: at the census mix texture is 5% → ~10 texture tiles (and ~46 gradient, ~66 structure). A ±30% tolerance on a 10-tile texture MAE is not a reproduction check. Also the FLUX.1 Fill dev cost range 120–400 ms/tile at 512 is implausible for a 12B DiT at normal step counts (~1–4 s/tile on a 4090), which breaks the T1 0.5–10 GPU-h budget (17,920 × 0.25 s ≈ 1.2 h; ×2 s ≈ 10 h). | 200 tiles × 5% = 10. FLUX.1 Fill dev ≈12B params, ~20+ steps; 512² → ~1,024 tokens; published 1024² timings on a 4090 are single-digit seconds, so 512² is ~1–3 s, not 0.12–0.4 s. | Make the 200-tile check set stratified (≥40 tiles/class) or enlarge it; pin FLUX step count/variant and re-derive cost, and reconcile T1's budget with the measured number. |
| 21 | **S2** | §5.3 F1 (L724), §4.2 B3 (L463) | The structure-extension prior for B3 is not specified enough to implement, and §4.2/§5.3 disagree: §5.3 dilates the predicted field by 3 px, then B3's formula applies `dilate(E_exp, 3)` again (6 px tolerance); no Canny/LSD thresholds, structure-tensor window, or handling for edge tangents nearly parallel to the seam (which produce degenerate extensions); no calibrated GT FPR is given for the prior. | "detect edges with Canny/LSD" — no thresholds (contrast §6.2 gives Canny 20/60). "extend it … for b pixels" is undefined when the tangent does not cross the seam. | Specify one dilation, all thresholds/windows, a tangent-grazing rule, and the prior's measured GT FPR; make B3 net of that FPR. |
| 22 | **S2** | §6.4 (L810–822) | The per-line pass/fail tolerances and the tile-level SCS threshold are mutually inconsistent: a line with a single error at the per-line *pass* limit already gives SCS ≈0.37–0.64, far below the 0.80 tile threshold. A 2° angle error (passes `angle_err > 3°`? no — but 2° passes) gives SCS 0.641; a 2 px offset (passes) gives 0.368; colour_err 2.0 (passes) gives 0.368; width ratio 1.33 (passes) gives 0.515. So the per-line rules are dead letters and the tile rule is much stricter than they imply. | SCS_line(2°,0,0,0)=exp(−(2/3)²)=0.641<0.80; SCS_line(0,2,0,0)=exp(−1)=0.368; SCS_line(0,0,ln1.33,0)=exp(−(0.285/0.35)²)=0.515; SCS_line(0,0,0,2.0)=exp(−1)=0.368. | Derive the per-line tolerances from the SCS=0.80 contour (or define tile C4 as "any per-line failure"), and publish the joint budget so analysts can reproduce it. |
| 23 | **S2** | §6.2 (L779, L816), §6.4 (L819) | Width and text metrics are not measurable at the specified extremes: the generator allows rules of 0.25 pt (=1.04 px at 300 DPI), but FWHM-of-gradient width estimation needs ≥2–3 px; the `width_ratio ∈ [0.75, 1.33]` tolerance is sub-pixel there. Text sizes start at 4 pt (cap height ≈12 px at 300 DPI); OCR line-box cap-height/x-height estimates and colour means at that size are unreliable. | 0.25 pt × 300/72 = 1.04 px; 4 pt cap height ≈ 0.7·4·300/72 = 11.7 px. | State a minimum measurable rule width (≈0.75 pt) and minimum type size for TCS, or mark SCS/TCS `n/a` below them. |
| 24 | **S2** | §6.5 (L818–829) | Occlusion *inside the strip* is not covered: a known rule reaches the seam but is legitimately hidden by a foreground object just outside the trim; a correct model paints the object and no line, producing an unmatched known line → C4 fail. §6.5 only lists "a line that legitimately stops at the trim". | No exception/recovery path; the match rule requires a generated line. | Add a "continuation explained by an occluder/segment boundary" pass condition, or exclude known lines whose predicted ray crosses a detected foreground boundary. |
| 25 | **S2** | §2.6 (L238–240) | Orientation semantics are ambiguous and the §9.3 gradient self-test depends on the ambiguity. If the rotation includes the mask (as "the whole tile (content included)" implies), the unknown band is not on top for r≠0 and "canonical orientation" is false; if only content rotates, then the self-test "linear horizontal gradient, rotated 90° tile, edge_repeat → same MAE as unrotated" is false (the gradient becomes perpendicular to the seam, MAE 19.5·s, not 0). | §2.6 L238 says the canonical tile has unknown on top, L238 says the harness rotates the whole tile; the two cannot both hold for r≠0. | State explicitly whether the mask rotates; if both production canonicalisation and orientation bias are wanted, define two separate experiments. |
| 26 | **S3** | §4.4 D2/D4 (L526–528), D3 (L527) | D2/D4 are read from submission-declared fields (`inpainter.last_changed(_max)`) — a submission can report 0 while writing trim pixels; only D1's final trim hash is harness-computed. D3's denominator `|K_neighbourhood|` is never defined. | §2.4 L215–216 defines these as attributes on the submission object; §4.4 uses them as metrics. A raw write is DQ per DQ12 only if the harness computes it. | Harness computes D2/D4/D6 from the raw pre-clamp output it already holds; define `K_neighbourhood` (e.g. K pixels within 2 px of the seam) in the CSV schema. |
| 27 | **S3** | §4.3 C7 (L501), C8 (L502), §2.2 (L162) | C7 needs overlapping tiles but placement does not guarantee overlap: 6 tiles of 512 px on an edge of 2,481 px have 413 px spacing and jitter ±103 px, so adjacent centres can be 619 px apart > 512 → no overlap, C7 undefined for those pairs. C8's `R_composited` (how overlapping tiles are composited) is never defined. | 512 + 2·103 = 718 px max centre distance… overlap requires centre distance <512; jitter alone can exceed it. "Tiles MAY overlap" (L162) makes C7 conditional. | Mandate spacing ≤ tile size (e.g. 50% overlap) for C7 subsets and define the compositing rule (last-writer/feather) for C8. |
| 28 | **S3** | §4.6 F3/F4/F5 (L585–587), §8 T4 (L931) | F4 ("classified paper vs continue correctly") has no decision rule; F5's `paper_share(R)` is undefined; F3's `mark_ink`/`mark_line` are undefined and the brief's crop-mark offsets (0/9/38 px) never appear in §4.6/T4. §2.7 also declares crop marks "out of scope" while T4/F3 score their leak. | Search: no definition of paper_share, mark_ink, mark_line, or the 0/9/38 offsets anywhere; §2.7 L246 vs §8 T4 L931 contradict. | Define the model-output classifier (ink share threshold), paper_share, mark geometry/offsets (0/9/38 px), and qualify §2.7's "out of scope" as content-to-reproduce, not distractor. |
| 29 | **S3** | §9.3 (L999–1012) | Three of the twelve "exact" self-tests are not closed-form: the pasted-logo test depends on B5's object detector, the text-line test on OCR, and the rotated-4°-line test on LSD/Hough detection accuracy. §9.3 promises closed-form checks a new harness must pass. | Rows L1010–1011 and L985 (text) depend on third-party detectors and their thresholds. | Relabel those as detector smoke tests (with tolerances) and keep the truly analytic ones as hard gates. |
| 30 | **S3** | §3.1 (L316, L305–314), §8 T3 (L930) | Count arithmetic is internally inconsistent: 320 quiet pages × 4 = 1,280 NO_INK edges, but "1,284 inked edges of which ~831 FULL, ~453 STOP" implies 1,284+1,280 = 2,564 edges vs the stated 2,560; the material page counts 186+93+32+8+2 = 321 non-quiet pages → 641 pages. T3's "320 STOP/NO_INK pages (test split 160)" cannot fit a 160-page test split with ~50% quiet pages. | 2,560 edges total (640×4); quiet 320 pages → 1,280; 831+453=1,284 ≠ 1,280. 186+93+32+8+2 = 321. | Re-derive exact counts from the 640/2,560 base (inked = 1,280; ~831 FULL/~449 STOP; 185 photo pages) and pin them in the manifest. |
| 31 | **S3** | §2.1 (L139), §3.4 V1 (L344), §3.1 (L286) | The render region is never defined against MediaBox/BleedBox for real PDFs, and the apron (a px beyond the BleedBox) may not exist in the source; no rule for padding it or for excluding marks/slugs that live outside the BleedBox. Tier A says "Cairo (or MuPDF) … in both sRGB and CMYK" — Cairo is RGB-only, so the CMYK path cannot use Cairo. | Real PDFs frequently have BleedBox = TrimBox + 0.125 in exactly; the 10 px apron then has no artwork and MediaBox may contain marks. | Specify: render = BleedBox dilated by a (clipped to MediaBox), pad missing pixels with paper, and require a CMYK-capable renderer (MuPDF CMYK device) for CMYK pages. |
| 32 | **S3** | §4.2 B1/B2/B9 (L474–482, L486), A6 (L448) | Restraint tolerances are mutually inconsistent: B1 permits 0.1% ink (≈19 px on a 19,456-px tile) and B2 permits a 50-px blob, while B9 requires exactly zero ink on the edge and §4.2 says "one 2 px speck" is a visible defect and must fail. A6 applies B1>0.001 and B2>50 px to **all** tiles although B1/B2 are defined only "on STOP edges". | 0.001 × 512·38 = 19.5 px allowed by B1 vs zero allowed by B9. A6 clause has no STOP scope. | Choose one tolerance for the defect class (recommend no non-continuation ink on STOP: B1=B2=0, B9 as the hard rule), and scope A6's B1/B2 clauses to STOP tiles. |
| 33 | **S4** | §12.2 (L1183) | "300 pairs × 15 s ≈ 75 min per rater … Total ~4.5 rater-hours": 3 × 75 min = **3.75** rater-hours (4.5 only if 30 min training/setup per rater is included — say so). | 3 × 1.25 h = 3.75 h. | Correct to 3.75 h or state the included setup overhead. |
| 34 | **S4** | §9.4 R1 (L1020) | "(44.29 vs 45.96)" is unlabelled; the reader cannot tell whether LaMa or edge_repeat is 44.29. The operationalisation (Δ>1.67) implies LaMa=44.29, edge_repeat=45.96. | 45.96−44.29 = 1.67 = the required margin. | Label the pair ("LaMa 44.29 vs edge_repeat 45.96"). |
| 35 | **S4** | §2.2 (L162), §2.3 (L184–189) | The E=4-at-1024 justification conflates the 976 px *across-seam* known band with *along-edge* overlap; six 1024-wide tiles on a 2,481 px edge do overlap 2.5×, but the reason is the 1024 tile extent, not the 976 band. | 6·976 = 5,856 ≠ along-edge coverage; 6·1024/2,481 = 2.48×. | Cite the tile extent (1024) in the justification. |
| 36 | **S4** | §2.1, §4.9 (L648, L659) | "Physical bleed width is held constant across DPI" is not exact: 19/150 = 38/300 = 0.12667 in, but 75/600 = 0.125 in, so the 600 DPI pages have a 1.3% narrower physical bleed. I3's cross-DPI dE comparison therefore includes a ~0.5 px GT content difference at the outer ring. | 37.5 → 38 px ceil at 300 = 0.12667 in; 600: 75 px = 0.125 in. | State the per-DPI physical widths (0.1267/0.1267/0.125 in) and note the sub-pixel I3 caveat. |
| 37 | **S4** | §9.2 (L993) | "edge_repeat not the best **non-learned** method on flat" — LaMa is a learned CNN; the intended comparison is "classical", and the flat ranges (edge 0.0–0.5 vs stretch 0–1) overlap, so the sanity check is not exact either. | Terminology + overlapping intervals. | Say "classical" and state that the ordering check is on interval midpoints/tolerance. |
| 38 | **S4** | §4.0 (L408), B.3 (L1441) | "Metrics are computed per tile at 8-bit output precision" conflicts with 16-bit GT/renders and "computed in float64 after decoding"; the metric precision should be the declared output bit depth, not fixed 8-bit (O11 already flags the CMYK floor consequence). | §4.0 L408 vs B.3 L1441. | Say "in float64 of the declared output precision (8-bit default, 16-bit declared)". |

## Detailed notes

### A. Geometry and latent alignment — what checks out, what does not

**Checks out exactly.** Every entry in the §2.3 table (and B.1) recomputes:
`b = ceil(3.175/25.4×300) = ceil(37.5) = 38`; `a = (−38) mod 16 = 10`; `B = 48` (3×16);
150 DPI: 18.75→19, a=13, B=32, 480/992; 5 mm: 59.055→60, a=4, B=64, 448/960;
600 DPI: 0.125×600 = 75, a=5, B=80, 432/944; `B mod 16 = 0` in all four cases; tile known bands
512−B = 464/480/448/432 and 1024−B = 976/992/960/944. The 0.125 in = 3.175 mm conversion, the "26% more strip"
(48/38 = 1.263) and the v1 "7× at 2 px" (88/12.5 = 7.04) are all correct.

**Does not check out (finding 1).** `δx = (−W) mod 16` is applied to the right margin so that
`W + 2B + δx ≡ 0 (mod 16)` — i.e. it makes the **canvas** a multiple of 16 (which is needed for a VAE encoder),
but the right/bottom **seam** is at `B + W` and is unmoved by δx. Alignment of the right seam requires
`(B + W) ≡ 0 (mod 16)`, i.e. `W ≡ 0 (mod 16)`, which cannot be forced by margin padding. Therefore:
- L171 (`no trim pixel shares a latent cell…`) and L234 (`regen_trim_px = 0 for L ≤ 16…`) are false in
  whole-page mode for arbitrary W/H;
- D5 would flag a *compliant* L=8 or L=16 model (on Letter: 6 known columns per latent row on the right, 4 on
  the bottom);
- the "B-wide border" description of whole-page mode (§2.2 table) is also inaccurate: right/bottom unknown band
  is B+δx wide (63 px for Letter), so the right/bottom apron is a+δx, not a;
- the same applies to right/bottom **edge tiles** if they are literally "a crop of the whole-page canvas"
  (§2.2 L160): their seam sits 464−δx px from the tile edge (454 on Letter, not 16-aligned), contradicting the
  table's 464 known band. If instead tiles are anchored to the B-margin boundary they are fine — the spec must
  say which.

This is a one-decision fix (DD4) but it is the central v2 geometry claim, so it must be fixed before freeze.

**Other geometry/judgement notes.** Corner L semantics are correct in concept (two 48 px bands, 38 px scored
ring, miter 45°); J4's "dE00 between the two arms at the 45° miter line" is under-specified but implementable.
Tile jitter can push end tiles off the canvas (E=6, spacing ≈413 px, jitter ±103 px, half-tile 256 px) — tiles
that do not fit are only declared invalid for *small pages* (V7); for normal pages the clipping rule is missing
(S3, folded into finding 27). §2.2's "the 1024 tile covers 976 px of known band, so six would overlap heavily"
mixes the two tile dimensions (S4). Physical bleed is not exactly constant across DPI (S4). And `b` uses
`ceil(bleed_mm/25.4×dpi)` with `bleed_mm` for a 0.125 in spec — the 0.125 in is exact in inches, so defining the
input in mm introduces a redundant conversion; harmless but note that 0.125 in → 3.175 mm exactly in the spec.

### B. Colour (page space, ICC, CMYK, spot, black)

Positives: page-space scoring (DD10), declared intent/BPC (DD12), round-trip floor publication (DD13), separate
native-CMYK table, no dithering, and the explicit C11 warning that naive sRGB conversion gives up to 15 dE00 on
black. The V3 ink test with dE00 > 1.5 **or** L* < paper−2 does catch the documented 3–20% tints (3% K:
L*≈97.4 < 98 → caught; 5% C ≈ (242,255,255): ΔE00≈4 → caught), so the pale-tint fix is sound in principle.

Defects: (a) E6 is not a model metric (finding 8); (b) E3 has no floor and no ΔCMY rule (finding 11); (c) the
Adobe RGB floor of 0 is wrong under the default sRGB proxy (finding 11); (d) D65 vs D50 ΔE00 mixing (finding 15);
(e) E4 one-sided (finding 17); (f) paper estimation from the GT outer ring misclassifies full-bleed pages
(finding 16); (g) E1 duplicates A2 with a different flat threshold (finding 12); (h) `tint(R)` in E7 is not
defined for RGB-proxy entries — inverting a spot recipe from an sRGB pixel is many-to-one and undefined near the
solid (S3, part of the E completeness table below); (i) E2's `flat_drift_E = |mean ΔE00|` is just `mean ΔE00`
(absolute value is redundant) and its undefined `recipe_match` baseline needs defining (S3).

**dE00 thresholds against print perception.** 1.0 (C2), 1.5 (D6/E5/E7/J4/V3), 2.0 (A2 flat; E2 fail is `>2`),
2.5 (E1 flat), 4.0 (A2/E1 overall; B7), 8.0 (A6 texture). In print terms:
- 1.0–1.5 dE00 is at/just above the side-by-side JND for *large flat patches* on a proof (≈1 dE00 is the usual
  perceptibility threshold under controlled D50 viewing); C2/D6/J4/E5/E7 at 1.5 are **defensible**.
- 2.0–2.5 dE00 for a **flat continued tint** (A2 flat 2.0, E1 flat 2.5) is **not defensible**: a 2.0–2.5 dE00
  step between the trim and a solid is clearly visible on press and is exactly the "3-level drift is a customer
  complaint" case §C8 itself invokes (3 levels ≈ 1.2% dot ≈ well under 2 dE00 on many tints). Tighten flat to
  ≤1.0–1.5 dE00 and justify against ISO 12647-2 numbers expressed in ΔE*ab (≈ΔE00×1.5–1.7 for many pairs).
- 4.0 mean over the whole ring (overall) is a *lenient* pass criterion for images and is acceptable only because
  A6/A5 handle class failures; keep but say so.
- 8.0 for texture (A6) is large, but the stated reason (GT texture is a rendering convention) is a real one;
  defensible as class-conditional.
- B7's ΔE00 > 4 for "invented content on flat GT" may miss a faint invented tint (a 2–3 dE00 mark is visible at
  50 px = 4.2 mm on press) — consider 2.5–3 with the 50 px blob condition kept.

### C. Metric completeness audit (A1–J5)

Every row has a numeric/rule threshold and a named sanity baseline, which is a real improvement over v1. The
table lists every row that is **not** formula-complete, not computable from the described inputs, mis-ranged/
directed, or whose baseline is implausible. Rows not listed passed.

| Metric | Defect | Sev |
|---|---|---|
| A2 | Duplicate of E1 (both mean page-space ΔE00 over U) with contradictory flat thresholds (2.0 vs 2.5) | S2 |
| A4 | Fine (20 dB floor added; report-only) | — |
| A5 | "Class MAE + p90": p90 is not defined (A7 is p99; p90 never appears in a formula) | S3 |
| A6 | Same quantities with third thresholds (C1>3.0 vs C1 table 2.0; B1/B2 applied without STOP scope; flat A1>1.5 stricter than B8>2) | S2 |
| B1/B2/B9 | Three different tolerances for the same defect (0.1% / 50 px / zero); B9 undefined (0/0) on NO_INK pages | S2 |
| B3 | gt_copy=0 implausible (prior FPR > 0); double-dilation ambiguity; no thresholds for the prior | S2 |
| B4 | Per-10⁴ formula vs ">0 on STOP/flat" threshold; gt_copy=0 ignores OCR false positives; range "0–∞" vs ≤10⁴ cap | S2 |
| B5 | Formula per tile vs threshold per 1,000 tiles (1000×); gt_copy=0 ignores detector FPR | S1 |
| B6 | OK; baseline = judge FPR is the right model (but see §5.4 LOTO/contamination) | — |
| B7 | OK formula; threshold may be too lax for faint tints (see above) | S4 |
| B8 | OK, but conflicts with A6 flat 1.5 (A6 is stricter) | S2 |
| C1 | OK, but conflicting duplicate threshold in A6 (3.0) | S2 |
| C2 | OK | — |
| C3 | Reference baseline (edge_repeat, 3.78) fails the metric's own 3.0 threshold; R4 uses 3.78 | S2 |
| C4 | SCS=0 when no lines → gt_copy=1.0 and the §9.3 self-test fail; per-line vs aggregate tolerance conflict; no n/a rule | S1 |
| C5 | Zero-line analogue of C4 (formula only in §6); cap-height error undefined (`capheight_err` units/nats) | S2 |
| C6 | "salient" threshold undefined; prior FPR > 0 vs gt_copy≈0 | S2 |
| C7 | Overlap not guaranteed by placement; orientation of the two overlapping tiles not specified | S3 |
| C8 | `R_composited` undefined (compositing rule for overlaps missing) | S3 |
| D2 | Submission self-reported (`inpainter.last_changed`) — spoofable | S2 |
| D3 | `K_neighbourhood` undefined | S3 |
| D4 | Self-reported (as D2) | S2 |
| D5 | Whole-page geometry bug makes it fire on compliant L≤16 models | S1 (via #1) |
| D6 | Defined to be 0 when nothing changed (trivially passes gt_copy) — acceptable but note it does not score unchanged-but-bad fills | S4 |
| E1 | Duplicate of A2 with conflicting flat threshold | S2 |
| E2 | `recipe_match` baseline undefined; `|mean ΔE00|` redundant | S3 |
| E3 | No floor; ΔCMY aggregation undefined; ΔK>2% below proxy round-trip floor | S2 |
| E4 | One-sided; gtc=0 contradiction if near-white GT includes tints | S2 |
| E5 | OK (floor published; net can be negative — state the range) | S4 |
| E6 | Computed from GT, identical for all methods → not a model score | S2 |
| E7 | `tint(R)` not invertible for RGB proxy; 2% absolute tint threshold not meaningful on a ramp (O12 admits this) | S3 |
| E8 | OK (DQ at ingestion; boolean) | — |
| F1 | Scored region after trim shift not defined (MAE_δ over original U or new U?); no threshold at δ=1 | S3 |
| F2 | OK-ish; "output ink share" needs the paper-estimation definition | S3 |
| F3 | `mark_ink`/`mark_line` undefined; 0/9/38 px offsets missing; conflicts with §2.7 "out of scope" | S2 (via 28) |
| F4 | Model-output classification rule ("paper vs continue") undefined → uncomputable | S2 |
| F5 | `paper_share` undefined → uncomputable | S2 |
| F6 | Ratio semantics as F1 (dataset shift); δ=1 has no threshold | S3 |
| G1 | OK | — |
| G2 | OK | — |
| G3 | ">2.0 MAE or >0.5 dE" — the dE-gap version is not defined in the formula | S3 |
| G4 | Batch 8 OOM would be recorded as non-determinism (G4 fail → badge loss); conflates capacity with determinism | S3 |
| H1 | OK as a badge gate (defensible for production); note every generative baseline in §9.2 exceeds it | S4 |
| H2 | 1.5 s/page inconsistent with H1 100 ms × 28 tiles = 2.8 s; "28 tiles" wrong at 1024 (20) | S2 |
| H3 | Gain per second uses ungated MAE gain; if the model is gated the realised gain is lower — should use SystemGain per §7.6 rather than MAE_ref − MAE_m | S3 |
| H4 | Mixed units, numeric fail rules now present | S4 |
| I1 | gt_copy = 1.0 is 0/0 undefined | S2 |
| I2 | Same 0/0 | S2 |
| I3 | OK (but see 600 DPI physical bleed 1.3% narrower — S4) | — |
| I4 | OK | — |
| I5 | OK | — |
| I6 | gt_copy = 0 is 0/0 undefined | S2 |
| J1 | OK (ratio threshold defensible) | — |
| J2 | Undefined when tiles do not overlap (see C7) | S3 |
| J3 | Inherits SCS=0 bug → every line-free corner fails | S1 (via #2) |
| J4 | Formula vague ("dE00 between the two arms at the 45° miter line") but implementable | S3 |
| J5 | OK | — |

### D. Hallucination / restraint (§5)

Positives: four genuinely independent detector families with explicit blind spots; no-GT and GT-equipped
approaches; the "if no detector clears the bar, say so" clause; the correct statement that synthetic injection is
not validation.

Defects beyond findings 9/10/21: (a) the 2,000-vs-1,200 strip-count inconsistency is a factual error that also
changes the annotation budget; (b) B4's ">0 on STOP/flat" plus a 17,920-tile manifest demands an OCR with zero
false positives over thousands of tiles — unachievable, so the metric is only meaningful as a *rate*; (c) the
judge-positives/negatives construction (different page, paper fill on inked edge, perturbed GT) is sensible, but
"paper-filled strips on inked edges" overlaps the restraint class, so the judge may learn the paper/ink contrast
rather than invention; state the class balance. (d) B3's "two should correlate" with `halluc_edges` has no
acceptance criterion (correlation value, sample size) and `halluc_edges` is now declared a non-scored diagnostic —
fine, but then the validation claim needs a number.

### E. Structure continuation (§6)

The four-error decomposition (angle/offset/width/colour), the explicit matching tolerances, greedy matching and
per-line CSV export are a genuine improvement over BGE and are implementable for *long, straight, wide* rules.
The following prevent it from being scored fairly as written:
- zero-line convention (finding 2) makes C4/J3 fail everything line-free;
- per-line vs tile threshold inconsistency (finding 22) means the stated per-line tolerances are never the
  operative ones;
- thin-rule and small-type measurability (finding 23);
- occlusion inside the strip (finding 24);
- non-Latin/decorative type: acknowledged as an OCR blind spot for B4 but not for C5/TCS, which is where it will
  silently reduce `match_rate` (a model that correctly continues Arabic or a display face scores no matched
  lines); add the caveat to C5.
- Curved/diagonal structure and soft gradients are correctly listed as uncovered.

### F. Baselines and expected numbers (§9)

Positives: the seven-method frozen oracle (6 classical + LaMa) is correctly justified and isolated from v1's
six-method oracle; `legacy_v1` recomputation is required; v1 numbers are restated consistently (edge_repeat 11.50
matches C7's "mean 11.5"; LaMa 14.06≈14.1; SD2 78.37≈78.4/77.9; `sd_refine` 12.60; BGE 3.78 reused in R4);
headroom 11.50−8.58 = 2.92 and 11.50−9.00 = 2.50 exactly matches the "2.5–2.9 MAE" claim; ~2,600× = 1295/0.5;
the analytic gradient MAE 19.5·s is exact (mean distance 1..38); the 4°-line SCS = exp(−(4/3)²) = 0.169 < 0.80
is exact given §6.4; the 2×2 checkerboard and gt_copy rows are correct.

Defects: finding 20 (200-tile check set undersampling texture; FLUX cost), finding 6 (two-proportion n), the
SD3-inpainting baseline has no official pinned checkpoint to hash (BL11; "SD3-class MMDiT inpainting pipeline,
pinned weights" does not name an artifact — either name a concrete community checkpoint + derivation or mark it
constructed), the "±30% tolerance" is meaningless on the edge_repeat flat row (0.0–0.5 MAE), and §9.3's claim of
"exact" closed-form tests is false for three rows (finding 29). R4's use of C3 ≤ 3.78 contradicts C3's own
threshold (finding 12). R6's `SystemGain_headroom` is a new undefined quantity (S3) — define it or express R6 in
`regret`/MAE terms.

**Legacy table restatement.** Appendix B.5 is consistent with the v1 numbers quoted elsewhere in the document
(11.50/4.01/0.87/3.78/3.35 for edge_repeat; 14.06 for LaMa; 78.37 for sd_raw; 12.60 for sd_refine), and the
subset sizes (480, 730) are plausible against the 1,730 dev tiles. One gap: the table is described as "v1's
published dev-set results" but the document elsewhere says v1's severe rates came from the six-method oracle —
B.5 must be labelled as the six-method-oracle table (it is, by §9.1's note, but B.5 itself does not say so).

### G. Human study (§12)

Beyond findings 4/18/19: the preprint-size display instruction should state the display calibration target
(white point/luminance, e.g. 120 cd/m² D65 and soft proof for print D50) and the fact that a 4× toggle is used
in the main study, not only in the hallucination task. The rater design does not say whether all three raters see
the same 300 pairs (needed for Bradley–Terry rater effects) or disjoint sets (in which case rater effects are
confounded with pair allocation). "AUC ≥ 0.75 for the defect-category classifiers" is undefined (which
classifier, binary vs multi-class AUC). The 40 stimuli are selected "from the private calibration set" — using
calibration pages for the human study and then freezing thresholds is consistent with pre-registration, but the
study should not reuse the calibration pages a model's gate was tuned on without saying so.

### H. Cross-section contradictions and arithmetic (for the owners of §3/§7/§10)

These are outside my primary sections but block the protocol as a whole:
- §0 vs §7.6/§7.4 headline unit contradiction (finding 7).
- §10.2 third two-proportion row (finding 6).
- §10.4 "Mean MAE within a class, ±0.5 → ~1,500 tiles" does not follow from "σ≈15–20; design effect 2.35":
  n = (1.96·15/0.5)²·2.35 ≈ 8,100 (σ=15), ~14,400 (σ=20). The stated 1,500 corresponds to σ≈6.4 — re-derive.
- §10.1 "the exact bound is the one used for gates" vs §10.3 "the gate uses the larger of the two [exact and
  cluster-bootstrap] bounds" — direct contradiction; the gate rule must be one of them (and clustering argues for
  the bootstrap, or an exact bound on *families*).
- §3.1 count arithmetic (finding 30); T3's stop/no-ink page count.
- §13.1 CSV column `halluc_ppm` implies parts-per-million while B3 is per 10⁴ px (10,000× scale) and
  `object_hits` lacks its per-tile denominator — name the denominator in the column or in the schema docs.
- §3.3 "v1 private corpus of 124 pages/70 families remains usable: v2 recomputes validity … (recovering the 33
  STOP/NO_INK pages)" but C2 says the 10 blank pages are NO_INK, so v2 recovers up to 43 pages and the usable
  count should be stated (117?), not left as "124 pages remains usable".
- Duplicate `### 10.6 Missing data and attrition` heading (L1106/L1108) — editorial.

## Checks performed

- [x] Recomputed every geometry constant in §2.1/§2.3 and Appendix B.1: b for 150/300/600 DPI and 5 mm, a=(−b) mod 16, B=b+a, 512/1024 known bands, `B mod 16 = 0`, 464/976 alignment; all correct.
- [x] Recomputed the whole-page canvas: left/top margin B, right/bottom B+δx, `δx=(−W) mod 16`, canvas multiple of 16; verified the right/bottom **seam** does not move with δx and is off-grid for W ≢ 0 (mod 16) — counterexample US Letter 2550 px → seam 2598 ≡ 6.
- [x] Verified corner L geometry, 45° miter, ring width b on all four sides, apron width a (left/top) vs a+δx (right/bottom), and the 26% band inflation.
- [x] Checked tile placement arithmetic (E=6/512, E=4/1024; 28 tile-runs/page = 6×4+4; 160×4×28 = 17,920; 2,560 corner tiles) and the jitter/overlap guarantee (fails for C7).
- [x] Audited every metric row A1–A7, B1–B9, C1–C8, D1–D6, E1–E8, F1–F6, G1–G4, H1–H4, I1–I6, J1–J5 for formula/range/direction/threshold/sanity baseline/blind spot (table in §C above).
- [x] Checked all dE00 thresholds (1/1.5/2/2.5/4/8) against print perceptibility and ISO 12647-style tolerances; flagged flat 2.0/2.5.
- [x] Checked colour pipeline: page space vs model space, ICC PCS D50 vs sRGB D65, intent/BPC, CMYK round-trip floor, RGB proxy vs native CMYK, Adobe RGB floor, rich black/TAC, spot tint ramps, gamut clipping, near-white/paper estimation.
- [x] Recomputed the analytic self-tests: gradient MAE 19.5·s exact; 4° line SCS 0.169; per-line vs tile SCS budget (2°/2 px/dE 2.0/width 1.33 → 0.64/0.37/0.37/0.51); zero-line SCS convention contradicts gt_copy=1.0 and the solid-page self-test.
- [x] Verified the zero-event bounds 1−0.05^(1/n) for n = 11/48/80/89/160/292/299/320/1000/1300; all correct (89 → 3.31%, table says 3.30%).
- [x] Recomputed the proportion half-widths and sample sizes in §10.2: ±2.8/±1.39/±1.0/±0.98 pp correct; 1,118/1,244/4,976 correct; two-proportion 1 vs 2% and 2 vs 3% within rounding; 3.35 vs 4.35% wrong (3,048 vs 5,807).
- [x] Recomputed the §10.4 mean-MAE sample size (1,500 vs needed ~8,100) and the §10.3 design-effect examples (1.11 and 1.45 correct).
- [x] Checked the §9.2 baseline ordering (gt_copy 0; edge_repeat best classical on flat; paper_fill near 0 on B1) and the FLUX/SD3/MAE/ViT/LaMa/Telea/NS/PatchMatch baselines and their names/pinning plausibility.
- [x] Restated and cross-checked the v1 legacy table (Appendix B.5) against §1/C7/C17 and §9.4: consistent; headroom 2.50–2.92 correct; 2,600× correct.
- [x] Checked the human-study design (40 strips, 300 pairs, 3 raters): 300×15 s = 75 min ✓; 3 raters = 3.75 h (stated 4.5); ±5.4 pp arithmetic ✓ but ignores page/rater clustering; print-size/zoom and D50/D65 display issues; missing accept/reject labels for threshold calibration.
- [x] Checked the hallucination validation set arithmetic (2,000 vs 1,200), prevalence/precision logic, leave-one-generator-out feasibility, and detector train/test contamination.
- [x] Cross-checked §0 SystemGain/gate units against §7.4/§7.6, §10.1 vs §10.3 gate-bound rule, §3.1 count arithmetic (2,560 edges; 1,280 vs 1,284 inked; 320 vs 321 pages), and §13.1 CSV column denominators.
- [x] Confirmed scope compliance: this review edits only `reviews/prepress-review.md`; SPEC.md, README.md and other reviewers' files were read but not modified.

---

## Post-fix verification (current revision)

Snapshot: `SPEC.md` sha256 `7cccd0b06a5181a3cd66a8c4185ed93adedd7622cc6b40af69b7b844a4c0f826`
(1,554 lines, `LastWriteTime` 2026-11-01 01:04:48 local). Targeted re-read of §0, §2.2–2.8, §3.4, §4.1–4.10,
§5.3–5.4, §6.4–6.5, §7.4–7.7, §9.1–9.4, §10.1–10.4, §11.4, §12.1–12.4, §13.1; arithmetic recomputed where
changed. **Verdict on this revision: PASS WITH FIXES** — all six S1s are resolved; no new S1; three residual/new
S2s and a short S3 list remain.

### Six S1s

| S1 | Status | Evidence at current revision |
|---|---|---|
| 1. Whole-page δx / latent alignment (§2.3, §2.5, DD4) | **PASS** | Alignment claim now scoped: tile mode every seam 16-aligned (tile is seam-anchored, known band exactly 464/976 also for right/bottom, §2.2 L163); whole-page left/top aligned, right/bottom remainder stated as `r_x=(B+W) mod 16 = W mod 16` (L185–190) and the US Letter example is correct (W=2550 → r=6; 6 known + 10 unknown columns in a 16-cell). The false "right/bottom seams land on the 16 grid" claim is gone; §2.5 now expects nonzero `regen_trim_px` on right/bottom, reports per seam, scores with D6, never DQ; D5 threshold updated (L564). |
| 2. C4/SCS zero-line convention (§6.4, C4, J3, §7.4, §9.3) | **PASS** | `SCS = 1.0` convention when no known line, C4 `n/a` and excluded from the denominator with `line_coverage`/`text_coverage` reported (L540, L532, L860–862, L872); per-line tolerances are the operative pass rule; §9.3 solid-page test now says "C4 = n/a (no known line)" (L1064); J3 n/a (L712, L721); page_safety conditioned "on a tile where the metric applies" (L919–920); J5 updated. |
| 3. Hallucination set count (§5.4 vs §12.3/O3/DD40) | **PASS** | 1,200 strips = 400 GT + 400 injected + 400 model, with 200 ambiguous as a non-additive subset (L775–782); §12.3 L1260, O3 L1389 and DD40 all say 1,200. |
| 4. Human study accept/reject labels (§12) | **PASS** | 60 strips × accept/reject/unsure is the response variable, explicitly "pairwise preference alone cannot provide it" (L1247–1249); logistic calibration on the accept/reject label, global/directional only, class thresholds deferred to O6 (L1259); 3 raters see the same 300 pairs; print-size `zoom = display_PPI/300`, 2–4× loupe, CMYK soft proof (L1252); power caveat and DE 1.5 planning interval stated (L1257). |
| 5. B5 unit error (§4.2) | **PASS** | `B5 = 1000·hits/#tiles − 1000·FPR_det`, per 1,000 tiles net, threshold >1 per 1,000 net, gt_copy ≈0 after FPR subtraction (L484, L491, L499); FPR measured on the separate frozen 2,000-strip detector-calibration set. |
| 6. SystemGain / gate units (§0, §7.4, §7.6) | **PASS** | One page-level definition (q90 page_fidelity, page weights) in §0 L43–47 and §7.6 L936–946; "there is no tile-weighted SystemGain variant"; gate is tile-level, page acceptance = all tiles; §7.7 adds 50/50 selection/certification halves and CP-DE bound. Arithmetic checks: 299×2.35 = 702.65 → ≥703 accepted tiles; 89×2.35 = 209.2 → ≥210; 299×1.11 = 331.9 → 332 raw pages; 350/1.11 = 315.3 → 0.95% UB. §10.1/§10.2/§10.3/§10.4 and DD55 (350-page set) are now consistent. |

### S2 list from the first review

| S2 | Status | Evidence |
|---|---|---|
| E6 computed from GT only | **PASS (residual S2/S3)** | Now `gamut_handling` scores R on `U_out` (L587–588, threshold 0.05, baseline roundtrip_gt). Residual: `G_clip` is "GT after **declared** mapping" and the spec does not say who declares it; §2.8's "one declaration per entry" suggests the submission, in which case a submission can choose the mapping whose target equals its own output and drive E6→0. Freeze `G_clip` from the page/harness mapping (roundtrip_gt) and add the 0/0 n/a rule when `|U_out| = 0`. |
| B3/B4/C6 `gt_copy = 0` implausible for no-GT detectors | **PASS** | B3/B4/B5 now net of measured GT FPRs from a frozen 2,000-strip set (L482–499); C6 also stated net of prior FPR (L765). Residual S3: C6 is an edge-count ratio while `FPR_prior` is per-10⁴ px — state C6's GT-FPR as an expected unsupported ratio, and state B3/B4 FPR units. |
| §5.4 precision prevalence / judge contamination / LOCO | **PASS on prevalence; REMAINING S2 on contamination/LOCO** | PPV(π) formula, π=5%, ~33% enrichment acknowledged, CP lower bound ≥0.85 on PPV(0.05), AUROC ≥0.85 (L784–800) — the prevalence problem is fixed. But the judge's training negatives are "model outputs collected across generators" (L771) while the human-labelled "model negatives" are outputs from ≥5 baseline methods (L781): the same generator families can appear in both, so the measured PPV is inflated; and leave-one-generator-out is still undefined for a submission whose generator was never in the judge's held-out set. Fix: forbid judge training on the frozen human set or its source outputs, and add an advisory (not gating) rule for unseen generators. |
| E3 no floor / Adobe RGB floor 0 | **PASS** | `rich_black_net = raw − roundtrip_floor_richblack`, ΔCMY = max_c, thresholds on the net (L581–583, L597, L604); Adobe RGB row now "0 if model space is Adobe RGB; measured if an sRGB proxy is used" and §4.5 "Wide-gamut pages" repeats it (L269, L606). |
| V2 paper estimate on full bleed | **PASS** | Outer-ring estimate only when the ring is uniform and near-paper (≥90% within 2 dE00 and not dark), full-bleed rings explicitly prohibited; `paper_source`/`paper_confidence` recorded; low confidence → `paper_uncertain`, excluded from STOP/B1 but retained for FULL (L362). |
| Duplicate/conflicting thresholds (A2 vs E1, C1, C3/R4, B8/A6) | **PASS** | A2 = E1 = >1.5 flat / >5.0 overall (L460, L595); A6 flat A1>2.0/A2>1.5 and C1>2.0 match the metric tables (L467); C3 threshold >4.0 with "edge_repeat = 3.78 passes" (L531); R3/R4 now reference edge-repeat's recomputed v2 values with v1 numbers as pre-freeze placeholders (L1086–1087, L1095). Residual S4: A6's sentence "No threshold here sits below edge repeat's own published mean (11.50 MAE…)" is numerically false as worded (flat A1 threshold 2.0 < 11.50); reword to "edge repeat passes every per-class rule". |
| H1/H2 inconsistency | **PASS** | H2 = 3.5 s/page at 512 (28×100 ms + assembly) and 2.5 s at 1024 (20 tiles), whole-page single pass 1.5 s (L681); matches H1 exactly. |
| I1/I2/I6 0/0 baselines | **PASS** | ratio = 1 if both 0 (I1/I2), 0 if both 0 (I4/I6) (L693–698). |
| §12 print-size/zoom and power | **PASS (bounded)** | zoom = display_PPI/300, 2–4× loupe, CMYK soft proof, sub-0.1 mm judged at loupe scale, D50 proof check (L1252); 300 pairs' independence assumption and page-clustering caveat (DE≈1.5 → ±6.6 pp) stated and treated as ranking evidence (L1257); class-conditional thresholds explicitly out of scope (L1259, L1264). Residual S4: arithmetic gives (60×10 s + 300×15 s + 15 min)/rater = 100 min = 1.67 h → **5.0 rater-hours**, not "about 2 h per rater, 6 rater-hours"; and §12.1 still says the study "calibrate[s] the absolute failure thresholds (A6, B1)" while §12.3/12.4 say it only validates their direction. |
| FLUX cost implausible / 200-tile check set | **PASS** | flux_fill now 800–2,500 ms and sd3 1,000–3,000 ms at 512 (plausible for a 12B DiT); §9.2 uses a 400-tile stratified check set with ≥40 tiles/class (L1035); the census-weighted "overall" column now recomputes consistently for all 15 rows (checked: paper_fill 13.65∈[12,20], edge_repeat 6.93∈[5,8], lama 12.39∈[9,16], mae_vit 13.69∈[12,20], sd2_raw 42.55∈[30,55], etc.). |
| SD3-class baseline not pinnable | **PASS (residual S3)** | BL11 is now `sd3_mmdit` = a named SD3.5 checkpoint + declared inpainting adapter derivation, explicitly "a constructed pipeline, not an official single artifact" (L1025). Residual: "the exact derivation is part of the submission" conflicts with the same-baseline-rows rule — maintainers should freeze one derivation in `expected_baselines.json`. |
| §6.4 per-line vs aggregate SCS tolerance conflict | **PASS with residual S2** | Per-line tolerances are the pass rule and SCS<0.80 is withdrawn (L872). Residual: the new catastrophic rule `SCS < 0.20` is still reachable by lines that pass **every** per-line tolerance. Max Σ while passing = (3/3)² + (2/2)² + (ln1.33/0.35)² + (2/2)² = 1+1+0.676+1 = 3.676 → SCS_line = e^−3.676 = 0.025 < 0.20. A single such line (or a mean of them) fails C4 under the catastrophic clause despite no per-line breach. Fix: set the catastrophic floor below the per-line-consistent minimum (<0.02) or drop SCS from pass/fail and keep it as ranking only. |
| Width/TCS measurability | **PASS** | Floors added: SCS ≥0.75 pt (≥3.1 px at 300 DPI) and TCS ≥6 pt (cap height ≥17.5 px); below floors the line is `unmeasurable` and excluded (L874). |
| B3 continuation prior under-specified | **PASS** | Canny 20/60, LSD ≥12 px/≥3 levels, 11×11 structure tensor, b-px extension with grazing rule \|t·n\|<0.2, single 3 px dilation, salience \|∇\|>8, FPR measured on a separate frozen set and netted (L765). |
| D65/D50 Lab mixing | **PASS** | All scoring Lab is now D50: "Lab D50 (Bradford-adapted)" for sRGB, "Lab D50" for Adobe RGB, "CMYK→Lab D50 via ICC" (L268–270); consistent with ICC PCS. |
| D2/D4 self-reported | **PASS** | Harness computes D1/D2/D4 from the raw pre-clamp output it holds; submission attributes are "informational and never trusted"; D1b final-identity gate added (L225–228, L547–551, L567). |
| C7/C8 overlap/compositing undefined | **PASS** | C7/J2 restricted to a dedicated 50%-overlap subset (100 pages); C8 compositing rule defined (32 px raised-cosine feather, weights sum to 1; same rule for both arms) (L165, L522–524, L540). |
| F3/F4/F5 uncomputable / crop-mark offsets | **PASS** | F3 offsets {0,9,38} px with a 0.25 pt 100% K full-length mark definition; F4 classify(R) rule (≥99% of U within 2 dE00 of paper); F5 paper_share defined; 200-page/40-family robustness manifest disjoint from T1/T2 (L610–631); §2.7 scopes marks as in-scope input distractors. |
| §2.6 orientation ambiguity | **PASS** | Explicit: base canonical generation, then the entire tile (content **and mask**) is rotated; "canonical orientation describes tile generation, not evaluation"; rotation-equivariance rationale for the 19.5·s self-test stated (L250–252). |
| D5 whole-page false-fail | **PASS** | Threshold scoped: >0 fails on tile-mode / left-top whole-page seams for L≤16; expected and scored on right/bottom (L246, L564). |
| §9.3 "exact" tests not closed-form | **PASS** | First nine rows closed-form/fully specified; text/4°-line/pasted-logo rows labelled detector smoke tests with tolerances (L1061–1076). |

### New / still-open findings at this revision

**S2:**
- **N1 — §5.4**: judge training/human-label overlap and undefined LOCO for unseen submission generators (details in the table). The only substantive residual risk to a gating hallucination claim.
- **N2 — §6.5 occlusion exclusion is gameable (new, introduced by the fix).** "a known line whose projected ray crosses a detected foreground boundary … is moved to `excluded_occluded`" (L881) does not say on which image the boundary is detected. If it is detected on the model output R (the only place the occluder can exist for missing bleed), a model can paint a strong contrasting edge across a line's ray and convert a missed continuation into an excluded one, inflating C4. Fix: detect the occluder on GT where available (or require it to be reproduced in GT), cap the excluded fraction per tile and report it, and never let exclusion be driven by R alone.
- **N3 — §6.4**: catastrophic `SCS < 0.20` is not disjoint from the per-line pass rule (recomputation: a line at 3°/2 px/1.33/2.0 dE passes every tolerance and scores 0.025). Fix: floor <0.02 or drop SCS from pass/fail.

**S3 (brief, not blocking):**
- §13.1 CSV is missing the new fields the metrics now rely on: `line_coverage`/`text_coverage` (§4.3/§6.4), per-seam `regen_trim_px_left/top/right/bottom` (§2.5; CSV has one `regen_trim_px`), `paper_source`/`paper_confidence` (§3.4 V2), `D1b`; the metric is renamed `gamut_handling` while the CSV column is still `gamut_clip`; `object_hits` vs net `B5` needs a denominator/net definition; `excluded_occluded` has no column.
- §2.1/§3.4 still never define the render region against MediaBox/BleedBox (no MediaBox mention in the file): for real PDFs the apron beyond the BleedBox may not exist, and no padding rule is given. (First-review S3 #31 is unfixed.)
- §2.3 four-pass whole-page alternative: C8 compares a single-pass output with the tile composite; a model that only ever runs four seam-anchored passes has no single-pass arm. State that C8 is n/a for declared multi-pass strategies, or require the model to run both.
- §11.4 G4: batch sizes 1/4/8 are mandatory; a 12B model that cannot run batch 8 on a 24 GB card would be recorded as non-deterministic. Allow OOM at batch 8 to be declared and scored on 1/4.
- §10.4 texture row: "~610 unclustered; ~1,440 clustered; σ≈15–20" — 1,440 clustered corresponds to σ=15; at σ=20 it is ~2,550, which the 65 texture pages (≈1,820 tiles) of the annual set would not meet. Tighten the σ statement.
- §12.1 wording (see S4 above) and the rater-hour arithmetic (5.0 h vs 6 h).
- §4.2/B3–B4 FPR units and C6 net-FPR units (see table).

### Post-fix checks performed

- [x] Re-read the requested sections in the `7cccd0b…` revision and diffed them against the audited `d657463…`/`a1a7e68…` versions.
- [x] Re-verified all six S1s against the current text (table above), including the US Letter r_x=6 example, tile known band 464/976, D5/D6 handling, C4 n/a and SCS convention, 1,200-strip arithmetic, accept/reject protocol, B5 net formula, and the single page-level SystemGain.
- [x] Recomputed the new gate/sample arithmetic: 299×2.35=702.65→703; 89×2.35=209.2→210; 299×1.11=331.9→332; 350/1.11=315.3→UB 0.95%; 1,300 at 5% attrition (1,235)→0.24%; 88-tile 3.35% crossover; ±1.03–1.06 pp at DE 1.11; human CI ±6.6 pp at DE 1.5.
- [x] Recomputed all 15 rows of the revised §9.2 census-weighted "overall" column against the stated ranges (all consistent).
- [x] Recomputed the H2 thresholds (28×100+700 = 3.5 s; 20×100+500 = 2.5 s), the texture test share (16/160 = 10%), the ±0.5 MAE sample sizes (8,125 at σ=15; 14,444 at σ=20), and the §6.4 catastrophic-floor arithmetic (e^−3.676 = 0.025 < 0.20).
- [x] Checked the new cross-references that could break: §3.6 counts (829+451 = 1,280; 185+93+32+8+2 = 320), §10.1/§10.3 gate-bound wording, §2.5/§13.1 field names, §4.5 E6 mapping ownership, §6.5 exclusion source, §12.1 vs §12.3 purpose.
- [x] Confirmed no new S1 and no new requirement violation; the residual items above are the only ones I would hold the freeze for (N1–N3 S2s, plus the CSV/render-region S3s).

**Post-fix verdict: PASS WITH FIXES** (six S1s closed; 3 S2s and a small S3 set remain, none requiring redesign).
