# Handoff — bleedBENCH v2.1

**Date:** 2026-11-01 · **State:** v2.1 draft spec + reference harness + first private pilot tier (C0). Not frozen; the v2.0 re-audit is still pending and should now cover the v2.1 diff.

## What exists

| Path | Purpose |
|---|---|
| `SPEC.md` | Specification. v2.1 amendments in §0.1 (M1–M10), new pitfalls §1.3 (N1–N9), C0 pilot §3.3a, pseudo track §3.3b, V12–V14 + STOP rule in §3.4, D1/D2 fix in §4.4, dev table §9.5, O15–O17, DD67–DD86. |
| `bleedbench/` | Reference harness (see README layout). |
| `aggregates/census_c0.json` | Measured C0 priors (deployment and real-GT censuses), k ≥ 5 families per cell. |
| `aggregates/dev_c0.json` | C0 dev table: per-method metrics, design effects, oracle-bias check, missing-bleed table, gates, achieved bounds. |
| `aggregates/transfer_c0.json` | T10 pseudo→real transfer; O13 synthetic→real rank transfer. |
| `aggregates/cost_c0.json` | Quiet batch-1 cost on the RTX 3090 (`clocks_locked=false`). |
| `tests/` | 36 public tests (geometry, §9.3 self-tests, CIEDE2000 reference pairs, metrics, stats, privacy, resume, models) + 6 private leakage tests (`pytest -m private`). |
| `tools/verify_spec_numbers.py` | Spec arithmetic incl. V12 geometry, census consistency, k-anonymity, dev DE identities. |
| `tools/check_no_private.py` | Pre-commit privacy guard. |

Private, never committed (`_private/`, gitignored): inventory, review decisions, renders, input/label stores, `splits.json`, `oracle_c0.json`, run CSVs, weights (big-LaMa safetensors, trained models + manifests), gate models.

## Results so far (C0 dev, real GT, FULL + NO_INK edges, 14 families)

- **Edge repeat is the best method measured** (mean MAE 10.74, median 1.00, severe 3.5%). No classical fill, LaMa, or trained model has a paired ΔMAE or SystemGain interval on the winning side of zero (the LaMa fine-tune ties it). Matches v1 (11.50 / 3.35%).
- **LaMa** drifts on flat colour (2.45 vs 0.30) and does not win texture on C0; its raw output rewrites the trim on every tile.
- **STOP is missing bleed:** 47% of real inked edges end exactly at the trim. Scoring "paper" there (v2.0) made every continuation method look catastrophic; v2.1 removes STOP from fidelity and scores restraint on NO_INK.
- **Design effects are much larger than planned:** `DE_tile` 12.9 (v2.0 assumed 2.35), `DE_page` 1.84. No gate is certifiable on C0; that sizes Tier C.
- **Pseudo GT ranks methods like real GT** (Spearman 0.95 over ten methods) but with different absolute errors; a pseudo-GT win does not imply a real-GT win.
- **Synthetic transfer (O13):** Tier A vs C0 dev Spearman 0.64 (nine methods, low power), below the 0.8 target. bleedgen v0 is not yet a faithful ranking proxy.
- **Trained models** (train_fit only, selected on train_dev, no real-GT family seen):
  - `strip_unet_mix` (residual over edge repeat, 15.1 M params) converged to a zero residual; its dev output is identical to edge repeat. Ablations were skipped.
  - `lama_ft_c0` (big-LaMa, 3,000 fine-tune steps) **ties** edge repeat: MAE 10.81 vs 10.74, ΔMAE +0.07 [−0.54, 1.69], SystemGain +0.21 [−3.48, 2.87]. It cuts LaMa's flat drift (0.79 vs 2.45; edge repeat 0.30) and wins on structure (24.9 vs 26.1), but its severe rate is 6.5% vs 3.5%, and it costs 92 ms/tile vs 16 ms. It beats edge repeat on pseudo pages (7.00 vs 8.23), which mostly does not transfer.
  - No gate is selectable for any model on C0.

## What to do next (in order)

1. **Re-audit** v2.0 + the v2.1 diff (same three reviewers). Items to check first: M1 (STOP semantics), M2 (D1/D2), M4 (A6 seam scope), M8 (gate units / DE), DD77 (cell-replacement rule).
2. **Verify the 8 `inferred_trim` pages** by hand (`_private/review/inferred_verified.txt`) and re-run splits/census if any are promoted.
3. **Collect Tier C** at the size the measured design effects require (§10): page-level claims need families, not tiles.
4. **Quiet cost with locked clocks** (admin): `nvidia-smi -lgc` then `_private/cost.py`; set `clocks_locked=true`.
5. **Freeze** thresholds (`protocol_c0_v2.1.json`), then open the C0 sealed test once.
6. **Models worth trying next:** `lama_ft_c0` is the starting point. A model that beats edge repeat must keep its structure win without drifting on flat; a gate that routes only structure-class tiles to `lama_ft_c0` is the cheapest next test once Tier C makes gates certifiable. Also try class-conditional residuals and a perceptual or structure-continuation loss. Do not train on real-GT families.

## Operational notes

- The RTX 3090 dropped off the bus once under two concurrent sustained GPU jobs; `_private/pipeline.sh` runs GPU work sequentially and is resumable (page-level for scoring, step markers for stages). Consider a power limit (`nvidia-smi -pl 300`, admin).
- Windows: DataLoader workers need a script file with a `__main__` guard (stdin scripts hang).
- big-LaMa is loaded from `big_lama_generator.safetensors` (SHA `abfef2e8…`), converted once from the HF `smartywu/big-lama` checkpoint (zip SHA `f1b358ca…`) with a restricted unpickler.

## Freeze checklist

- [ ] re-audit: no S1 on the v2.1 diff
- [ ] `python tools/verify_spec_numbers.py` passes
- [ ] `pytest` and `pytest -m private` pass
- [ ] inferred-trim pages verified or excluded
- [ ] thresholds frozen (A6, content classes, V1 integrity) on `cal_sel`
- [ ] sealed test unopened until freeze
