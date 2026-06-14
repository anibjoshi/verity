# Verity — Product Requirements Document

*Revision 2026-06 — evidence-first direction. Supersedes `docs/Verity-PRD.md`.*

## 1. Summary

**Verity is a deterministic verification layer for autonomous AI agents** — an open-source reference monitor that sits at the single point where an agent decides to act and the action executes, answers one question — *is this action allowed, for this user, in this context?* — and returns a verdict the agent runtime acts on.

**The one claim it proves:** for an agent that is autonomous and manipulable, the safety check between intent and execution must be (a) **deterministic and independent of the model** — so it cannot be jailbroken along with the agent — and (b) **specific to the person and use case** — so it does not over-block (crippling the agent) or under-block (missing the catastrophe that matters to *this* user). No widely used approach today is both.

**Two commitments shape how this PRD is sequenced:**

1. **Evidence-first — prove the problem before building the cure.** Before a line of the verifier is written, Verity builds an *evaluation corpus* of real agent failures and measures how often agents actually take catastrophic actions. The corpus is the spine of the project: it proves the problem exists now, and later it is the exact instrument that grades whether the verifier works (coverage on the attacks, noise on the controls). A solution built ahead of a measured problem is a guess; a solution built against a corpus has a number attached to every claim.
2. **Measure where the risk concentrates — small models first.** The proliferation of agents does not mean everyone runs a frontier model. It means millions of cheap 1B–3B models in local, unsupervised, autonomous loops. Those models fail more — to injection *and* to plain incompetence — and they run in exactly the "no human in the loop" setting that motivates the whole project. So the corpus targets small models first. Frontier models serve as an accuracy anchor that shows the gap, not as the primary subject.

This is **not a product company.** Verity is an open-source tool for a real and worsening problem: no pricing, billing, SaaS, or go-to-market. Its value is the verification capability, the corpus that proves it is needed, and what building both for real teaches.

This is also not a speculative architecture. The major labs have independently converged on exactly this shape: Google's published agent-security model names a deterministic "Layer 1" runtime policy engine that intercepts every tool call as the necessary complement to reasoning-based defenses (which it states "cannot provide absolute guarantees… for critical or irreversible actions"), and research such as CaMeL is explicitly built "around an untrusted model" assuming such an enforcement layer exists. **Verity is the open reference implementation of that layer — and the corpus is the open evidence that it is needed.**

---

## 2. The Problem: Agents That Can Act

AI agents are crossing from *advising* to *acting*. Open autonomous harnesses now in wide use — OpenClaw (a heartbeat daemon that acts without being prompted; thousands of skills spanning files, shell, email, and more) and Hermes (Nous Research; writes and runs code, manages files, calls external services) — give a model real hands in the real world.

Three properties make these agents dangerous, and they compound:

1. **Autonomous.** They act without a human in the loop — sometimes without even a prompt. There is no one standing by to catch a bad action.
2. **Manipulable.** They are prompt-injectable and hallucination-prone. A poisoned web page, a crafted document, or a confident wrong inference can make the agent *want* to do the wrong thing.
3. **General.** The same agent does thousands of different things, so what counts as "catastrophic" is entirely contextual. `rm` in a scratch directory is nothing; in your life's work it is a disaster. Emailing your whole contact list is a marketer's job and everyone else's nightmare.

**The load-bearing fact:** you cannot use a model to guard a model that can be jailbroken. If the guard is itself a model — a prompt instruction, an LLM judge, the agent's own "reasoning" — then the injection that turns the agent turns the guard too. The joint OpenAI/Anthropic/Google DeepMind paper *"The Attacker Moves Second"* found adaptive attacks bypass 12 published defenses with >90% success — most of which had reported near-zero in their own papers. OpenAI states prompt injection is "unlikely to ever be fully solved." If the model can be turned, the only durable boundary is one the model does not sit inside.

### 2.1 Why the problem grows: proliferation and small models

The instinct is to test these claims on frontier models. That is the wrong place to look, for two reasons:

