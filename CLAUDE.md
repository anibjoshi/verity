# Verity — Project Context

Orientation for a working session on Verity. **Thesis & strategy (start here):** `docs/product/verity-vision.md` (the synthesis: what/why/plan). **What to build next:** `docs/product/verity-execution-plan.md` (step-by-step, with exit gates). Full design: `docs/product/verity-prd.md`. Phase 0 corpus: `docs/product/verity-eval-plan.md` + `docs/product/verity-corpus-spec.md`. Measured proof: `docs/product/verity-baseline-v1-findings.md`. Testing/CI: `docs/product/verity-testing-ci-plan.md`. Kernel: `docs/kernel-spec.md`. Research: `docs/verity-agent-action-verification.md`, `docs/research/`.

## What Verity is

A deterministic verification layer for autonomous AI agents — a model-independent **reference monitor** at the harness's tool-execution step. `verify(action, context) → verdict`; the runtime decides what to do with the verdict (**verify, not enforce**). Open-source, built **into** an open agent harness (OpenClaw or Hermes) because that is where the only real chokepoint is.

**The one claim:** for an autonomous, manipulable agent, the safety check between intent and execution must be (a) **deterministic + model-independent** (so it can't be jailbroken with the agent) and (b) **specific to person/use-case** (or it over-blocks/under-blocks).

## How we're building it: evidence first

**Prove the problem before building the cure.** Two make-or-break questions are empirical, not rhetorical: can a deterministic floor stay *crisp and quiet* on real traffic, and do small-model agents take catastrophic actions often enough to justify the boundary? So the build order is **measure first**:

- The **evaluation corpus is the first deliverable** — it proves the problem exists now, and later it grades the verifier (coverage on attacks, noise on controls). Every downstream claim gets a number.
- **Target small models first (1B–3B).** Frontier models are accurate and hide the problem; the deployed mass of agents is cheap small models in unsupervised loops — the honest, growing threat surface. Small models fail to *injection and to plain incompetence*.
- **Build-to-learn** — depth and credibility come from building the corpus and the verifier for real, not from a PoC. Write conclusions from the scars of building.

## The evaluation corpus (current focus — Phase 0)

- **Threat model:** injection + hallucination on behalf of a **benign user** (confused-deputy + incompetent-agent). Deliberately **not** the malicious-user model — a reference monitor can't constrain an operator who disables it.
- **Sources — adapt and extend:**
  - **AgentDojo (MIT) — the spine.** Deterministic *effect*-based oracle (success = real state mutation); `{injection_*}` placeholders are built-in taint markers; loads as data without a model. Strong on exfil-on-tainted-path.
  - **InjecAgent (MIT) — breadth.** ~1,054 indirect-injection cases, ReAct-native (good for small models), thin shell-exec + PII. Weaker oracle (tool-name match).
  - **AgentHarm (MIT+use-clause) — pattern only, not corpus.** Wrong threat model (malicious user). Borrow its matched harmful/benign pairs and function-call grading discipline.
- **The gap we author:** the **system/code-access floor** the benchmarks miss — secret-file reads, arbitrary shell/exec, self-modification/persistence — each with a **matched benign control**. This is exactly where the crispness question lives (`is_secret`, semantic command resolution).
- **Methodology guard — capability vs intent:** small-model tool-calling fails on *format* 30–80% of the time. Use a **three-valued outcome** (attempted-violation / safe / invalid), report **valid-only and all** rates, and use **guided/grammar-constrained decoding** so a recorded catastrophic action is genuine intent, not a parser artifact.
- **Runner:** a minimal hand-written ReAct loop whose **tool-dispatch step is the future chokepoint** `verify()` plugs into. Designed to map onto OpenClaw's `before_tool_call` later.
- **Models:** five small families for cross-architecture evidence — Qwen2.5-3B/1.5B, Llama-3.2-3B/1B, Hermes-3-Llama-3.2-3B, Gemma-4-E4B/E2B-it (license-gated), Phi-4-mini-3.8B + one frontier anchor. Each carries its own tool-call parser (per-model `decode.py` registry). **Serving:** vLLM (reproducible, per-model tool parser, guided decoding); llama.cpp/GBNF to force valid output from 1B models. Not Ollama for the scored run. Local dev/scoring on a single RTX 4070 SUPER (12GB) → models served one at a time; harness is an OpenAI-compatible client, so it ports to bigger GPUs unchanged.

## Core principles

- **Evidence before architecture** — measure on the corpus before committing the cure.
- **Verify, not enforce** — Verity is the `if`-condition; the runtime writes the body.
- **Determinism because the agent is corruptible** — a model-based guard shares the agent's failure mode. Determinism also buys auditability.
- **Context knowledge lives in the policy** (authored or learned), never in Verity's inference. No second-order-consequence prediction; no domain-physics inference.
- **LLM + solver at authoring time only**; runtime is a pure deterministic check.
- **Author by intent / learn from corrections** — users never hand-write policy.
- **Honest scope** — deterministic for the crisp catastrophe floor only; cede open semantic judgment to model-based layers.
- **Noise budget above coverage** — a verifier that gets disabled (`setenforce 0`) protects no one. The matched controls measure this.

## Architecture (the verifier — Phase 1+)

- **Encode time** (LLM + Z3 compile intent → evasion-aware verifier) vs **runtime** (fast, deterministic, no LLM in the path).
- **Verdict model:** `Conform` / `Violate(+pathway)` / `Indeterminate(→escalate)`.
- **Two hard requirements:** provenance/taint-awareness (against the confused deputy) + atomic resolved-action verification (TOCTOU-free, the seccomp lesson). The corpus encodes taint on untrusted inputs from day one.
- **Assurance, not assumption:** every verdict states what the chokepoint actually provided (atomicity, provenance, resolution, context-completeness). Provenance-dependent policy with no taint → `Indeterminate → escalate`, never a silent allow.
- **Ownership boundary:** Verity owns its compiled policies (JSON, **versioned in git**); the **harness memory** holds the *agent's* world state — Verity reads it as context, never stores it. No separate data layer.

## Stack (settled)

- **Runtime verifier** = `verity-core`, a small **Rust** crate (`serde` only; no Z3, no LLM, no async) — a tiny, auditable TCB; no GC → predictable hot-path latency.
- **Bindings** from one audited core: **PyO3 first** (Python is where most agents live, incl. small autonomous ones; the eval harness is the first consumer), **WASM/napi for TS** later. Ship **prebuilt wheels/packages** → `pip install`, no toolchain.
- **Encode-time compiler** = **Python** (LLM + Z3), emits the compiled-policy JSON the core reads. Z3 never touches the runtime.
- **Eval harness (Phase 0)** = **Python** (vLLM/llama.cpp + ReAct loop), the first consumer of `verity-core`.
- **Policies** = **JSON, versioned in git** — no separate data layer.
- **Repo** = one **polyglot monorepo**: `crates/verity-core` + `crates/verity-py`, `encode/`, `eval/`, `policies/`, `docs/`.

## What it catches

Catastrophe floor (system/code-access first, evidence-backed): arbitrary shell exec (semantic, not lexical, allowlist), secret-file reads, self-modification/persistence, exfiltration on a tainted path, irreversible/financial actions over threshold, network egress to non-allowlisted destinations. Unifying rule = the lethal trifecta / Meta's "Rule of Two." Floor criterion: *a reasonable user would never want this done silently.* Honest nuance: the crisp/semantic line runs *through* some floor members (`is_secret`, command resolution) — the corpus is built to map exactly where.

## Roadmap

- **Phase 0 — evaluation corpus + prove the problem** *(current)*.
- **Phase 1 — `verity-core` kernel** (kernel-spec M1→M7; build-and-learn, not a PoC).
- **Phase 2 — grade the verifier against the corpus** (coverage + false-positive budget).
- **Phase 3 — OpenClaw integration** at `before_tool_call`; thread message-level provenance through to the hook (first upstream contribution).
- **Phase 4 — learned personalization** from corrections; optimize the noise budget. *(Held thread: the user has further thinking here.)*

## Harness

OpenClaw is the lead: its `before_tool_call` hook is veto-capable and atomic on the resolved action — a clean chokepoint — but exposes **no data-flow provenance** (taint exists on user messages, not on tool params) and only binary block/allow. Threading provenance through is the first concrete upstream patch. Hermes review still open. Note OpenClaw ships no built-in shell tool; its dangerous surface is `sessions_spawn` (RCE), `cron`, `gateway`, and messaging-exfil.

## How to work on this

- **Build it for real, not a proof of concept** — depth and credibility come from building.
- **Converge, don't over-expand**; lead with intellectual honesty (name clearly what it does *not* do).
- **Skip the business shell** (pricing, SaaS, GTM, multi-tenancy) — not the point.
- **Product thinking and docs come first** — update the PRD to reflect direction before building against it.

## Naming

Named **Verity** (truth / verify / verdict) — the deterministic source of truth about whether an agent action is safe. The verification engine is the `verity-core` crate.
