# Re-audit request — SPEC.md v2.1 (C0 pilot)

**Spec revision:** the commit that adds this file (`git log -1 -- reviews/reaudit-request-v2.1.md`).
Baseline: revision 2 (`24e0e71`) plus `reviews/reaudit-request.md`, which is still open.

## Changed sections (diff-only audit scope)

| Section | Change | Reviewer |
|---|---|---|
| §0.1 M1, §3.4 | STOP edges are missing bleed: excluded from fidelity, severe, A6, gates and SystemGain; restraint scored on NO_INK | prepress, stats |
| §4.4 M2, DD83 | D1 on returned output; D2–D4/D6 on the exposed raw network output | compliance |
| M4, DD86 | A6 C1 seam rule applies to flat/gradient only | prepress |
| §3.4 V12–V14 | Scored ring `min(b, floor(bleed_pt·dpi/72))`; pseudo-GT validity; imposed sheets and low-DPI rasters are not GT | prepress |
| §3.3a, §3.3b | C0 pilot tier and Track P pseudo-GT; no pooling with C or real GT | stats |
| §3.5, M9 | Multi-signal families; training manifests; gate_fit disjoint from train_fit | compliance |
| §7.7 M8, DD74 | Gate certification on orientation-0 units with measured DE | stats |
| DD77 | Prior cell-replacement rule (CI half-width ≤ 10 pp) | stats |
| §1.3 | Corpus-era pitfalls N1–N9 | all |
| §9.5 | First C0 dev table incl. trained models; T10 and O13 | stats |
| §14, App. A | O15–O17; DD67–DD86 | all |

## Questions for reviewers

- Prepress: is "STOP = missing bleed" the right production reading, or should STOP be scored against a page-extension preference collected from operators?
- Stats: with `DE_tile` 12.9 measured, are the Tier C sample sizes in §10 now adequate, and is orientation-0-only certification sufficient?
- Compliance: confirm no client-identifying content in `aggregates/*.json`, SPEC or HANDOFF, and that the k ≥ 5-family export rule is enforced by `bleedbench/privacy.py`.

Freeze only if no S1 from any reviewer.