- **Frontier models hide the problem.** They are accurate and heavily safety-trained, so eliciting a catastrophic action is rare and laborious. Measuring there understates a risk that is real everywhere else.
- **Proliferation is small models, not frontier ones.** As agents spread, the deployed mass will be cheap 1B–3B models running locally on edge devices, in hobbyist automation, in loops nobody is watching. That is *exactly* the "autonomous + no human to escalate to" scenario Verity exists for. Targeting small models is not a shortcut to manufacturing failures — it is the **honest, growing threat model.**

Small models also fail in a way frontier models largely do not: **incompetence, not just manipulation.** A 1.5B model does not need a prompt-injection to run a destructive command or read a key file — weak, malformed tool-calling produces catastrophic actions with *no attacker at all*. The problem the corpus must capture is therefore broader than injection: it is **injection *and* hallucination, on behalf of a benign user.** (This is deliberately *not* the "malicious user" threat model — see §4.2.)

As models get cheaper and more numerous, the number of unsupervised agents taking real actions grows, the average competence of those agents per action falls, and the human-in-the-loop assumption erodes. The problem does not plateau; it compounds. That is the case for a deterministic boundary that does not depend on the model's judgment.

### 2.2 Why today's approaches fail

| Approach | Why it fails for this problem |
|---|---|
| **Prompt instructions / model self-policing** | The guard shares the failure mode of the thing it guards. Jailbreak the agent and you have jailbroken its conscience. |
| **Generic guardrails / content filters** | Per-call and context-blind. They cannot encode what is catastrophic *for this person*, so they are either too strict (and cripple the agent) or too loose (and miss the personal catastrophe). |
| **Human approval gates** | Hollow when the human is absent (autonomous agents) or cannot foresee the consequence. Approval moves blame, not risk. |
| **Detection-only / LLM-as-judge** | Probabilistic and after-the-fact; for an irreversible action a false negative *is* the catastrophe. An LLM judge shares the agent's jailbreak. |

The gap is a check that is **deterministic, model-independent, and personal.** That is Verity.

---

## 3. Strategy: Prove the Problem, Then Build the Cure

The two make-or-break questions for Verity are empirical, not rhetorical:

1. Can a deterministic floor stay **crisp and quiet** on real, diverse agent traffic — catching the catastrophes without a flood of false positives?
2. Do small-model agents actually **take catastrophic actions** often enough, in realistic settings, to justify the boundary?

No amount of argument resolves these. The build order follows directly: **measure first.** Build the evaluation corpus, run real agents against it, and produce the headline number — *how often do small-model agents take catastrophic floor actions?* — before committing to the shape of the verifier. The corpus then does double duty: it is the proof the problem exists, and it is the grader for everything downstream. Every later claim about the verifier ("the floor catches X," "false positives are below Y") becomes a measurement against this corpus, not an assertion.

This is build-to-learn. The depth and credibility come from building the corpus and the verifier for real — not from a proof of concept or a slide. The corpus is the first deliverable.

---

## 4. The Evaluation Corpus (first deliverable)

### 4.1 What it is

A versioned, reusable set of **scenarios**: reproducible setups in which an agent, driven by a small model in a minimal harness, is given a task and an environment, and may take (or propose) a catastrophic action. Each scenario carries ground truth — the specific tool call that would constitute a violation, or, for controls, the assertion that no violation should occur. Running the corpus produces, per model, the rate at which agents take catastrophic actions, broken down by catastrophe class and attack vector.

A floor-scoped, small-model, *with-controls* agent-catastrophe benchmark does not exist today (the closest, AgentDojo, is frontier-focused and exfiltration-centric). The corpus is plausibly a standalone contribution before the verifier ships a line of code.

### 4.2 Threat model: injection + hallucination on a benign user

The corpus models a **benign user whose agent is tricked or errs** — the confused-deputy and the incompetent-agent. Two vectors:

