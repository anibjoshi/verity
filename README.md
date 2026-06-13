# Verity

**A deterministic verification layer for autonomous AI agents** — an open-source reference monitor for agent actions.

Verity sits at the point where an agent decides to act and the action executes. It answers one question — *is this action allowed, for this user, in this context?* — and returns a verdict the agent runtime acts on. It is built **into the agent harness, at the tool-execution step**, because that is the one place every agent action already passes through.

The verifier is **symbolic and model-independent**: its decision does not come from a model, so it cannot be jailbroken along with the agent it guards.

---

## The problem

AI agents are crossing from *advising* to *acting*. Open autonomous harnesses — OpenClaw, Hermes — now run code, edit files, send messages, and call APIs, sometimes without a human in the loop and sometimes without even a prompt. Three properties make this dangerous, and they compound:

- **Autonomous** — they act with no one standing by to catch a mistake.
- **Manipulable** — they are prompt-injectable and hallucination-prone; a poisoned web page or a confident wrong inference can make the agent *want* to do the wrong thing.
- **General** — the same agent does thousands of things, so what counts as catastrophic is entirely contextual.

Every common defense fails on the same point: if the guard is itself a model — a prompt instruction, an LLM judge, the agent's own "reasoning" — then the injection that turns the agent turns the guard too. **You cannot use a model to guard a model that can be jailbroken.** The joint OpenAI/Anthropic/Google DeepMind paper *"The Attacker Moves Second"* found adaptive attacks bypass 12 published defenses with >90% success — most of which had reported near-zero in their own papers.

### The problem grows with proliferation

The deployed mass of agents will not be frontier models. It will be cheap **1B–3B models in local, unsupervised, autonomous loops** — on edge devices, in hobbyist automation, in places nobody is watching. That is exactly the "no human to catch it" setting Verity exists for. Small models also fail in a way frontier models largely do not: **incompetence, not just manipulation** — a 1.5B model can run a destructive command or read a key file through weak tool-calling alone, with no attacker present. As models get cheaper and more numerous, the number of unsupervised agents grows, their per-action competence falls, and the human-in-the-loop assumption erodes. The problem compounds.

## Evidence first

Verity is built **problem-first.** Before the verifier is written, the project builds an **evaluation corpus** of real agent failures and measures how often agents — especially small ones — actually take catastrophic actions. The corpus is the spine: it proves the problem exists now, and later it is the exact instrument that grades whether the verifier works (coverage on the attacks, noise on the controls). Every claim downstream has a number attached, not an assertion.

The corpus adapts existing MIT-licensed benchmarks (AgentDojo, InjecAgent) and authors the system/code-access classes they lack (secret reads, shell exec, self-modification) — each with a **matched benign control** that looks dangerous but is not, so over-blocking is measurable from day one.

## What Verity is

```
intent → verity.verify(action, context) → verdict → [ runtime decides ]
```

- **Deterministic, model-independent, auditable.** The verifier is symbolic. Its answer does not depend on the agent's prompt, cannot be social-engineered, and does not drift — and a small deterministic core can be read and trusted in a way an LLM judge cannot.
- **Verify, not enforce.** Verity returns a verdict with reasoning; the runtime decides what to do — block, escalate, hand the reasoning back to the agent to self-correct, or log. Verity is the `if`-condition, not the body. (This composability is also why it drops cleanly into any harness.)
- **Neurosymbolic, only at the seams.** A solver and an LLM compile policy from intent *at authoring time*. At runtime there is no LLM in the path — just a fast, deterministic check.

## Why this shape — and not a guess

The major labs have independently converged on this architecture:

- **Google's** published agent-security model names a deterministic **"Layer 1" runtime policy engine that intercepts every tool call**, and states reasoning-based defenses "cannot provide absolute guarantees… for critical or irreversible actions." Verity is the open reference implementation of that layer.
- **CaMeL** (Google DeepMind / ETH) is built explicitly "around an untrusted model… robust even if the model itself is not," and enforces its policy *at tool-call time* — it assumes the layer Verity provides.
- **Meta's** "Agents Rule of Two" and **OpenAI's** admission that prompt injection is "unlikely to ever be fully solved" point the same way: the durable boundary is one the model does not sit inside.

