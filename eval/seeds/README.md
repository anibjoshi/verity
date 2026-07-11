# Vendored seed corpora — provenance & license ledger

The E5 corpus is a **measuring instrument**: every downstream number (baseline
catastrophe rate, verifier coverage, over-block budget) is read against it. So
its *ground truth* — the concrete secret path, the real dangerous command, the
attacker host — must come from **curated real sources**, never from an LLM
(corpus-spec §8.1). This directory holds those sources, vendored and pinned, so
the generators in `eval/verity_eval/corpus_gen/` can derive ground truth
deterministically and reproducibly.

**License rule (corpus-spec §8.4):** permissive/MIT only. **Avoid** trufflehog
(AGPL) and R-Judge (CC BY-NC). Verify per-repo before vendoring. Each source
below records its license, the exact pin, and the SHA-256 of the vendored file.

## Ledger

| Source | Used for | License | Pin | Vendored file | SHA-256 |
|---|---|---|---|---|---|
| [gitleaks](https://github.com/gitleaks/gitleaks) `config/gitleaks.toml` | `secret_read` — anchors every planted secret value to a real detector rule (222 rules) | MIT (Zachary Rice) | tag `v8.30.1` → commit `83d9cd684c87d95d656c1458ef04895a7f1cbd8e` | `gitleaks/gitleaks.toml` | `e163e53b9e7e8a8511e77271e2b323ed057759542a6d988258afe3a1fa329caf` |

Planned (not yet vendored — subsequent E5 tranches):

| Source | Used for | License | Notes |
|---|---|---|---|
| [NL2Bash](https://github.com/TellinaTool/nl2bash) | `shell_exec` — real command payloads | GPLv3 → **verify redistribution terms; data may differ from code license** | corpus-spec §8.2 |
| [InterCode](https://github.com/princeton-nlp/intercode) (bash, corrected) | `shell_exec` — task shells | MIT | needs the human "correct InterCode" step (§8.4) |
| [GTFOBins](https://github.com/GTFOBins/GTFOBins.github.io) / [LOLBAS](https://github.com/LOLBAS-Project/LOLBAS) | `self_mod` — living-off-the-land binaries | verify per-repo (GTFOBins content = CC-BY? confirm) | corpus-spec §8.2 |
| [NotInject / InjecGuard](https://github.com/SaFoLab-WISC/InjecGuard) | benign trigger-word pool (`floor_class: none`) | MIT | 339 samples, expand by template |

> The planned rows are recorded here so the license check is a standing gate, not
> a last-minute scramble. A source moves from *planned* to the main ledger only
> once it is vendored, pinned, SHA-recorded, and its license verified.

## What the generators do with these

The ground truth is derived mechanically, and re-verified against the real
artifact before any scenario is written:

- **gitleaks → `secret_read`.** For each anchoring rule, `corpus_gen` holds a
  real-format token **in memory only**, assembled from fragments so no complete
  token appears as a literal in source. `generate.verify_secret_values`
  re-compiles the rule's regex from the pinned `gitleaks.toml` and asserts that
  token matches — "is this really a secret?" is answered by the vendored detector.
  The corpus then ships a **redacted placeholder** at the secret path, and
  `verify_redacted_safe` asserts the committed content matches no provider rule.
  Net: the corpus proves it can plant a genuine secret and proves it commits none
  — so nothing live-format lands in the repo to trip downstream scanners.

## Refreshing a pin

Bumping a pin is a deliberate act (it changes ground truth): update the pin +
SHA here, re-run the generator's ground-truth check, regenerate the affected
tranche, and refresh `eval/corpus/CORPUS.lock`.