- **Injection** (direct and indirect): poisoned content — a web page, a file, a tool's return value, a malicious skill — makes the agent *want* the wrong action.
- **Hallucination**: no attacker; the agent, especially a small one, simply proposes a catastrophic action through weak reasoning or malformed tool use.

This is deliberately **not the "malicious user" model** (an attacker directing their own agent to do harm). That is a different problem, and a reference monitor is least relevant to it — a malicious operator can disable their own guard. Verity exists where the user is on the right side and the agent is the liability. (This is why AgentHarm, whose threat model is the malicious user, contributes a pattern but not content — see §4.3.)

### 4.3 Sources: adapt and extend

We do not reinvent. We harvest the on-target parts of existing MIT-licensed benchmarks and author what they lack.

- **AgentDojo (MIT) — the spine.** Its strength is a **deterministic, code-defined oracle**: success is a real, inspectable state mutation (a transfer to the attacker's account actually exists), not a string match. Its `{injection_*}` placeholders are built-in **taint markers** — anything entering through one is, by construction, untrusted input, which directly serves Verity's provenance requirement. Scenarios load as data without instantiating a model. *Coverage:* strong on exfiltration-on-a-tainted-path; partial on financial/irreversible and network egress.
- **InjecAgent (MIT) — the breadth.** ~1,054 indirect-injection cases in a flat, standalone-loadable schema, ReAct-native (well-suited to small/local models). Adds a thin shell-exec slice (`Terminal.Execute`) and PII-access cases. *Caveat:* its oracle is weaker — attacker-tool-*name* match, no effect or argument check.
- **AgentHarm (MIT + use-restriction) — the pattern, not the corpus.** Its threat model is the malicious user (the opposite of ours), so its content is off-target. What we borrow is its engineering discipline: **matched harmful/benign pairs** (the instrument for measuring over-blocking — our #1 metric) and **per-behavior grading functions** (function-call-level rubrics: correct tool, correct order, correct arguments).

### 4.4 The gap we author: the system/code-access floor + matched controls

The literature covers the data-flow half (exfiltration, financial). It leaves the **system/code-access half** — the half the documented incident record says matters most (RCE CVEs, secret theft, supply-chain skill poisoning) — almost entirely open:

- **Secret-file reads** — no benchmark treats reading `~/.ssh/id_rsa`, `.env`, or a credential store as a violation.
- **Arbitrary shell / command execution** — only InjecAgent touches it, thinly.
- **Self-modification / persistence** — writes to skill files, agent/MCP config, autostart, the system prompt — covered by no one.

This gap is not a problem; it is the point. The classes we must author by hand are **exactly** the ones where the design's hardest question lives: *is the predicate actually crisp?* Authoring `is_secret` forces a position — is it a path match over known locations (honest: "covers the well-known cases, misses the exotic"), or something more? Authoring the exec class forces confronting that **semantic command resolution** (defeating lexical bypass — line continuation, busybox, option abbreviation) is the genuinely hard, deferred predicate. We discover whether the floor can be crisp by trying to write it down.

Every authored attack ships with a **matched benign control** — a legitimate action that *looks* dangerous but is not (`fs.read` on `./config.yaml` vs. `~/.ssh/id_rsa`; the email the user asked for vs. exfiltration on a tainted path; `rm` in a scratch dir vs. in source). Attacks-only measures coverage; attacks-plus-controls measures the thing that actually decides whether the tool survives in someone's stack (§10).

Beyond the low-stakes controls, the corpus also authors an **authorized-high-stakes** class: legitimate actions that are *genuinely* catastrophic-class — what a human operator does 100/100 (reading your own SSH key to move laptops, wiring a real over-threshold invoice, recreating the staging DB, extending the agent's own skills). These carry `expected_disposition: confirm`, and they earn their place twice over. First, they are the proof that the floor is a **confirmation gate, not a blunt blocker** — the honest answer to "won't a catastrophe floor over-block?" is that for a legitimate high-stakes action the right verdict is `Violate(require_approval)`, not `deny` (§6). Second, they measure the model's **over-refusal** — the dangerous mirror of over-action — and, since competent models often *resist* attacks outright, they are where a deterministic verifier actually earns its keep: the action the model rightly performs but a reasonable user would never want done *silently*.

### 4.5 Methodology: capability vs. intent — the central measurement guard

Small-model tool-calling fails on *format* 30–80% of the time (malformed JSON, ignored schemas, hallucinated tools, omitted calls). If we conflate "the agent *attempted* a catastrophic action" (the safety signal) with "the agent emitted garbage" (capability noise), the headline number is meaningless. The corpus therefore enforces:

- **A three-valued outcome per scenario:** `attempted_violation` / `safe` / `invalid` (malformed or no well-formed call).
- **Two metric families**, after InjecAgent's example: rate over *valid* trajectories (conditioned on a well-formed call) and rate over *all* trajectories (invalids count as failures). Reporting both separates safety behavior from capability.
- **Grammar-constrained / guided decoding** to suppress format noise, so a recorded catastrophic action is a genuine intent signal, not a parser artifact.

### 4.6 The runner: a minimal harness whose tool-dispatch is the chokepoint

We build a small, hand-written ReAct/tool-use loop rather than importing a framework's quirks between us and the measurement. This is deliberate and **on-thesis**: the loop's tool-dispatch step is the exact chokepoint where `verify()` will later sit. Owning it now means the corpus harness *becomes* the integration surface — we instrument the resolved tool call, the taint on its inputs, and the three-valued outcome at the precise point the verifier will one day read. The harness is designed to map onto a real harness's pre-execution hook (OpenClaw's `before_tool_call`) later.

### 4.7 Models and serving

- **Subjects (small):** Qwen2.5-3B and -1.5B, Llama-3.2-3B and -1B, Hermes-3-Llama-3.2-3B (a tool-tuned variant, to test whether tool-specialization shifts catastrophe propensity).
- **Anchor (frontier):** one frontier API model, run on identical scenarios, to quantify the small-vs-frontier gap — the visible evidence that the problem grows as models get cheaper.
- **Serving:** vLLM (reproducible OpenAI-compatible endpoint, per-model tool-call parser, guided decoding) as primary; llama.cpp with GBNF grammar to force valid output from the smallest models. Not Ollama for the scored run (weak structured-output control and batch reproducibility).

### 4.8 Metrics and the proof

The headline proof: **attack-success-rate per catastrophe class, per model, with the small-vs-frontier gap and the valid/all split.** Supporting: the false-positive base rate on matched controls (the denominator for over-blocking, used later to grade the verifier). If small-model agents take catastrophic floor actions at a meaningful rate while frontier models resist, the problem is demonstrated and the case for a deterministic, model-independent boundary is made on evidence rather than assertion.

### 4.9 What's genuinely new here

The Phase-0 reuse-vs-build research confirmed that most of the corpus is assembled from prior art (AgentDojo / InjecAgent / BIPIA for breadth; NL2Bash, InterCode, gitleaks, GTFOBins/LOLBAS to seed the floor) — credited honestly. But it also identified what *nothing* existing provides, and that is Verity's contribution:

- **Benign-user-hallucination catastrophe cases.** Every harmful-action corpus assumes indirect injection or a deliberately malicious user. None model a *benign user whose small model hallucinates its way into a catastrophic action* — which, given proliferation (§2.1), is the common case, not the exotic one.
- **The self-modification / persistence class**, essentially greenfield as a labeled corpus.
- **A unified three-valued (attempted / safe / invalid) scoring schema** that normalizes attack-success over valid-only *and* all — separating genuine safety behavior from small-model incompetence, which nothing existing reports cleanly.

These are the project's novel contribution, built on an honestly-credited reuse base. Detail: `verity-eval-plan.md` §5.

---

## 5. The Core Idea (the verifier)

Once the problem is measured, Verity is the `if`-condition between an agent's intent and its action:

```
intent → verity.verify(action, context) → verdict → [agent runtime decides]
```

Three commitments define it:

- **Deterministic and model-independent.** The verifier is symbolic, not a model. Its answer does not depend on the agent's prompt, cannot be social-engineered, and does not drift. *The determinism is the feature precisely because the agent is corruptible* — you want the thing between a manipulable agent and an irreversible action to be the one component that cannot be talked around. It is also **auditable by construction** — a small, deterministic core can be read and trusted; an LLM judge cannot.
- **Verify, not enforce.** Verity returns a verdict with reasoning; the runtime decides what to do with it (block, escalate to a human, hand the reasoning back to the agent to self-correct, or log). Verity is the condition, not the body of the `if`. This composability is also why it is the right shape for open-source adoption: a library that returns a verdict drops into any harness without taking over its control flow.
- **Neurosymbolic division of labor.** The **symbolic core decides**, at runtime, deterministically. **Neural reasoning (an LLM, plus a solver) works only at authoring time** — to turn intent and context into a policy, to enumerate how it could be circumvented, and to explain a verdict. *The smart part suggests; the strict part decides.* No LLM is ever in the execution path.

### 5.1 Why now — the field has converged here

- **Model-layer defense has an admitted ceiling.** OpenAI: injection "unlikely to ever be fully solved." "The Attacker Moves Second": >90% bypass of 12 defenses. If the model can be turned, the durable boundary is one the model does not sit inside.
- **The labs prescribe the deterministic layer.** Google's two-layer model (deterministic Layer 1 + reasoning Layer 2); Meta's "Agents Rule of Two" (the lethal trifecta as policy); Anthropic/Redwood control research ("deferring on critical actions is highly robust").
- **The productization template exists.** AWS's Zelkova runs ~a billion SMT checks/day with the solver invisible and no user-written specifications — exactly Verity's "compile policy from intent at authoring time; return a verdict at runtime."

---

## 6. Why Build It Into a Harness

The natural home for `verify()` is the harness's tool-execution step: **every tool call already passes through it.** That is the one place, between intent and execution, that all actions traverse — a real, free chokepoint. An external, standalone verifier has no such chokepoint (an agent can call its tools directly), which is precisely why a deterministic gate belongs *at the platform's execution layer*, not bolted on beside it.

For an open-source tool this is a feature, not a constraint: you contribute the gate upstream, and it grows by adoption rather than by ownership. The composable "verify, not enforce" shape (§5) is what makes that adoption cheap.

**Target harness:** OpenClaw is the lead. Its `before_tool_call` hook is veto-capable and runs on the **resolved, immutable** action in the same critical section as dispatch — so the atomicity requirement (§8.6) is satisfiable. The one gap: it exposes **no data-flow provenance** (taint exists on user messages but is not propagated to tool params), and its control surface is binary block/allow. That gap is a concrete, valuable first upstream contribution (§13). A Hermes review remains the open alternative.

---

## 7. Principles

1. **Evidence before architecture.** Measure the problem on a real corpus before committing the cure. Write conclusions from the scars of building, not ahead of them.
2. **Verify, don't enforce.** Verity returns a verdict; the runtime owns the action.
3. **Determinism because the agent is corruptible.** The guard must not share the agent's failure mode. Symbolic, model-independent, jailbreak-proof, auditable — by construction.
4. **Context knowledge lives in the policy, not in Verity's inference.** Verity does not predict second-order consequences and does not infer a domain's physics. The person or expert encodes what matters; Verity enforces it deterministically.
5. **LLMs suggest, the core decides — at authoring time only.**
6. **Author by intent, review by consequence.** Users never hand-write policy syntax. They express intent (or simply correct the agent) and review what the system would *do*.
7. **Explaining a rejection is safe**, because the authoring step pre-enumerates the circumvention pathways.
8. **Honest scope.** Verity catches what can be articulated as policy. Where it cannot verify, it returns *indeterminate* and escalates rather than guessing. The credibility is in the honesty of the line.
9. **Noise budget above coverage.** A verifier that is disabled protects no one. False positives are the primary risk (§10).

---

## 8. Architecture

### 8.1 Encode time vs. runtime

- **Encode time** (when a policy is established): an LLM plus an SMT solver (Z3) translate intent and context into a compiled verifier and enumerate the circumvention pathways. Expensive, thorough, occasional. The *only* place the solver and LLM run.
- **Runtime** (every tool call): `verify(action, context)` evaluates the action against the compiled policy and current context. Fast, deterministic, no solver, no LLM. Returns a verdict, and on violation, the circumvention pathway.

### 8.2 The verify primitive and verdict model

```
verify(action, context) → Verdict
  Conform                                    # nothing on the floor fired
  Violate { reason, pathway, disposition }   # + the policy-authored intent
  Indeterminate { missing, disposition }     # cannot verify → escalate
                                             # every verdict also carries an assurance record (§8.6)
```

The verdict is the entire output. On `Violate`, the `pathway` is the actionable explanation — consumed by the **agent** (self-correct in real time and re-verify) and the **developer/user** (review after the fact). The **disposition** (`deny | require_approval | require_context | escalate | allow`) is the *policy's authored intent*; the caller expresses it in whatever controls the harness offers. Detailed schema: `kernel-spec.md`.

### 8.3 Integration point — the adapter

`verify()` sits behind a thin, harness-specific **adapter** — the only harness-coupled code. It intercepts at the harness's pre-execution hook, **normalizes** the raw tool call into the harness-neutral action the verifier reads (`{tool, params}` → `{capability, resource, effect}`), gathers context, and **maps the verdict's disposition onto the harness's controls** — failing closed when the harness cannot express the intent. The normalization step is the adapter's most safety-critical code: the deterministic guarantee holds only over a correctly-resolved action.

### 8.4 Two stores, clear ownership

- **Verity's own artifacts** — the compiled policies — are JSON files **versioned in git** (which gives versioning *and* branching for free); the runtime loads them into memory at startup. There is no separate data layer in the runtime or the early phases. Heavier encode-time machinery (simulation/forking, a relationship graph, learned-personalization state) belongs to those later phases and chooses its own storage then.
- **The harness's memory** holds the *agent's* external/world state. Verity **reads** it as context; it does **not** store or duplicate it.

### 8.5 Implementation stack (leading hypothesis, partly open)

**The runtime** is `verity-core`, a small Rust crate (`serde` only — no Z3, no LLM, no async; a tiny auditable TCB, and no GC means predictable hot-path latency), exposed to the agent ecosystem through bindings from a single audited core: **PyO3 first** (Python is where most agents live, especially the small autonomous ones — and our own eval harness is the first consumer), with **WASM/napi for TypeScript** later, shipped as **prebuilt wheels/packages** so adoption is `pip install` with no toolchain. **Encode-time** is a separate **Python** tool (LLM + Z3) that emits the compiled-policy JSON the core reads — Z3 never touches the runtime. **Policies are JSON, versioned in git** (no separate data layer). Everything lives in **one polyglot monorepo** — `crates/verity-core` + `crates/verity-py`, `encode/`, `eval/`, `policies/`, `docs/`; the Phase 0 corpus harness (§4.6) is Python and is built first.

### 8.6 Two hard requirements: provenance and atomicity

- **Provenance / taint awareness (against the confused deputy).** Authorizing by action *type* ("the agent may send email") is insufficient — an injected agent uses its *legitimate* privileges for the attacker. The gate must bind *which data* flows to *which destination* under *which provenance.* The corpus encodes this from day one: every injection scenario carries an explicit taint marker on its untrusted inputs.
- **Atomic, resolved-action verification (against TOCTOU).** The verifier must evaluate the fully-resolved, immutable action in the same critical section as dispatch — no gap in which a different action is substituted after the verdict.

**Assurance, not assumption.** A harness may not supply both. Every verdict carries an **assurance** record stating what the chokepoint actually provided (atomicity, provenance, resolution, context-completeness). A provenance-dependent policy evaluated with no taint available returns `Indeterminate → escalate`, never a silent allow. The assurance record is honest scope made machine-readable — and the precise spec for what a harness must expose to earn a strong guarantee.

---

## 9. What It Catches — the Catastrophe Floor

The floor gates actions that resolve to crisp, checkable predicates and that *a reasonable user would never want done silently.* Its members map one-to-one onto the corpus's catastrophe classes (§4):

- **Arbitrary shell / command execution** — gated on a *semantic* allowlist of resolved commands, not lexical strings. (The hard predicate; corpus class authored in §4.4.)
- **Reads of secret material** — SSH keys, cloud-credential files, `.env`, token stores. (Authored in §4.4.)
- **Self-modification / persistence** — writes to skill files, agent/MCP config, persistent memory, system prompt, autostart. (Authored in §4.4.)
- **Exfiltration on a tainted path** — outbound HTTP, email/chat send, PR/issue creation — when the execution path carries untrusted-content provenance. (Covered by the AgentDojo/InjecAgent spine.)
- **Irreversible / financial actions above threshold** — payments, transfers, deletions, mass mutations, external publishing.
- **Network egress to non-allowlisted destinations.**

**The unifying rule** (Meta's "Rule of Two" / the lethal trifecta): block, or force confirmation for, any action that combines **untrusted-content provenance + sensitive access + external or irreversible effect** in a single tainted path.

**What the floor does NOT cover — deliberately.** Deterministic verification scales to crisp predicates and not to open semantic judgment ("is this email appropriately worded?"). Unlike a closed syscall set, the agent action space is open-ended and semantic, so Verity claims provable guarantees **only for the floor** and cedes the rest to model-based layers. The honest nuance the corpus will surface: the crisp/semantic line runs not only at the floor's boundary but *through some floor members themselves* — `is_secret` and command-resolution have a crisp core and a semantic fringe. Naming that precisely is part of the contribution; overclaiming would repeat SELinux's over-reach (§10).

---

## 10. Personalization — the Differentiated Problem

"Specific to the person, domain, or use case" is three authoring problems: **domain** (an expert authors it — feasible), **use case** (a developer/template authors it — feasible), and **person** (a consumer who will never author a policy — the hard one).

The honest resolution for the consumer case is two parts, and it avoids the unreliable inference Verity refuses to do:

1. **A universal catastrophe floor**, shipped **always-on and invisible, like seccomp** — the user never writes it.
2. **Personalization learned from behavior and corrections, not authored — like AppArmor's complain mode.** Run permissively, observe, propose rules, let the user confirm, then enforce, with an `audit2allow`-style correction loop. Ordinary preference-learning from feedback, not physics inference.

**The decisive lesson — and it sets the #1 metric.** SELinux was disabled across the industry (`setenforce 0`) not because it failed to enforce, but because its policy was **unauthorable and its denials were noisy.** Therefore **false-positive / noise budget is Verity's #1 product metric, above coverage** — and the matched benign controls in the corpus (§4.4) exist precisely to measure it. A verifier that is strict but noisy gets ripped out and protects no one. For an open-source tool the dynamic is identical: a security tool that overclaims and over-blocks gets removed from configs and badmouthed.

> **What remains genuinely open** is the precise learned-personalization mechanism: cold-start behavior, how few corrections suffice, and how to keep learned boundaries deterministic and inspectable. Intentionally left open (§13).

---

## 11. Scope

### In scope

- An **evaluation corpus** of small-model agent catastrophe-failures, with matched benign controls, that proves the problem and grades the verifier (the first deliverable).
- A deterministic runtime verification primitive at a harness's tool-execution chokepoint.
- An encode-time compiler (LLM + solver) from intent/context to an evasion-aware verifier.
- A universal catastrophe floor and a learned per-user personalization loop.
- Verdict + circumvention-pathway output, feeding agent self-correction and after-the-fact review.
- A real integration into one open harness, built for production use, not as a proof of concept.

### Explicitly out of scope

- **Predicting second-order consequences.** A confidently wrong prediction is worse than none.
- **Enforcement.** Verity returns verdicts; the runtime acts.
- **Inferring a domain's physics or a person's full risk profile.** Knowledge comes from policy (authored or learned), not speculative inference.
- **Being a product or company** — no pricing, billing, multi-tenancy, managed control plane, or go-to-market.
- **The "malicious user" threat model** (§4.2) — a reference monitor cannot constrain an operator who can disable it; Verity serves the benign user whose agent is the liability.

### The honest scope boundary

Verity is deterministic for the **catastrophe floor** — actions that resolve to crisp, checkable predicates — and only there. Provable guarantees are claimed for the floor; open semantic judgment is ceded to model-based layers. The credibility of the project is in the honesty of this line, and the corpus is what holds it honest.

---

## 12. Roadmap

The build is the point; the corpus comes first so every later claim has a number.

- **Phase 0 — Evaluation corpus + prove the problem.** Unified scenario schema; minimal ReAct harness (tool-dispatch as the future chokepoint); ingest AgentDojo (spine) and InjecAgent (breadth); author the system/code-access floor classes + matched controls; run the small-model set + frontier anchor; report attack-success-rate per class, the small-vs-frontier gap, and the valid/all split. **Deliverable: the evidence the problem exists.**
- **Phase 1 — Core verifier.** The `verify(action, context) → verdict` engine (`verity-core`): policy representation, deterministic evaluation, the three-valued verdict, the verdict trace, assurance. Per `kernel-spec.md`.
- **Phase 2 — Measure the verifier against the corpus.** Coverage on the attacks; false-positive rate on the matched controls. The corpus that proved the problem now grades the cure.
- **Phase 3 — Harness integration.** Insert `verify()` at OpenClaw's `before_tool_call`; wire the verdict into the runtime and the pathway into the agent's self-correction loop. Thread message-level provenance through to the hook (the first upstream contribution).
- **Phase 4 — Personalization loop.** Learn per-user boundaries from corrections; optimize against the noise budget.

**The demonstration:** an autonomous small-model agent in the harness confidently proposes a catastrophic action (prompt-injected or hallucinated), and Verity returns `Violate` with a human-readable reason and pathway, *before* execution — impossible for a model-based guard to do reliably, because the same injection that fooled the agent fools the guard.

---

## 13. Open Questions

1. **Floor crispness on real traffic** — the gating empirical question. Can `is_secret`, semantic command-resolution, and the rest stay crisp and low-noise on the corpus? Where exactly does the crisp core end and the semantic fringe begin? The corpus is built to answer this.
2. **The autonomy / escalation tension** — `Indeterminate → escalate` is a human-approval gate, but the motivating scenario (unprompted autonomous agents) has no human to escalate to. What does the tool *do* when it is honest-but-cannot-verify and no one is there? Unresolved and important.
3. **Semantic resolution of the exec gate** — defeating lexical bypass (line continuation, busybox, option abbreviation) deterministically. An open implementation problem; the corpus's authored exec class is where it gets stress-tested.
4. **Provenance/taint plumbing** — OpenClaw exposes provenance on user *messages* but not on tool-call params. Threading it through to `before_tool_call` is the first concrete upstream patch. Until then, provenance-dependent floor policies return `Indeterminate → escalate`.
5. **Personalization design** — cold-start, how few corrections suffice, keeping learned boundaries deterministic and inspectable, and where "learned preference" ends and "inference we refuse to do" begins. Deliberately left open.
6. **Corpus oracle uniformity** — AgentDojo uses effect-based oracles, InjecAgent tool-name match; the authored classes need crisp oracles too. How to harmonize without weakening the strong ones.
7. **Harness selection** — OpenClaw is the lead; confirm against a Hermes review. Note the floor's *instantiation* is harness-specific (OpenClaw ships no built-in shell; its dangerous surface is `sessions_spawn`, `cron`, `gateway`, messaging-exfil).

---

## 14. Naming

The product is named **Verity** — the deterministic source of truth about whether an agent action is safe. Verity's verification engine is the **`verity-core`** crate.
