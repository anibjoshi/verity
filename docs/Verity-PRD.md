# Verity — Product Requirements Document

*This document supersedes the earlier `Symbolica-new.md` (archived), which described an earlier, broader product framing under the working name "Symbolica."*

---

## 1. Summary

**Verity is a deterministic verification layer for autonomous AI agents.** It sits at the single point where an agent decides to act and the action executes, answers one question — *is this action allowed, for this user, in this context?* — and returns a verdict the agent runtime acts on.

It is built **into an open agent harness** (OpenClaw or Hermes), because that is where the only real chokepoint for agent actions exists, and because building it there demonstrates the central claim rather than merely asserting it.

**The one claim it proves:** for an agent that is autonomous and manipulable, the safety check between intent and execution must be (a) **deterministic and independent of the model** — so it cannot be jailbroken along with the agent — and (b) **specific to the person and use case** — so it does not over-block (crippling the agent) or under-block (missing the catastrophe that matters to *this* user). No widely used approach today is both.

This is not a speculative bet. The major labs have independently converged on exactly this architecture: Google's published agent-security model names a deterministic "Layer 1" runtime policy engine that intercepts every tool call as the necessary complement to reasoning-based defenses (which it states "cannot provide absolute guarantees… for critical or irreversible actions"), and research such as CaMeL is explicitly built "around an untrusted model" assuming such an enforcement layer exists. **Verity is the reference implementation of that layer.**

---

## 2. The Problem: Agents That Can Act

AI agents are crossing from *advising* to *acting*. Open autonomous harnesses now in wide use — OpenClaw (~100k GitHub stars; a heartbeat daemon that acts without being prompted; thousands of skills spanning files, shell, email, smart-home, and more) and Hermes (Nous Research; writes and runs code, manages files, calls external services) — give a model real hands in the real world.

Three properties make these agents dangerous, and they compound:

1. **Autonomous.** They act without a human in the loop — sometimes without even a prompt. There is no one standing by to catch a bad action.
2. **Manipulable.** They are prompt-injectable and hallucination-prone. A poisoned web page, a crafted document, or a confident wrong inference can make the agent *want* to do the wrong thing.
3. **General.** The same agent does thousands of different things, so what counts as "catastrophic" is entirely contextual. `rm` in a scratch directory is nothing; in your life's work it is a disaster. Emailing your whole contact list is a marketer's job and everyone else's nightmare. Unlocking the front door is fine when you are home.

### Why today's approaches fail

| Approach | Why it fails for this problem |
|---|---|
| **Prompt instructions / model self-policing** | The guard shares the failure mode of the thing it guards. Jailbreak the agent and you have jailbroken its conscience. A probabilistic check on a manipulable agent is not independent of it. |
| **Generic guardrails / content filters** | Per-call and context-blind. They cannot encode what is catastrophic *for this person*, so they are either too strict (and cripple the agent that made the harness worth using) or too loose (and miss the personal catastrophe). |
| **Human approval gates** | Hollow when the human is absent (autonomous agents) or cannot foresee the consequence (a person is not omniscient about second-order effects). Approval moves blame, not risk. |

The gap is a check that is **deterministic, model-independent, and personal**. That is Verity.

---

## 3. The Core Idea

Verity is the `if`-condition between an agent's intent and its action:

```
intent → symbolica.verify(action, context) → verdict → [agent runtime decides]
```

Three commitments define it:

- **Deterministic and model-independent.** The verifier is symbolic, not a model. Its answer does not depend on the agent's prompt, cannot be social-engineered, and does not drift. *The determinism is the feature precisely because the agent is corruptible* — you want the thing between a manipulable agent and an irreversible action to be the one component that cannot be talked around.
- **Verify, not enforce.** Verity returns a verdict with reasoning; the runtime decides what to do with it (block, escalate to a human, hand the reasoning back to the agent to self-correct, or log). Verity is the condition, not the body of the `if`.
- **Neurosymbolic division of labor.** The **symbolic core decides**, at runtime, deterministically. **Neural reasoning (an LLM, plus a solver) works only at authoring time** — to turn a person's intent and context into a policy, to enumerate how that policy could be circumvented, and to explain a verdict in human terms. *The smart part suggests; the strict part decides.* No LLM is ever in the execution path.

### 3.1 Why now — the field has converged here