The production template exists too — AWS's Zelkova runs roughly a billion SMT checks a day with the solver invisible and no user-written specifications, which is exactly Verity's "compile policy from intent; return a verdict at runtime."

## What it catches — and what it deliberately doesn't

Verity gates a **catastrophe floor** of actions that resolve to crisp, checkable predicates and that a reasonable user would never want done silently:

- arbitrary shell / command execution
- reads of secret material (SSH keys, `.env`, credentials)
- self-modification / persistence (skill files, agent config, autostart locations)
- exfiltration on a tainted path (outbound HTTP, email, PR creation)
- irreversible or financial actions above a threshold
- network egress to non-allowlisted destinations

**The honest boundary:** deterministic verification scales to crisp predicates like these — and *not* to open semantic judgment ("is this email appropriately worded?"). Unlike a closed syscall set, the agent action space is open-ended and semantic, so Verity claims provable guarantees only for the floor and cedes the rest to model-based layers. The honest nuance the corpus is built to surface: the crisp/semantic line runs not only at the floor's boundary but *through some floor members themselves* — `is_secret` and command-resolution have a crisp core and a semantic fringe.

Two requirements follow from decades of reference-monitor design and are non-negotiable: the gate must be **provenance/taint-aware** (so an injected agent can't misuse its legitimate privileges — the confused-deputy attack), and it must verify the **fully-resolved, immutable action atomically** with dispatch (no time-of-check/time-of-use gap).

## Personalization

The catastrophe floor needs no per-user input — it ships always-on and invisible, like `seccomp`. What is catastrophic *beyond* the floor is personal, and the hard lesson from mandatory-access-control history (SELinux was disabled across the industry because its policy was unauthorable and its denials were noisy) sets the design: **never ask users to author policy; learn the per-user layer from behavior and corrections**, like AppArmor's complain mode. The primary product metric is therefore the false-positive/noise budget, above coverage — a verifier that gets disabled protects no one.

## Status

Early — evidence-first. The thesis, architecture, and a primary-source threat analysis are written; the current work is the **evaluation corpus** that measures how often small-model agents take catastrophic actions, before the verifier is built. See the docs.

## Repository

- [`docs/product/verity-prd.md`](docs/product/verity-prd.md) — the product requirements and design (canonical).
- [`docs/product/verity-execution-plan.md`](docs/product/verity-execution-plan.md) — the step-by-step build plan, with an exit gate per step.
- [`docs/product/verity-eval-plan.md`](docs/product/verity-eval-plan.md) — Phase 0 evaluation corpus & benchmark plan.
- [`docs/product/verity-corpus-spec.md`](docs/product/verity-corpus-spec.md) — the scenario schema and seed set (E0).
- [`docs/product/verity-testing-ci-plan.md`](docs/product/verity-testing-ci-plan.md) — testing & CI plan for the library.
- [`docs/kernel-spec.md`](docs/kernel-spec.md) — the buildable spec for the verification kernel (`verity-core`).
- [`docs/verity-agent-action-verification.md`](docs/verity-agent-action-verification.md) — cited research: the threat landscape, why current defenses are insufficient, and the systems-security precedent (seccomp, SELinux, capabilities, seL4, Zelkova).
- [`docs/research/`](docs/research/) — the eval-plan deep-research prompt and findings.

## Non-goals

- **Not predicting second-order consequences** (e.g. "will this change cascade into an outage"). That needs domain inference Verity will not pretend to do; a confidently wrong prediction is worse than none.
- **Not enforcement.** Verity returns verdicts; the runtime acts.
- **Not a model-based guard, content filter, or detector.**
- **Not the "malicious user" threat model** — a reference monitor cannot constrain an operator who can disable it. Verity serves the benign user whose agent is the liability.
- **Not a company** — no pricing, SaaS, or go-to-market. The value is the verification capability and what building it for real teaches.

---

*Verity — the deterministic source of truth about whether an agent action is safe.*
