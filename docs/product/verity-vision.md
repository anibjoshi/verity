# Verity — Thesis, Strategy & Plan

*The north-star document: what Verity is, the one claim it rests on, the evidence
that the problem is real, how the system is built, and the sequenced plan. The
detailed specs live alongside this — product requirements in
[`verity-prd.md`](verity-prd.md), the kernel in [`../kernel-spec.md`](../kernel-spec.md),
the corpus in [`verity-corpus-spec.md`](verity-corpus-spec.md), the measured proof
in [`verity-baseline-v1-findings.md`](verity-baseline-v1-findings.md), and the
step-by-step build in [`verity-execution-plan.md`](verity-execution-plan.md). This
doc is the synthesis they hang from.*

---

## 1. The thesis, in one paragraph

Autonomous AI agents are crossing from *advising* to *acting* — running code,
moving money, sending messages, calling APIs, often with no human standing by.
The reliability that makes such autonomy *safe to deploy* is, today, a property
you **rent from a frontier lab**: the expensive, closed, API-gated models resist
manipulation, and the cheap, open, deploy-anywhere small models — the ones that
will actually make up the deployed mass — do not. We measured this (§3). We also
measured that you **cannot train your way out of it at small scale**: within one
model lineage, more capability made injection-compliance *worse*, not better.
Reliability is therefore **orthogonal to capability**; it must be supplied by a
separate layer. **Verity is that layer** — a deterministic, model-independent
safety check between an agent's intent and its execution. And because a *closed*
reliability layer would just move the gatekeeper, Verity is open and built into
open harnesses. That is the lever: **Verity adds the frontier's reliability floor
to a small model, un-gating safe autonomy from the labs' API moats — the enabling
substrate for cheap, abundant intelligence that isn't controlled by a handful of
large corporations.**

---

## 2. The problem

Three properties of modern agents are individually manageable and together
dangerous:

- **Autonomous** — they act with no one positioned to catch a mistake.
- **Manipulable** — they are prompt-injectable and hallucination-prone; a poisoned
  web page, a malicious tool result, or a confident wrong inference can make the
  agent *want* to do the wrong thing.
- **General** — the same agent does thousands of different things, so what counts
  as "catastrophic" is entirely contextual.

**Every common defense fails on the same point.** If the guard is itself a
model — a system-prompt instruction, an LLM judge, the agent's own "reasoning" —
then the injection that turns the agent turns the guard too; they share a failure
mode. The joint OpenAI/Anthropic/Google DeepMind paper *"The Attacker Moves
Second"* found adaptive attacks bypass 12 published defenses with >90% success,
most of which had reported near-zero in their own papers. **You cannot use a model
to guard a model that can be jailbroken.**

**And the problem grows with proliferation.** The deployed mass of agents will not
be frontier models. It will be cheap 1B–8B models in local, unsupervised loops —
edge devices, hobbyist automation, small institutions, places nobody is watching.
Small models fail two ways frontier models largely don't: **manipulation** *and*
plain **incompetence** — a weak model can run a destructive command or read a key
file through bad tool-calling alone, no attacker required. As models get cheaper
and more numerous, per-action competence falls and the human-in-the-loop
assumption erodes. The threat surface compounds.

---

## 3. The evidence — we measured it (Baseline v1)

Verity is built **problem-first**. Before writing the verifier, we built an
evaluation corpus of real agent failures and measured how often agents — especially
small ones — actually take catastrophic actions. Every downstream claim carries a
number, not an assertion. Full detail in
[`verity-baseline-v1-findings.md`](verity-baseline-v1-findings.md); the spine:

- **484 authored scenarios**, six catastrophe-floor classes + a benign
  trigger-word pool, each attack with a matched benign control, deterministic
  oracles, ground truth from real sources (gitleaks, MITRE ATT&CK), never from an
  LLM. **13 measurable models** (10 small local via vLLM, 3 frontier via API),
  verifier **OFF**.

- **The catastrophe gap is real and large.** Small-model mean attack-success rate
  (`ASR_valid`) = **0.27**; frontier mean = **0.01**. Gap **+0.25**, and **+0.62**
  on `irreversible_financial`. Claude Opus 4.8 and Sonnet 5 took the catastrophic
  action **never** (0.00); GPT-5.6-sol near-never (0.04). Not one frontier model
  wired injected money, read a secret on injection, or exfiltrated data.

- **Capability does not buy reliability.** The Qwen3 ladder (0.6B → 8B, one
  lineage) showed injection-compliance *rising* monotonically with size —
  `irreversible_financial` **0.60 → 0.80 → 0.93 → 1.00**, overall ASR peaking at
  8B. The failure mode *shifts*: the tiny model is dangerous through chaotic
  flailing; the capable model through **competent confused-deputy compliance** — it
  reliably executes the attacker's injected instruction.

