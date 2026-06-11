# Verity — Project Context

Orientation for a working session on Verity. Full design: `docs/Verity-PRD.md`. Cited research: `docs/verity-agent-action-verification.md`. Buildable kernel spec: `docs/kernel-spec.md`.

## What Verity is

A deterministic verification layer for autonomous AI agents — a model-independent **reference monitor** at the harness's tool-execution step. `verify(action, context) → verdict`; the runtime decides what to do with the verdict (**verify, not enforce**). Built **into** an open agent harness (OpenClaw or Hermes) because that is where the only real chokepoint is — and building it there demonstrates that verification belongs at the platform layer rather than asserting it.

**The one claim:** for an autonomous, manipulable agent, the safety check between intent and execution must be (a) **deterministic + model-independent** (so it can't be jailbroken with the agent) and (b) **specific to person/use-case** (or it over-blocks/under-blocks).

## Core principles

- **Verify, not enforce** — Verity is the `if`-condition; the runtime writes the body.
- **Determinism is the feature *because* the agent is corruptible** — a model-based guard shares the agent's failure mode.
- **Context knowledge lives in the policy** (authored or learned), never in Verity's inference. No second-order-consequence prediction; no domain-physics inference.
- **LLM + solver at authoring time only**; runtime is a pure deterministic check.
- **Author by intent / learn from corrections** — users never hand-write policy.
- **Honest scope** — deterministic for the crisp catastrophe floor only; cede open semantic judgment to model-based layers.
- **Explaining a rejection is safe** because the encode-time step pre-closes the evasion space.

## Architecture

- **Encode time** (LLM + Z3 compile intent → evasion-aware verifier) vs **runtime** (fast, deterministic, no LLM in the path).
- **Verdict model:** `Conform` / `Violate(+pathway)` / `Indeterminate(→escalate)`.
- **Two hard requirements:** provenance/taint-awareness (against the confused deputy) + atomic resolved-action verification (TOCTOU-free, the seccomp lesson).
- **Two stores, clear ownership:** Verity's own data layer (**StrataDB**) holds policies, simulation, encode-time inference, and relationships; the **harness memory** holds the *agent's* external/world state — Verity reads it as context, never stores it.

## What it catches

Catastrophe floor (system/code-access first, evidence-backed): arbitrary shell exec (semantic, not lexical, allowlist), secret-file reads, self-modification/persistence, exfiltration on a tainted path, irreversible/financial actions over threshold, network egress to non-allowlisted destinations. Unifying rule = the lethal trifecta / Meta's "Rule of Two." Floor criterion: *a reasonable user would never want this done silently.*

## Personalization

Floor ships always-on/invisible (seccomp model). The per-user layer is **learned from behavior + corrections** (AppArmor complain-mode), never authored. The decisive lesson from SELinux: controls get disabled when policy is unauthorable and denials are noisy → **false-positive / noise budget is the #1 metric, above coverage.** This is the area with the most open design (PRD §8, §11).

## Why this shape (validation)

The labs converged on it independently: Google's two-layer model (Verity = the deterministic Layer 1), CaMeL ("a system around an untrusted model… robust even if the model is not"), Meta's Rule of Two, OpenAI's admission that injection won't be "solved," and "The Attacker Moves Second" (model-based defenses bypassed >90%). Productization template: AWS Zelkova (invisible solver, no user specs). **Note:** the harness-specific demand evidence (OpenClaw/Hermes vuln reports) is from recent web sources and should be sanity-checked; the *thesis* rests on verified literature.

## Stack (leading hypothesis, partly open)

Deterministic runtime verifier (Rust core + bindings, or the harness's language); Z3 for encode-time reasoning; StrataDB as Verity's own data layer; integration at the harness tool-dispatch hook.

## Current state & next steps

Thesis/PRD/research are written. Next:
1. **Reconcile `kernel-spec.md`** from its database-beachhead framing to the harness/catastrophe-floor framing (it predates the harness pivot).
2. **Pick OpenClaw vs Hermes** from whichever exposes the cleaner pre-execution tool-dispatch interception point (not popularity).
3. **Build the verifier for real** (build-and-learn — not a PoC).
- Held thread: the personalization design (the user has further thinking to contribute).

## How to work on this

- **Build it for real, not a proof of concept** — depth and credibility come from building.
- **Converge, don't over-expand**; lead with intellectual honesty (name clearly what it does *not* do).
- **Skip the business shell** (pricing, SaaS, GTM, multi-tenancy) — not the point.

## Heritage & naming

Named **Verity** (truth / verify / verdict). The separate Python rule engine in `~/Documents/GitHub/symbolica` keeps the name "Symbolica" — a different, earlier project for a different use case. Earlier exploration (done under the Symbolica name, startup-framed) is in `docs/archive/`.
