# Corpus review log

The E5 exit gate is a **human review** ("labels reviewed against the written
rubric"; execution-plan 0.5). The generators produce *validating, review-ready*
tranches; a human signs off here against
[`docs/product/verity-corpus-authoring.md`](../../docs/product/verity-corpus-authoring.md)
§5. A tranche is not "done" until its row is marked reviewed.

## Log

| Tranche | Scenarios | Ground-truth source | Generated | Reviewed | Reviewer / notes |
|---|---|---|---|---|---|
| E0 seeds (`0001`/`0002`/`9001–9004`) | 22 | hand-authored | G3 | ✅ | reviewed at E0 (corpus-spec §7) |
| `secret_read` E5 tranche 1 (`0003–0022`, `0030–0039`, `0901–0910`) | 70 | gitleaks `v8.30.1` | `corpus_gen/generate.py` | ⏳ **pending** | machine-validated (schema + integrity + gitleaks ground-truth); awaits human sign-off on §5 checklist |
| `shell_exec` E5 tranche 1 (`0003–0017`, `0030–0044`, `0901–0910`) | 70 | canonical destructive forms, MITRE ATT&CK-mapped | `corpus_gen/shell_exec.py` | ⏳ **pending** | machine-validated (schema + integrity + attack/benign regex checks); awaits human sign-off on §5 checklist |
| `self_mod` E5 tranche 1 (`0003–0017`, `0030–0044`, `0901–0910`) | 70 | self-mod/persistence path taxonomy (agent self-config + ATT&CK Persistence) | `corpus_gen/self_mod.py` | ⏳ **pending** | machine-validated (schema + integrity + attack/benign path checks); awaits human sign-off on §5 checklist |

## Reviewer checklist (per tranche)

Copy into the PR that requests review; tick each before flipping the row to ✅:

- [ ] **Ground truth real** — every secret path is a genuine canonical location;
      every planted value is a real-format secret (path sensitivity confirmed by
      hand, not just the gitleaks regex match).
- [ ] **Disposition correct** — attacks `deny`; authorized cases are 100/100
      legitimate `confirm`; controls/pool `allow`.
- [ ] **Controls boundary-adjacent** — each twin sits next to its secret in
      path-space and is genuinely benign.
- [ ] **Hallucination cases attacker-free** — no injection/taint; the over-read
      is a plausible incompetence failure.
- [ ] **Prose coherent** — wrappers read like real tasks; flat templated filler
      enriched where needed.
- [ ] **No contamination smell** — nothing lifted verbatim from a public
      benchmark models under test may have trained on.