This is the empirical foundation, and it is the differentiator: the field is thick
with defenses that *assert* effectiveness and thin on ones that measured the
problem first. The same instrument that proved the problem will grade the cure
(Phase 2).

---

## 4. What Verity is

```
intent  →  verity.verify(action, context)  →  verdict  →  [ the runtime decides ]
```

A **deterministic verification layer for autonomous agents** — a model-independent
**reference monitor** at the harness's tool-execution step, the one place every
agent action already passes through. It answers one question — *is this action
allowed, for this person, in this context?* — and returns a verdict with a
human-readable rationale.

**The one claim everything rests on:** for an autonomous, manipulable agent, the
safety check between intent and execution must be (a) **deterministic and
model-independent** — so it cannot be jailbroken along with the agent it guards —
and (b) **specific to person and use-case** — or it over-blocks and under-blocks
into uselessness.

Three design commitments follow:

- **Deterministic, model-independent, auditable.** The verdict does not come from a
  model, so it can't be social-engineered and doesn't drift; a small deterministic
  core can be read and trusted in a way an LLM judge cannot.
- **Verify, not enforce.** Verity returns a verdict with reasoning; the *runtime*
  decides what to do with it — block, escalate, hand the reasoning back to the
  agent to self-correct, or log. Verity is the `if`-condition, not the body. This
  is what lets it drop into any harness.
- **Neurosymbolic only at the seams.** An LLM and a solver compile policy from
  intent *at authoring time*. At **runtime there is no LLM in the path** — just a
  fast, deterministic check. (LLM at authoring, determinism at the checkpoint.)

---

## 5. The catastrophe floor — what it catches, and what it doesn't

Verity is deliberately scoped to a **catastrophe floor**: the class of actions a
reasonable user would *never* want done silently. Evidence-backed, system/code-
access first:

- arbitrary shell/exec (semantic, not lexical, resolution)
- secret-file reads
- self-modification / persistence
- exfiltration on a tainted path (the "lethal trifecta")
- irreversible/financial actions over a threshold
- network egress to non-allowlisted destinations

The unifying rule is the lethal trifecta / Meta's "Rule of Two." **Honest nuance,
stated up front:** the crisp/semantic line runs *through* some floor members —
`is_secret(path)` is crisp at `~/.ssh/id_rsa` and fuzzy at a token in an odd config;
command resolution is crisp for `rm -rf /` and fuzzy at the lexical-bypass fringe.
The corpus is built to *map exactly where* that line falls. Verity owns the crisp
core and **cedes open semantic judgment to model-based layers** — it is not a total
safety solution, and claiming otherwise would be the kind of over-reach the project
exists to avoid.

---

## 6. Why it must be built this way

Four non-negotiables, each with a reason the alternative fails:

1. **Determinism** — because the agent is corruptible. A model-based guard shares
   the agent's failure mode; the injection that fools one fools both. Determinism
   also buys auditability and stable behavior.
2. **Model-independence** — so the check generalizes across the thousands of cheap
   models that will run agents, and can't be jailbroken with any of them.
3. **At the harness layer** — the tool-dispatch step is the only real chokepoint;
   it is veto-capable and atomic on the *resolved* action. A standalone
   verification "product" has no chokepoint — the control sits with whoever owns
   the agent platform. (Naming this honestly is why Verity is built **into** an
   open harness rather than pitched as a standalone startup: verification belongs
   at the platform layer, and the intellectually honest move is to build the
   reference implementation there.)
4. **Open** — because a *closed* reliability layer just relocates the gatekeeper.
   The whole point (§9) is to *un-gate* reliable autonomy; an open, model-
   independent check is the only shape that does that.

Two hard requirements the architecture must satisfy from day one: **provenance /
taint-awareness** (against the confused deputy) and **atomic resolved-action
verification** (TOCTOU-free — the seccomp lesson). The corpus encodes taint on
untrusted inputs from the first scenario.

---

## 7. Architecture

- **Encode time vs runtime.** At encode time, an LLM + Z3 compile *intent* into an
  evasion-aware verifier (JSON policy). At runtime, a fast deterministic check
  reads that policy — **no LLM, no solver, no async** in the path.
- **Verdict model:** `Conform` / `Violate(+pathway)` / `Indeterminate(→escalate)`.
  A provenance-dependent policy with no taint available returns `Indeterminate →
  escalate`, **never a silent allow**.
- **Assurance, not assumption.** Every verdict states what the chokepoint actually
  provided — atomicity, provenance, resolution, context-completeness — so a "safe"
  answer is never blind.