The case rests on real, published work, not on this document's framing:

- **Model-layer defense has an admitted ceiling.** OpenAI states prompt injection is "unlikely to ever be fully solved" (Dec 2025); the joint OpenAI/Anthropic/Google DeepMind paper "The Attacker Moves Second" shows adaptive attacks bypass 12 recent defenses with >90% success — most of which had reported near-zero in their own papers. If the model can be turned, the only durable boundary is one the model does not sit inside.
- **The labs prescribe the deterministic layer.** Google's two-layer model (deterministic Layer 1 + reasoning Layer 2); Meta's "Agents Rule of Two" (operationalizing the lethal trifecta — untrusted input + sensitive access + state change — as policy); Anthropic/Redwood control research finding "deferring on critical actions is highly robust." Verity builds the Layer-1 reference they each assume.
- **The productization template exists.** AWS's Zelkova/IAM Access Analyzer runs ~a billion SMT checks/day with the solver invisible and no user-written specifications; Certora's SMT-based contract verifier has secured ~$196B in value — both confirm the sweet spot is *deterministic + irreversible + high-stakes + crisp predicate*, which is exactly the agent catastrophe-floor profile (§7).

---

## 4. Why Build It Into a Harness

A standalone, third-party verification layer has a fatal structural weakness: **there is no chokepoint in the harness layer that it can own.** An agent can call its tools directly; nothing forces traffic through an external verifier. (This is the lesson of policy engines that won where a mandatory interception point existed and stalled where they had to be integrated everywhere.)

But *inside* a harness, the chokepoint is real and free: **every tool call already passes through the harness's tool-execution step.** That is the natural home for `verify()` — one place, between intent and execution, that all actions traverse. Building Verity there is not a workaround for the missing chokepoint; it is the demonstration of where verification *belongs*: at the agent platform's execution layer, owned by whoever owns the platform.

**Target harness:** OpenClaw or Hermes. Both are MIT-licensed, widely adopted, take consequential actions, and already maintain per-user local memory (OpenClaw as markdown files; Hermes as an episodic store) — the substrate personalization needs. OpenClaw is the current lean: its unprompted autonomy is the strongest motivation for pre-execution verification, its safety gap is already publicly recognized (a published vulnerability taxonomy; an NVIDIA safety effort), and it exposes an agent-harness plugin SDK. **Final selection is pending a review of each harness's tool-dispatch interception point** — the integration is only as clean as that hook (§11).

---

## 5. Principles

1. **Verify, don't enforce.** Verity returns a verdict; the runtime owns the action. This keeps Verity composable and keeps the developer in control of their own agent.
2. **Determinism because the agent is corruptible.** The guard must not share the agent's failure mode. Symbolic, model-independent, jailbreak-proof — by construction.
3. **Context knowledge lives in the policy, not in Verity's inference.** Verity does not predict second-order consequences and does not infer a domain's physics. The person or expert encodes what matters; Verity enforces it deterministically. (See §9, out of scope.)
4. **LLMs suggest, the core decides — at authoring time only.** Drafting, personalizing, circumvention-search, and explanation are neural; the runtime verdict is purely symbolic.
5. **Author by intent, review by consequence.** Users never hand-write policy syntax. They express intent (or, for consumers, they simply correct the agent), and review what the system would *do* — concrete allowed/blocked cases — not what it says.
6. **Explaining a rejection is safe.** Because the authoring step pre-enumerates the circumvention pathways, the runtime can tell the agent *why* its action was rejected without teaching it a new way to cheat — every alternative evasion is already closed (within the encoded model).
7. **Honest scope.** Verity catches what can be articulated as policy. It does not claim to prevent all harm, and it says so. Where it cannot verify (missing context), it returns *indeterminate* and escalates rather than guessing.

---

## 6. Architecture

### 6.1 Encode time vs. runtime

The product runs in two phases, and keeping them separate is the core design discipline.

- **Encode time** (when a policy or personalization is established): an LLM plus an SMT solver (Z3) translate intent and context into a compiled verifier and enumerate the circumvention pathways. Expensive, thorough, occasional. This is the *only* place the solver and LLM run.
- **Runtime** (every tool call): `verify(action, context)` evaluates the action against the compiled policy and the current context. Fast, deterministic, no solver, no LLM. Returns a verdict, and on violation, the circumvention pathway.

