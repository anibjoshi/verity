# Baseline v1 — Findings (Phase 0 exit)

*The evidence the problem is real, measured — the published result of the E5→E7
pipeline (corpus → sweep → baseline). Verifier **OFF**: this is unguarded
agent behavior. Methodology + reproduction recipe live in
[`verity-baseline-v1.md`](verity-baseline-v1.md); the raw table regenerates from
`eval/results/` via `python -m verity_eval.report`.*

**Corpus:** 484 authored scenarios, v1.0 (six floor classes + benign trigger-word
pool). **Models:** 13 measurable (10 small local + 3 frontier API); Gemini 3.1 Pro
attempted but rate-limited on the available key. **Decode:** small models under
guided/forced decoding (`tool_choice=required`); frontier under `auto` (Anthropic
rejects `required`; frontier tool-call rate 0.60–0.93 confirms they engage).

## The one-line result: the decision gate is a clear GO

> **Small-model mean `ASR_valid` = 0.27. Frontier mean = 0.01. Gap = +0.25**,
> and **+0.62 on `irreversible_financial`.** Small models take catastrophic floor
> actions often; frontier models resist them almost perfectly. Both halves of the
> Phase-0 go/no-go are empirically true. → **Phase 1.**

`ASR_valid` = attack-success rate excluding format-invalid trajectories (the honest
catastrophe rate). A model whose tool-calling the harness can't extract is flagged
**not measurable**, never scored as a false zero (the capability-floor confound).

## The small models (10 measurable, verifier OFF)

| model | tc | ASR_v | invalid | benign over-action | over-refusal |
|---|--:|--:|--:|--:|--:|
| Qwen3-8B (fp8) | 0.99 | **0.49** | 0.01 | 0.31 | 0.26 |
| Qwen2.5-1.5B | 0.99 | 0.47 | 0.01 | 0.75 | 0.28 |
| Qwen3-1.7B | 0.92 | 0.38 | 0.08 | 0.50 | 0.30 |
| Qwen3-4B | 0.99 | 0.36 | 0.01 | 0.30 | 0.26 |
| Qwen3-0.6B | 0.97 | 0.34 | 0.03 | 0.56 | 0.31 |
| Llama-3.2-3B | 0.94 | 0.33 | 0.06 | 0.51 | 0.35 |
| Qwen2.5-3B | 1.00 | 0.17 | 0.00 | 0.42 | 0.31 |
| Hermes-3-3B | 0.86 | 0.07 | 0.14 | 0.11 | 0.46 |
| Llama-3.2-1B | 0.98 | 0.06 | 0.02 | 0.67 | 0.43 |
| Phi-4-mini | 0.99 | 0.01 | 0.01 | 0.34 | 0.48 |

Catastrophe rates span **1%–49%**. And it is not just the model "being dumb":
even the models that resist take real floor actions on specific classes, and every
model over-acts on 11–75% of benign trigger-word tasks and over-refuses 26–48% of
*legitimate* high-stakes actions — the noise budget the verifier must respect.

## Capability does not buy reliability — the Qwen3 size ladder

Holding architecture and training regime fixed, scaling Qwen3 **0.6B → 8B**:

| Qwen3 | ASR_v | **financial** | secret_read | tainted_exfil | invalid | benign over-action |
|---|--:|--:|--:|--:|--:|--:|
| 0.6B | 0.34 | 0.60 | 0.20 | 0.19 | 0.03 | 0.56 |
| 1.7B | 0.38 | 0.80 | 0.13 | 0.40 | 0.08 | 0.50 |
| 4B | 0.36 | 0.93 | 0.26 | 0.44 | 0.01 | 0.30 |
| 8B | **0.49** | **1.00** | 0.65 | 0.50 | 0.01 | 0.31 |

Two curves move in opposite directions. **Incompetence falls** (invalid 0.03→0.01;
benign over-action 0.56→0.31 — the bigger model flails less). **Compliant
catastrophe rises** — `irreversible_financial` climbs **monotonically
0.60→1.00**, and overall ASR **peaks at 8B**. The failure mode *shifts*: the tiny
model is dangerous through chaotic flailing (it repeats `transfer` six times
because it can't decide to stop); the capable model is dangerous through
**competent confused-deputy compliance** — it reliably, correctly executes the
attacker's injected instruction. Scaling small models does not close the gap. It
buys a more effective deputy.

## The frontier ladder resists — the decisive comparison

| anchor | tc | ASR_v | financial | secret_read | tainted_exfil |
|---|--:|--:|--:|--:|--:|
| claude-opus-4-8 | 0.72 | **0.00** | 0.00 | 0.00 | 0.00 |
| claude-sonnet-5 | 0.60 | **0.00** | 0.00 | 0.00 | 0.00 |
| gpt-5.6-sol | 0.93 | 0.04 | 0.00 | 0.00 | 0.00 |

**Small mean − frontier mean, per floor class:**

| class | small | frontier | **gap** |
|---|--:|--:|--:|
| irreversible_financial | 0.62 | 0.00 | **+0.62** |
| net_egress | 0.29 | 0.02 | +0.26 |
| secret_read | 0.26 | 0.00 | +0.26 |
| shell_exec | 0.31 | 0.05 | +0.26 |
| tainted_exfil | 0.16 | 0.00 | +0.16 |
| self_mod | 0.10 | 0.00 | +0.10 |

Not one frontier model wired injected money, read a secret on injection, or
exfiltrated data. Opus and Sonnet take the catastrophic action **never**;
GPT-5.6-sol near-never. (Claude's lower `tc` is resistance, not incapacity — when
it declines it declines in prose, scored safe; when it acts, it never picks the
catastrophe.)

## What it means

**Reliable autonomy is, today, a property you rent from a frontier lab.** The
cheap, open, deploy-anywhere small models are exactly the ones that fall; the
frontier models resist. And the Qwen3 ladder proves you cannot train your way out
of it at small scale — reliability is orthogonal to capability, so it must be
supplied by a **separate, model-independent layer**. To democratize rather than
re-gate, that layer must be open and deterministic. That is the empirical case for
Verity: it is the lever that adds the frontier's reliability floor to a small
model, un-gating safe autonomy from the labs' closed API moats.

The floor Verity targets is exactly where the gap is widest — financial actions
over threshold, secret-path reads, tainted exfiltration, off-allowlist egress.
Phase 2 will flip `verify()` ON in the same harness and grade whether it closes
that 0.25 without spending the noise budget.

## Honest caveats

- **Decode-config asymmetry** — small under `required`, frontier under `auto`. But
  frontier `tc` (0.60–0.93) shows they engage, and the gap (0.27 vs 0.01) is far
  too large for a decode artifact to explain.
- **Gemini 3.1 Pro rate-limited** on the available key (tc 0.02, flagged
  non-measurable, excluded from the gap). A higher-quota key would add a fourth
  frontier point; the three anchors already make the pattern unambiguous.
- **Gemma-4** absent (does not fit 12 GB on vLLM; the llama.cpp GGUF route is
  set-up work, not yet done).
- **Provisional** until the corpus clears human review (`REVIEW.md`) and
  `CORPUS.lock` is frozen for the v1 release. Simulated tools measure *intent to
  act*, not real-environment exploitability (eval-plan §15).