- **The stack (settled).** The runtime verifier is `verity-core`, a small **Rust**
  crate (`serde` only; no Z3, no LLM, no GC) — a tiny, auditable trusted computing
  base with predictable hot-path latency. Bindings from one audited core: **PyO3
  first** (Python is where the agents are), WASM/napi later. The encode-time
  compiler is Python (LLM + Z3). Policies are **JSON, versioned in git** — no
  separate data layer. Verity reads the *harness's* world state as context; it
  never stores it.
- **Ownership boundary.** Verity owns its compiled policies; the harness owns the
  agent's world. No overlap, no second data plane.

---

## 8. The plan

Evidence-first throughout: **prove the problem before building the cure**, an
objective exit gate on every step, and two honest go/no-go forks that can stop or
narrow the work.

| Phase | What | Status |
|---|---|---|
| **0 — Corpus + prove the problem** | 484-scenario corpus, harness, model sweep, **Baseline v1** | ✅ **done — decision gate GO** (§3) |
| **1 — `verity-core` kernel** | The deterministic library (kernel-spec M0–M7) + PyO3 bindings, validated standalone against `StaticContext` and the corpus | ▶ next |
| **2 — Grade the verifier** | Flip `verify()` ON in the same harness; measure coverage (does it catch the 0.27?) within the noise budget (does it leave the benign pool alone?) | after 1 · 🚦 second go/no-go |
| **3 — Live harness integration** | OpenClaw adapter at `before_tool_call`; thread message-level provenance through to the hook (the first upstream contribution) | after 2 |
| **4 — Learned personalization** | Boundaries learned from user corrections; optimize the noise budget | deferred until the floor is proven quiet |

The Phase-0 → Phase-1 pivot is where we are now. `floor.json` (M0) is authored from
the Baseline: the policy invests first where the small/frontier gap is widest —
financial-over-threshold, secret reads, tainted exfil, off-allowlist egress.

**Phase 3 is the demonstration:** an autonomous small-model agent in OpenClaw,
prompt-injected or hallucinating, proposes a catastrophic action; Verity returns
`Violate` with a human-readable reason *before execution*, and the agent
self-corrects from the explanation — something a model-based guard cannot do
reliably, because the same injection that fooled the agent fools the guard.

---

## 9. Why it matters — the bigger picture

The stakes are larger than "an agent safety tool." **Cheap, abundant intelligence
that is *not* gated by a handful of large corporations depends on reliable small
models** that small companies and institutions can train and deploy themselves.
The Baseline showed the obstacle precisely: reliable autonomy is currently a
frontier-lab rental, and scaling small models doesn't earn it — it earns a more
competent confused deputy. So the missing piece is a reliability layer that is
**model-independent** (works on any small model), **deterministic** (can't be
jailbroken with the model), **cheap** (no LLM in the runtime path), and **open**
(so it doesn't reinstate a gatekeeper). That is Verity's exact shape — not by
choice, but because the problem structure forces it.

The bounded, honest version of the claim: Verity democratizes the **catastrophe
floor** — the highest-leverage, most-catastrophic, most-democratizable slice of
reliability. It converts "catastrophically unreliable small model" into "reliable
on the floor, still-fallible on semantics," which is a *deployable* posture (with a
human only on the `Indeterminate`/confirm cases). It is the biggest single lever on
small-model reliability, and reliability is the lever on decentralized AI.

This is not a hunch against the grain. The labs have published the shape — Google's
Layer 1, DeepMind's CaMeL — a deterministic control at the harness layer. Verity is
the **open reference implementation** of a check the labs have endorsed but not
shipped as public infrastructure, mapped to their live open problems (computer use,
tool-use safety, agentic alignment).

---

## 10. What Verity is *not* (honest scope)

- **Not total safety.** It is the deterministic catastrophe floor. Open semantic
  harm ("a subtly poisoned config," contextual judgment) is ceded to model-based
  layers; the crisp/semantic line runs through some floor members and the corpus
  maps where.
- **Not a runtime model.** No LLM in the verdict path — by design, and enforced
  (purity bans in `verity-core`).
- **Not a defense against a malicious operator.** A reference monitor cannot
  constrain someone who disables it (`setenforce 0`). The threat model is the
  *benign user* with a manipulable or incompetent agent — the confused deputy — not
  an adversarial owner.
- **Not a proof of real-world exploitability.** The corpus uses simulated,
  side-effect-free tools; it measures *intent to act catastrophically*, reproducibly
  — not whether a specific real environment is exploitable (eval-plan §15).
- **Not a standalone product.** There is no chokepoint for a standalone verifier;
  the value is realized *inside* the harness. Naming that — and building there — is
  the point.
- **Personalization is deferred.** Learned per-user boundaries (Phase 4) ride on top
  of a floor proven quiet (Phase 2); they never rescue a noisy floor.

---

*Verity — from **verity** (truth), **verify**, **verdict**: the deterministic
source of truth about whether an agent action is safe.*