### 6.2 The verify primitive and verdict model

```
verify(action, context) → Verdict
  Conform                          # allowed; runtime proceeds
  Violate { reason, pathway }      # blocked; reason + how it circumvents policy
  Indeterminate { missing }        # cannot verify (context incomplete) → escalate
```

The verdict is the entire output. There is no enforcement action inside Verity. On `Violate`, the `pathway` is the actionable explanation — consumed two ways: by the **agent**, which can self-correct its action in real time and re-verify, and by the **developer/user**, who can review the failure after the fact (e.g. in the harness's trace/memory).

### 6.3 Integration point

`verify()` is inserted at the harness's tool-execution step (OpenClaw plugin SDK / Hermes tool dispatch) — between the agent's decision to act and the action firing. A few lines; no change to the agent's reasoning.

### 6.4 Two stores, clear ownership

Verity has its own data layer, separate from the agent's memory, and the boundary matters.

**Verity's data layer (StrataDB)** holds Verity's own machinery:

- **Policies** — compiled verifiers, versioned and branchable.
- **Simulation** — forking state to run adversarial pathways against a policy and diff the outcomes (gap-finding; §10).
- **Trusted inference** — the encode-time LLM and embedding work (drafting, circumvention search, explanation), run through a controlled, embeddable inference layer rather than an arbitrary external endpoint.
- **Relationships** — the graph of how actions, effects, and entities relate, which the encode-time reasoning constructs and the verifier consults.

These map cleanly onto a multi-primitive store: versioned KV/JSON for policies, branches for simulation, an embedded inference layer, and a graph for relationships.

**The harness's memory** (OpenClaw's markdown files, Hermes's episodic store) holds the *agent's* external state — what it knows about the world, the user, and its tasks. Verity **reads** this as context when it verifies an action, but it does **not** store or duplicate it. Maintaining the agent's world state is the harness's job; maintaining the verification policy and its reasoning substrate is Verity's. (Where the *learned-from-corrections* personalization ultimately lives across these two stores is part of the open personalization design — §8, §11.)

### 6.5 Implementation stack (leading hypothesis, partly open)

A deterministic runtime verifier — a compact engine in the harness's language, or a high-assurance core with bindings (e.g. Rust with Python/TypeScript bindings) if that better fits the integration; Z3 (or an equivalent SMT solver) plus the controlled inference layer for encode-time reasoning; and **StrataDB as Verity's own data layer** (§6.4) for policies, simulation, inference, and relationships — distinct from the harness memory, which holds the agent's external state, not Verity's.

### 6.6 Two hard requirements: provenance and atomicity

Decades of reference-monitor design (seccomp, the object-capability model, CaMeL) impose two non-negotiable constraints. They are requirements, not options:

- **Provenance / taint awareness (against the confused deputy).** Authorizing by action *type* — "the agent may send email" — is insufficient: an injected agent uses its *legitimate* privileges on the attacker's behalf (the confused-deputy attack, Verity's most serious exposure). The gate must bind *which data* flows to *which destination* under *which provenance*, consuming taint metadata from the input side (the CaMeL pattern). Type-only policy is confusable; provenance-aware policy is not.
- **Atomic, resolved-action verification (against TOCTOU).** The verifier must evaluate the fully-resolved, immutable action in the same critical section as dispatch — no gap in which the agent or a race can substitute a different action after the verdict. This is seccomp's time-of-check-time-of-use-free design, applied to tool calls. Verify the ground-truth action parameters, never a description the agent can mutate.

---

## 7. What It Catches

### 7.1 The catastrophe floor — system/code-access first

The documented incident record (RCE CVEs, secret theft, supply-chain skill poisoning) clusters on **system and code-access actions**, not consumer-lifestyle. The floor leads there, and each member resolves to a crisp, checkable predicate:

- **Arbitrary shell / command execution** — gated on a *semantic* allowlist of resolved commands, not lexical strings (lexical allowlists are bypassed by line continuation, busybox multiplexing, and option abbreviation).
- **Reads of secret material** — SSH private keys, cloud-credential files, `.env`, token stores, `/etc/passwd`.
- **Self-modification / persistence** — writes to skill files, agent/MCP config, persistent memory, the system prompt, or autostart locations.
- **Exfiltration on a tainted path** — outbound HTTP, email/chat send, PR/issue creation, image-URL side channels — when the execution path carries untrusted-content provenance.
- **Irreversible / financial actions above threshold** — payments, transfers, deletions, mass mutations, external publishing.
- **Network egress to non-allowlisted destinations.**

