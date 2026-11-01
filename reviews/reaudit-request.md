# Re-audit request — SPEC.md revision 2

**Spec revision:** commit `24e0e71` (`git show 24e0e71:SPEC.md`).
Baseline: revision 1 plus the post-fix addenda in `reviews/*.md`.

## Changed sections (diff-only audit scope)

| Section | Change | Reviewer |
|---|---|---|
| §3.4 V11, §3.2 | Render region: BleedBox + apron, clipped to MediaBox, paper-padded, unscored | prepress |
| §4.3 (C8 applicability) | C8 `n/a` for four-pass models; C7 only | compliance |
| §9.1 BL11 | Named/hashed adapter or omitted from numbers-to-beat | compliance |
| §9.4 | R1/R2 `provisional-until-freeze`, provenance paragraph | stats |
| §10.1, §13.2 | `CP-DE` label; `certificate`, `accepted_severe_ub95_bootstrap` JSON fields | stats |
| §10.4 | σ_texture measured at calibration | stats |
| §3.1, O1 | `ASM-A1` naming | stats |
| §13.3 | `passes_per_page` in `track_config.json` | compliance |
| Appendix A | DD61–DD66 | all |

## Questions for reviewers

- Prepress: is "pad with the V2 paper estimate and leave unscored" sufficient when BleedBox exceeds MediaBox, or should such pages be dropped outright?
- Stats: does labelling `CP-DE` with the bootstrap UB beside it satisfy the earlier S1 on gate certification?
- Compliance: re-run `docs/review-checklist.md`; confirm 133-column CSV and the 22 v1 columns unchanged, and that no new hard constraint is violated.

Freeze only if no S1 from any reviewer.