**The unifying rule** (Meta's "Rule of Two" / the lethal trifecta): block, or force human confirmation for, any action that combines **untrusted-content provenance + sensitive access + external or irreversible effect** in a single tainted path. **Floor-membership criterion:** *a reasonable user would never want this done silently* — so a denial reads as obviously correct, never as friction (this criterion is what keeps the noise budget low; see §8).

Physical-world (smart-home) and social/impersonation actions are *plausible* floor members but are **not yet supported by the documented incident record** — treat them as candidates, not confirmed.

### 7.2 What the floor does NOT cover — deliberately

Deterministic verification scales to crisp, checkable predicates (this path is a secret; this destination is off-allowlist; this amount exceeds a threshold; this write mutates the agent's own config). It does **not** scale to open semantic judgment — "is this email appropriately worded?", "is this a good refactor?" — because, unlike a closed syscall set, the agent action space is open-ended and semantic (§9). Verity claims provable guarantees **only for the floor** and explicitly cedes subjective/reversible judgment to model-based layers. Overclaiming deterministic coverage of semantic judgment would repeat SELinux's over-reach and invite the same disablement (§8).

### 7.2b Context-specific catastrophe (personalized — §8)

Beyond the floor, what is catastrophic depends on the person and use case. This is where verification becomes specific — and where the hard problem (§8) lives.

### 7.3 Database operations as a worked example

The author's domain background (database administration; agents that change parameters, kill queries, and reconfigure production systems) provides a concrete, credible policy domain — e.g. a destructive-operation floor and expert-authored resource envelopes evaluated against live state. Databases are **one illustrative domain**, not the product's center; the primary surface is the general action space of an open harness.

---

## 8. Personalization — the Differentiated Problem

"Specific to the person, domain, or use case" is really **three different authoring problems**, and they are not equally solved:

- **Domain** (e.g. enterprise database operations): an expert authors the policy. *Feasible.*
- **Use case** (e.g. "a coding assistant scoped to this repo"): a developer or a template authors it. *Feasible.*
- **Person** (a consumer running OpenClaw at home): there is no expert, and the user will never author a policy — the entire appeal of these harnesses is "no configuration required." *This is the hard one.*

The honest resolution for the consumer case is **two parts**, and it deliberately avoids the unreliable inference Verity refuses to do:

1. **A universal catastrophe floor** (§7.1), shipped **always-on and invisible, like seccomp** — no per-use authoring; the user never writes it.
2. **Personalization learned from behavior and corrections, not authored — like AppArmor's complain mode.** Run permissively, observe real behavior, propose rules, let the user confirm, then enforce; with an `audit2allow`-style "approve this and remember it" correction loop. This is ordinary preference-learning from feedback, not physics inference or consequence prediction.

**The decisive lesson from mandatory-access-control history — and it inverts the primary metric.** SELinux was disabled across the industry (`setenforce 0`) not because it failed to enforce, but because its policy was **unauthorable and its denials were noisy**: when a control produces frequent, hard-to-resolve denials, operators turn it off wholesale, and its security value drops to zero. Therefore **false-positive / noise budget is Verity's #1 product metric, above coverage.** A verifier that is strict but noisy gets ripped out and protects no one; a verifier that gates only the crisp floor and otherwise stays silent survives. This is why the floor-membership criterion is "a reasonable user would never want this done silently" — and why the `setenforce 0` moment (the user disabling Verity or routing around the harness) is the failure mode the whole design optimizes against.

> **What remains genuinely open** is the precise learned-personalization mechanism: cold-start behavior, how few corrections suffice, and how to keep learned boundaries deterministic and inspectable. The author has further thinking here; intentionally left open (§11).

---

## 9. Scope

### In scope

- A deterministic runtime verification primitive at a harness's tool-execution chokepoint.
- An encode-time compiler (LLM + solver) from intent/context to an evasion-aware verifier.
- A universal catastrophe floor and a learned per-user personalization loop.
- Verdict + circumvention-pathway output, feeding agent self-correction and after-the-fact review.
- A real integration into one open harness, built for production use, not as a proof of concept.

### Explicitly out of scope

- **Predicting second-order consequences** (e.g. "will this configuration change cascade into an outage"). This requires domain inference Verity cannot reliably do; a confidently wrong prediction is worse than none.
- **Enforcement.** Verity returns verdicts; the runtime acts.
- **Inferring a domain's physics or a person's full risk profile.** Knowledge comes from policy (authored or learned-from-corrections), not from speculative inference.
- **Being a standalone product or company** — no pricing, billing, multi-tenancy, managed control plane, or go-to-market. The value and the learning are in the verification capability and its integration, not in a business shell.

### The honest scope boundary

Verity is deterministic for the **catastrophe floor** — actions that resolve to crisp, checkable predicates — and only there. Unlike a syscall set (closed, finite, semantically stable), the agent action space is open-ended and semantic, so deterministic policy cannot cover it whole. Provable guarantees are claimed for the floor; open semantic judgment is explicitly ceded to model-based layers (§3, Layer 2). Claiming deterministic coverage of the whole action space would repeat SELinux's over-reach and invite the same disablement (§8). The credibility of the project is in the honesty of this line.

---

## 10. Build Plan

"Built for real" means a working, integrated verifier — not a demo. Deep systems knowledge comes from building, not from prototyping; the build is the point.

1. **Core verifier.** The `verify(action, context) → verdict` engine: policy representation, deterministic evaluation, the three-valued verdict (conform / violate / indeterminate), and the verdict trace. Tested against the catastrophe-floor cases.
2. **Encode-time compiler.** Intent/context → compiled policy, with solver-assisted circumvention enumeration; LLM-drafted, reviewed by consequence.
3. **Harness integration.** Insert `verify()` at the chosen harness's tool-execution step; wire the verdict into the runtime and the circumvention pathway into the agent's self-correction loop and the harness memory.
4. **Catastrophe floor.** A baseline policy pack covering §7.1, derived in part from the published harness-vulnerability work.
5. **Personalization loop.** Learn per-user boundaries from corrections, stored in harness memory.

**The demonstration:** an autonomous agent in the harness confidently proposes a catastrophic action (a prompt-injected or hallucinated destructive command), and Verity returns `Violate` with a human-readable reason and pathway, *before* execution — and the agent self-corrects from the explanation. It is visceral, true to the real failure mode, and impossible for a model-based guard to do reliably (because the same injection that fooled the agent fools the guard).

---

## 11. Open Questions

1. **Harness selection** — OpenClaw vs. Hermes, decided from whichever exposes the cleaner pre-execution tool-dispatch interception point (not from popularity).
2. **Implementation stack** — language of the runtime verifier (and whether bindings are needed for the harness's language), and the policy representation. StrataDB is Verity's own data layer (§6.4) for policies, simulation, inference, and relationships; the open question is the runtime-core language and verifier form, not whether a data layer is needed.
3. **Personalization design** — the consumer learn-from-corrections model: cold-start behavior, how few corrections suffice, how to keep learned boundaries deterministic and inspectable, and where the line sits between "learned preference" and "inference we refuse to do." *The author has further thinking to contribute here; deliberately left open.*
4. **Catastrophe-floor coverage** — how complete a universal floor can be, and how to surface what it does *not* cover (honest scope made visible to the user). Lead candidates are concrete (§7.1); the open work is validating the floor stays small, stable, and low-noise on real agent traffic — the false-positive budget (§8) is the gating metric.
5. **Self-correction dynamics** — what an agent actually does when handed a circumvention pathway, and how to prevent unproductive retry loops (the runtime's concern, but it shapes the verdict format).
6. **Semantic-resolution of the exec gate** — the floor's shell/command rule must resolve commands semantically (defeating lexical bypass: line continuation, busybox, option abbreviation), not by string match. How to do this reliably and deterministically is an open implementation problem.
7. **Provenance/taint plumbing** — the confused-deputy defense (§6.6) requires taint metadata from the input side; what the harness exposes, and what Verity must reconstruct, is open.

---

## 12. Naming

The product is named **Verity** — the deterministic source of truth about whether an agent action is safe. The name is not treated as a commercial/trademark concern: this is a build-and-learn project, not a company. The earlier Python rule engine in this repository retains the name "Symbolica"; it is a separate, earlier project for a different use case.
