# Product Requirements Document: Symbolica

## 1. Product Name

**Symbolica**

## 2. One-Line Description

Symbolica is an open-source neurosymbolic reasoning and verification layer that lets AI agents evaluate, simulate, and safely execute state-changing actions against explicit policies, business rules, and system invariants.

## 3. Product Thesis

As AI agents move from answering questions to taking actions, every serious agent stack will need a control layer that determines what agents are allowed to do, why they are allowed to do it, and whether their actions could lead to unsafe or non-compliant outcomes.

Today, most agent systems rely on ad hoc guardrails: API permissions, prompt instructions, hardcoded checks, approval workflows, or simple policy engines. These are useful but insufficient for agents that operate across multi-step workflows, mutable state, enterprise policies, and consequential business systems.

Symbolica provides the missing reasoning layer. It combines deterministic symbolic rules, structured world models, LLM-assisted policy authoring, execution traces, simulation, and solver-backed verification to help developers build agents that can act safely, explainably, and auditably.

The long-term vision is to become the default reasoning and verification layer for AI agents.

## 4. Problem Statement

AI agents are increasingly being connected to tools, APIs, databases, enterprise applications, and operational systems. Once agents can mutate state, the central question becomes:

**How do we know the agent did what it was supposed to do, without violating policy, skipping approval, creating risk, or reaching a forbidden state?**

Existing approaches are fragmented:

* LLM prompts are not enforceable.
* API permissions are too coarse.
* Human approval workflows are manual and brittle.
* Traditional policy engines usually check individual requests, not multi-step agent plans.
* Agent frameworks focus on orchestration, not verification.
* Logs explain what happened after the fact, but do not prevent unsafe action.
* Formal methods are powerful but too difficult for most developers to use directly.

Teams need a practical middle layer between unconstrained agents and fully formal theorem proving.

Symbolica addresses this gap by giving developers a way to define entities, actions, policies, and invariants, then evaluate agent plans against those constraints before execution.

## 5. Target Users

### 5.1 Primary User: AI Application Developer

A developer building AI agents that can read and write application state, call APIs, execute workflows, or interact with enterprise systems.

Needs:

* Easy way to define what agents can and cannot do
* Runtime enforcement for tool calls and plans
* Clear explanations when actions are blocked
* Minimal formal methods expertise required
* SDKs that plug into existing agent frameworks

### 5.2 Secondary User: Platform Engineer

A platform engineer responsible for providing safe agent infrastructure to multiple internal teams.

Needs:

* Central policy registry
* Reusable action schemas
* Audit logs
* Enforcement hooks
* Integration with identity, approval, and observability systems
* Confidence that agents cannot bypass policy

### 5.3 Secondary User: Security, Risk, or Compliance Team

A security or governance stakeholder responsible for ensuring AI systems comply with internal rules and external regulations.

Needs:

* Auditability
* Explainable decisions
* Policy versioning
* Evidence of enforcement
* Ability to review counterexamples and unsafe pathways
* Reporting across agents and applications

### 5.4 Tertiary User: Enterprise Product Team

A product team embedding agents into customer-facing or internal workflows.

Needs:

* Faster path to shipping state-changing agents
* Guardrails that are stronger than prompt instructions
* Clear product UX for approvals, blocks, and explanations
* Ability to give customers confidence in agent safety

## 6. Core Use Cases

### 6.0 Beachhead: Database Operations

The launch wedge is agents acting on production databases — changing parameters, configurations, killing queries, applying fixes. This is felt, consequential pain (validated firsthand: the founder was Principal PM for IBM Db2 Genius Hub, which made exactly the advisory→acting transition Symbolica governs), and it carries founder-market fit: credibility with DBAs, a warm network, and lived knowledge of the failure modes. Refunds and PII (below) are illustrative and the expansion story; databases are where Symbolica lands.

Three failure classes structure the work (a progressive ladder; the ontology is the spine):

* **Obviously-wrong destructive/disruptive actions** — drop a schema, stop the primary, delete data. LLM agents propose these with full confidence. Caught by effect-category policy (`destructive`, `irreversible`, `availability_impacting`). The floor under a confidently-wrong agent. Ships first.
* **Nonlinear-consequence actions** — e.g. raising sort memory to fix queuing, cascading to host OOM. Symbolica does *not* predict the cascade (§9.13); the DBA encodes an envelope from their own knowledge (`sortheap × max_concurrency < host_mem × safety`), and Symbolica evaluates it against live state.
* **Compositional / cumulative** (the refund-splitting flavor) — a side tool here, not the spine.

### 6.1 Agent Tool-Call Authorization

An agent proposes a tool call. Symbolica **verifies** the action against state, policy, permissions, and declared side effects, and returns a verdict (§9.12) — the caller decides what to do with it.

Example:

* Agent proposes `issue_refund(customer_id, amount=15000)`
* Policy says refunds above $10,000 require finance approval
* Symbolica returns `requires_approval` with reasoning; the caller blocks, routes, or lets the agent self-correct

### 6.2 Multi-Step Agent Plan Validation

An agent proposes a sequence of actions. Symbolica evaluates the plan as a whole, not just individual tool calls.

Example:

* Step 1: apply discount
* Step 2: update contract
* Step 3: generate invoice
* Step 4: notify customer

Symbolica identifies that contract updates require legal approval before invoice generation.

### 6.3 Branch-Based Simulation

Symbolica runs proposed agent actions against a simulated or branched state before production execution.

Example:

* Fork current state
* Apply proposed plan
* Evaluate policy violations
* Generate state diff
* Approve, block, or escalate
* Commit only if safe

This use case becomes especially powerful when paired with Strata.

### 6.4 Invariant Checking

Developers define invariants that must never be violated.

Examples:

* Agents cannot approve their own actions.
* Production data cannot be deleted without approval.
* Customer PII cannot be sent to unapproved tools.
* Critical database workload changes require impact analysis.
* Payments cannot be released without a matching invoice.

Symbolica checks whether proposed actions or plans violate these invariants.

### 6.5 Counterexample Generation

When a policy is unsafe or incomplete, Symbolica provides a concrete failure path.

Example:

> This policy allows a support agent to split a $15,000 refund into two $7,500 refunds and bypass finance approval.

Counterexamples help developers fix policies faster than generic pass/fail results.

### 6.6 LLM-Assisted Policy Authoring

Users describe policies in natural language. Symbolica drafts structured rules, action schemas, invariants, and test cases.

Example:

User says:

> “Any production database change that affects query plans should require impact analysis and DBA approval.”

Symbolica proposes:

* Entities
* Relevant state fields
* Action categories
* Approval requirements
* Invariant
* Test cases

The user reviews and accepts the generated policy.

### 6.7 Audit and Explanation

Symbolica provides a trace for every decision.

Example output:

* Action requested
* State considered
* Rules evaluated
* Solver checks performed
* Decision made
* Missing approvals
* Counterexample if blocked
* Policy version used

This helps developers, auditors, and product teams understand why an action was allowed, blocked, or escalated.

## 7. Product Goals

### 7.1 Near-Term Goals

* Make agent tool calls safer and more explainable.
* Provide a simple rule and policy layer for state-changing agent workflows.
* Generate structured traces for allow, deny, and approval decisions.
* Support plan-level validation for multi-step agent workflows.
* Provide open-source SDKs that can plug into common agent frameworks.

### 7.2 Medium-Term Goals

* Add solver-backed verification for bounded action sequences.
* Generate counterexamples for unsafe policies or plans.
* Support branch-based simulation, especially with Strata.
* Provide policy authoring assistance using LLMs.
* Build a managed service for teams, audit logs, policy registry, and enterprise controls.

### 7.3 Long-Term Goals

* Become the default reasoning and verification layer for AI agents.
* Provide reusable domain models for enterprise workflows, infrastructure, databases, finance, and compliance.
* Support deeper formal methods integrations, including SMT solvers and Lean-backed proof checking for high-assurance use cases.
* Enable agent platforms to offer scoped mathematical guarantees about action safety.

## 8. Non-Goals

Symbolica will not initially attempt to:

* Verify arbitrary LLM reasoning.
* Prove universal AI safety.
* Replace all access control systems.
* Replace all human approval workflows.
* Model every possible real-world state.
* Require developers to learn theorem proving.
* Compete directly as a full agent orchestration framework.
* Compete directly as a general-purpose database.

Symbolica’s focus is narrower:

**Verify and govern state-changing agent actions using explicit policies, structured state, symbolic rules, and solver-backed checks where appropriate.**

## 9. Key Product Principles

### 9.1 Structured Freedom

Agents should be allowed to act, but only through typed tools, declared side effects, explicit policies, and observable state transitions.

### 9.2 Prove What Matters

Do not model everything. Formalize only the high-risk invariants that matter.

### 9.3 Explain Every Decision

Every allow, deny, and escalation decision should produce a human-readable trace.

### 9.4 Counterexamples Over Abstract Failures

When something is unsafe, show the pathway that makes it unsafe.

### 9.5 Progressive Assurance

Not every workflow needs theorem proving. Symbolica should support multiple levels of assurance:

* Basic rules
* Runtime policy checks
* Plan validation
* Simulation
* Adversarial simulation (millions of fuzzed pathways checked against invariants)
* SMT-backed verification
* Machine-checkable proofs for high-assurance use cases

### 9.6 Open Core Trust

The core reasoning engine should be open source. Trust-sensitive infrastructure benefits from transparency, inspectability, and community validation.

### 9.7 Human Review Where the Model Is Incomplete

If Symbolica cannot verify safety due to missing context, incomplete state, or ambiguous policy, it should escalate rather than guess.

### 9.8 Author by Intent, Review by Consequence

Users are never asked to hand-write policy JSON — that authoring burden is what sank prior rule engines. The policy DSL is an intermediate representation: machine-written, human-readable, version-controlled. Every authoring path is generative (starter packs, learn mode from traces, natural-language intent translation, red-team repairs), and users review by consequence — plain-English restatements, generated test cases, and backtests against their own history — not by reading syntax. Experts retain a direct-edit escape hatch; auditors and git keep the JSON artifact.

### 9.9 LLMs Suggest, the Core Decides

LLMs operate at authoring time only — drafting, formalizing, red-teaming, explaining — never in the execution path. Execution-path decisions come exclusively from the deterministic core; LLM findings never contribute to a "verified" claim until confirmed by solver or human.

### 9.10 Aggregate Only Over Verified Keys

Cumulative policy is only as trustworthy as the keys it aggregates over. Grouping keys supplied in the action payload (`customer_id`, `incident_id`) are *claimed by the governed agent* — an agent that can vary or mint a key can move a cumulative loophole one call upstream (split refunds across fresh incident IDs). Keys therefore carry provenance, exactly as predicate bindings do (§9.9):

* **verified** — bound to an entity in a system of record (connection-authenticated actor, gateway-observed session, or a key validated against external state)
* **claimed** — taken from the action payload, unverified

Aggregation over claimed keys yields at best a weak, advisory guarantee; high-risk cumulative invariants must aggregate over verified keys, and key-minting actions (e.g. "open incident") are themselves governed so the upstream move is in the policed action stream. The enforced property is always scoped to what the system can verify and observe (see §21.7); claims to the user must not exceed that scope.

### 9.11 Enforced Property ≠ Business Invariant

The runtime sees only the actions that flow through it. "No customer receives more than $10k per incident" is an invariant over the *business*; what a single gateway actually enforces is "≤$10k *via this chokepoint*." Refunds issued by humans, other agents, a second gateway, or direct API calls are invisible until a state adapter feeds them in. This gap is closed only by integration with systems of record — the per-application cost that limited OPA's reach (§16.1). The product must state this scope honestly wherever it claims enforcement; an auditor finds the gap in one question.

### 9.12 Verify, Don't Enforce

Symbolica is a **verification layer**, not a blocking layer. It answers a question — *does this action satisfy the policy, given current state?* — and returns a verdict with reasoning. It does not decide what happens next. In the developer's terms, Symbolica is the `if`-condition in the agent's execution path; the developer writes the body:

```
if (symbolica.verify(tool_call(params)).conforms) { ...your choice... }
else { ...block, escalate, ask a human, let the agent self-correct, log — your choice... }
```

Consequences of this framing: the allow/deny/escalate dispositions (§21) are a verdict *vocabulary*, not enforcement actions; shadow mode is not a mode but a body that logs instead of blocks; the gateway is an *opinionated deployment* that pre-wires the body to block-on-violate (giving the un-bypassable chokepoint), not a property of the engine. The hard, valuable, defensible work is the verification; the enforcement is trivial and situational, and it belongs to the caller.

### 9.13 Domain Knowledge Lives in the Policy

Symbolica never infers a domain's physics. It does not learn that raising sort memory cascades to host OOM, and it must not claim to predict second-order consequences — that is a research problem requiring domain inference Symbolica cannot reliably do, and a confidently-wrong prediction is worse than none. Instead, the domain expert encodes their knowledge once as policy (a limit, an envelope, a forbidden category), and Symbolica verifies against it deterministically using live state, tirelessly (the caller acts on the verdict — §9.12). Symbolica's own reasoning (Z3 + LLM, at encode time — §10.3) is about the *policy's logic* — its cases, gaps, and circumvention pathways — never about domain mechanics. The honest scope follows: Symbolica catches what experts can articulate as rules; genuinely novel, unforeseeable consequences nobody wrote a rule for are out of scope, and the product never claims to prevent all outages.

## 10. Conceptual Architecture

### 10.3 Encode Time vs Runtime

The product runs in two phases, and confusing them is the source of most design error:

- **Encode time** (when a policy is defined): the user states intent; a compiler uses Z3 + LLMs to enumerate the cases that need handling and the **circumvention pathways** of the policy, and emits a compiled policy plus an evasion catalog. Expensive, thorough, one-time per policy version. This is the only place the solver and LLM run.
- **Runtime** (every tool call): `verify(action, state, policy)` evaluates the action against the compiled policy and live state. Fast, deterministic, **no solver or LLM in the hot path.** Returns conform / violate / can't-determine, and on violate, the circumvention pathway.

Because the encode-time enumeration already closed the evasion space, the runtime explanation is *safe to expose* — it can tell the agent exactly why its action was rejected without teaching it a new way to cheat, since every alternative evasion is already caught (scoped to the encoded model). Two consumers use the explanation: the **agent**, which self-corrects its tool call in real time and re-verifies, and the **engineer**, who reviews the failure pathway later in a Langfuse trace.

### 10.1 High-Level Flow

1. Agent proposes an action or plan.
2. Symbolica receives the proposed action, relevant state, actor context, and policy set.
3. Symbolica evaluates deterministic rules.
4. Symbolica optionally simulates the plan against a branch or sandbox.
5. Symbolica optionally invokes a solver for invariant checking or counterexample search.
6. Symbolica returns a **verdict** with reasoning (the verdict vocabulary, §21):

   * Conform
   * Violate (with the circumvention pathway / reasoning)
   * Require approval (recommended disposition)
   * Require more context (state incomplete — can't verify)
   * Unsafe policy (with counterexample)
   * Unknown (incomplete model)
7. **The caller acts on the verdict** — block, escalate, let the agent self-correct, or log. Symbolica does not enforce (§9.12); the gateway deployment is what pre-wires "block on violate," and shadow mode is simply a caller that logs instead of acts.
8. Symbolica records a verdict trace for audit and replay, optionally emitted as OpenTelemetry spans into the team's existing observability tools — and, on violate, the circumvention pathway feeds both the agent's real-time self-correction and the engineer's later Langfuse review (§10.3).

### 10.2 Core Components

#### 10.2.1 World Model (Learned Domain Ontology)

Defines the entities, relationships, state fields, quantity flows, and permissions relevant to a domain. The world model is not just declared — it is **learned and maintained**: a living ontology of the deployment's actual domain, with provenance on every element.

Example entities:

* User
* Agent
* Tool
* Customer
* Contract
* Invoice
* Database
* Workload
* Approval
* Environment
* Policy

Beyond entities, the ontology captures what generic LLM world knowledge cannot: deployment-specific semantics — e.g., that `apply_discount`, `price_override`, `bundle_pricing`, and `goodwill_adjustment` all affect the same economic quantity (effective price paid). These equivalences are the difference between checking one action's argument and checking the invariant that was actually meant.

How it is built (conjecture–verify, same as policies):

* Seeded from action schemas, domain starter templates, and imported API/DB specs
* Grown from observed traces — shared identifiers link entities; two actions writing the same field is data evidence of equivalence
* Enriched by LLM-proposed edges (hypotheses, never facts), confirmed by data evidence or human review
* Every edge carries provenance (declared / observed / inferred / confirmed) and confidence
* Ontology changes follow the same shadow → enforce lifecycle as policies: new edges first report what they *would have* flagged
* Stored in Strata's graph/ontology primitive, which **already exists today** — Symbolica constructs no graph infrastructure of its own. Strata's next-gen architecture additionally overlays relationships across the other primitives (e.g. a KV key related to a JSON document through a relationship tag), enriching the model but not gating the basic ontology. Vector similarity (clustering), event-log provenance, versioning, and branch-testing ontology updates against the regression corpus all come from the substrate. Symbolica contributes only the policy-domain schema (entities, quantity flows, action-effect equivalences), the provenance/confidence semantics, the learning loop, and the consumers (gap search, directed fuzzing, drift detection)

What the learned ontology powers:

* **Gap search over the real model**: invariants quantify over quantities ("effective_price / list_price"), and the solver searches all pathways that touch them — questions that cannot even be phrased without the ontology
* **Semantically directed adversarial simulation**: the fuzzer composes cross-action attacks (discount + override + credit) that are combinatorially invisible to random search and unknown to generic LLM knowledge
* **Drift detection with a reference model**: unplaceable new tools and effect-divergence get flagged (§15.3)
* **Better invariant formalization**: intent like "no big discounts" binds to the quantity, not to a single action

Scope discipline: the ontology exists to serve gap search, simulation, and drift detection — entities, relationships, quantity flows, action-effect mappings. It is not a general knowledge graph or semantic-layer product. Verified claims remain scoped to the model version ("no loophole within model M v12"), with inferred edges enumerated.

#### 10.2.2 Action Model

Defines what agents can do and how each action affects state.

Each action includes:

* Name
* Input schema
* Actor requirements
* Preconditions
* Declared side effects
* Risk category
* State changes
* Required approvals
* Rollback metadata
* Auditing requirements

#### 10.2.3 Policy Model

Defines rules governing actions and state transitions.

Policy examples:

* If refund amount > $10,000, finance approval is required.
* If environment = production and action affects optimizer state, impact analysis is required.
* If action sends PII externally, destination must be approved.
* If action is destructive, backup validation is required.

#### 10.2.4 Invariant Model

Defines properties that must always hold.

Invariant examples:

* Agent cannot approve its own action.
* Production database cannot become internet reachable.
* Critical workload changes cannot execute without impact analysis.
* Payment cannot be released without matching invoice.
* Customer PII cannot be sent to unapproved tools.

#### 10.2.5 Rule Engine

Evaluates deterministic symbolic rules over the world model, action model, and runtime state.

Responsibilities:

* Match rules
* Evaluate conditions
* Produce decisions
* Produce traces
* Identify missing data
* Support backward chaining where useful

#### 10.2.6 Solver Layer

Integrates with SMT/SAT solvers and, later, theorem provers.

Responsibilities:

* Check whether constraints are satisfiable
* Identify policy contradictions
* Search for counterexamples
* Check bounded action sequences
* Verify whether certain forbidden states are reachable

Initial solver target:

* Z3 or cvc5

Future solver/prover targets:

* Lean 4
* Alloy-style modeling
* TLA+-style workflow modeling
* Domain-specific solvers

#### 10.2.7 Simulation / Branch Runtime

Runs proposed actions against a simulated state or branch.

Responsibilities:

* Create branch
* Apply action effects
* Track state diffs
* Evaluate policies at each step
* Block or escalate unsafe plans
* Commit safe changes
* Preserve full audit trail

Implementation: this component is built on StrataDB's branch primitive, embedded as a Rust library dependency (not external infrastructure). Fork-in-microseconds branching, state diffs, and merge/discard semantics come from Strata directly; in-memory simulation uses Strata's cache mode. Users do not need to deploy or adopt Strata separately.

#### 10.2.8 Trace Engine

Generates human-readable and machine-readable explanations.

Trace includes:

* Input action or plan
* Actor
* State fields evaluated
* Rules triggered
* Rules skipped
* Missing inputs
* Solver checks
* Decision
* Required approvals
* Counterexamples
* Policy version
* Timestamp

#### 10.2.9 LLM Policy Assistant

Helps users author and maintain policies.

The assistant is not a convenience layer — per §9.8 it is the only intended authoring path. Users state intent, import history, or accept packs; the assistant generates the DSL; users review consequences.

Capabilities:

* Learn mode: draft baseline policies from observed traffic or imported trace history (priority over freeform authoring in the MVP)
* Translate natural language intent into invariants and policies
* Check invariant faithfulness: does the formal invariant capture what the human actually meant?
* Adversarial red-teaming (conjecture–verify loop): propose loophole hypotheses against invariants — in-model hypotheses compile to solver queries and are mechanically confirmed or refuted; out-of-model hypotheses ("store credit also moves money to the customer") become model-extension proposals for human review
* Suggest action side effects
* Generate test cases (the review medium for generated policies)
* Identify missing assumptions
* Explain counterexamples
* Draft documentation
* Compare policy versions as behavioral diffs

The LLM assistant cannot be the final authority. It proposes; the solver or a human confirms. Confirmed loopholes become permanent regression test cases. Inference runs through Strata's inference layer (local llama.cpp models and Anthropic/OpenAI/Google cloud providers, exposed via the executor crate) — authoring-time work wants frontier reasoning models; cost and latency are acceptable there because nothing in the execution path waits on an LLM.

#### 10.2.10 Observability Connectors

Connects Symbolica to the observability stack teams already run. Built on OpenTelemetry GenAI semantic conventions; Langfuse is the first concrete connector, with LangSmith, Phoenix/Arize, and others reachable through the same OTel seam.

Responsibilities:

* Emit Symbolica decision traces as OTel spans linked to the existing execution trace (decision span as child of the tool-call span)
* Import historical execution traces to bootstrap draft policies (learn mode)
* Replay historical traces against proposed policies (backtesting / false-positive preview before enforcement)
* Keep the two trace types linked but distinct: the execution trace (what happened, owned by the observability tool) and the decision trace (why it was allowed or blocked, owned by Symbolica — the audit and compliance artifact)

Observability connectors are a data path, not an enforcement path. Enforcement always happens at the insertion surface (SDK wrapper or MCP gateway); by the time a span reaches an observability tool, the action has already executed.

#### 10.2.11 Adversarial Simulator (Policy Fuzzer)

Tests policies the way serious databases are tested: deterministic simulation over millions of adversarial pathways, in the tradition of FoundationDB/TigerBeetle-style testing. The invariants are the oracle — a pathway is a finding when every step was individually allowed but the resulting state violates an invariant. This is only possible because of the invariant/policy separation; engines without an independent intent layer have nothing to fuzz against.

Responsibilities:

* Schema-aware adversarial generation: typed args, boundary values clustered at policy thresholds, repeated actions, multi-actor interleavings, approval/execution reorderings
* Coverage-guided mutation (track which policies/predicates fired; steer toward unexplored territory)
* Execution over Strata branches in cache mode — fork state per pathway, run through the same kernel evaluator as production, discard
* Epistemic fault injection: missing context fields, stale state, concurrent in-flight actions, time-window boundary straddles — verifying that decision semantics fail safe (unknown must escalate, never default to allow)
* Counterexample shrinking: minimize violating sequences to the shortest reproduction before a human sees them
* Regression corpus: every confirmed loophole (fuzzer-, solver-, red-team-, or incident-sourced) becomes a permanent seed replayed on every policy change
* Behavioral diffing: replaying the corpus under two policy versions and diffing decisions powers the version-comparison UX (§25.2)
* Determinism guarantees: seeded runs over virtual (injected) time — every finding reproduces from a seed

The simulator, solver, and LLM red-team form one search portfolio: solver = exhaustive but shallow and fragment-limited; fuzzer = randomized but deep, any computable policy semantics; LLM = low-volume, out-of-model, semantic. LLM hypotheses seed directed fuzzing; fuzzer findings get LLM explanations; everything confirmed lands in the shared corpus. The simulator is dual-use: it tests user policy packs and Symbolica's own kernel semantics.

Kernel prerequisites (day-one constraints): pure transition function `(state, action) → (decision, state')`, virtual time injected with each action (the kernel never reads the wall clock), seeded determinism end-to-end.

## 11. Product Surface

### 11.1 Open-Source Core

The open-source core should include:

* Policy DSL
* Rule engine
* Action schema format
* Invariant schema format
* Local evaluation runtime
* SDK tool wrappers (one-line insertion into existing agents)
* MCP gateway mode (config-change insertion; the enforcement chokepoint)
* Shadow (log-only) mode
* Starter policy packs
* Trace output
* OpenTelemetry decision-span emitter (Langfuse as first connector)
* Learn mode (draft policies from observed or imported traces)
* Basic plan validation
* CLI
* SDKs
* Example integrations
* Local solver integration

### 11.2 Managed Service

The managed service should include:

* Hosted policy registry
* Versioned policies
* Team management
* RBAC
* SSO
* Audit log storage
* Approval workflows
* Dashboards
* Compliance exports
* Managed solver execution
* Continuous large-scale adversarial simulation (billions of pathways, certified results for policy packs)
* Managed LLM policy assistant
* Enterprise connectors
* Agent fleet governance
* Multi-environment policy rollout

### 11.3 Insertion and Adoption Model

Distribution is treated as a first-class product decision. The full strategy lives in `Symbolica-distribution.md`; the summary:

* Two primary insertion artifacts share one policy format:
  * **SDK tool wrapper** — `guard.wrap(tools)`, one line of code, framework-agnostic at the tool-callable layer. Wins the trial.
  * **MCP gateway** — point the agent's MCP config at Symbolica, which proxies tool servers behind policy. A config change, not a code change, and the only insertion that is a true enforcement chokepoint. Wins production.
* Framework-specific adapters (LangGraph middleware, OpenAI Agents SDK guardrails, Claude Code hooks) are thin veneers over the SDK wrapper, not separate engines.
* Shadow mode is the default: install, wrap, nothing breaks, and the team sees an action ledger plus what would have been blocked. Enforcement is a flag flipped after confidence builds.
* Value before authoring: the action ledger is useful with zero policies; starter packs cover the initial domains; learn mode drafts a policy baseline from observed or imported traffic.
* Graduation between surfaces is a config migration, never a rewrite.

## 12. Example Developer Experience

Note: the JSON in this section is what Symbolica **generates** — the reviewable, version-controlled output of intent translation, learn mode, or a starter pack (§9.8). Users review these artifacts and their consequences; they are not expected to write them by hand. The `rationale` field carries the plain-English intent inside the artifact: comments as structured data, rendered in review UIs and quoted in decision traces.

### 12.1 Define an Action

```json
{
  "actions": {
    "issue_refund": {
      "inputs": {
        "customer_id": "string",
        "amount": "number",
        "reason": "string"
      },
      "effects": [
        "mutates_financial_state",
        "sends_customer_notification"
      ],
      "requires_actor_role": ["support_agent", "finance_agent"]
    }
  }
}
```

### 12.2 Define a Policy

```json
{
  "policies": {
    "refunds_over_10000_need_approval": {
      "rationale": "Refunds above 10000 require finance approval",
      "when": {
        "action": "issue_refund",
        "amount_gt": 10000
      },
      "require": {
        "approval_from": "finance_manager"
      }
    }
  }
}
```

### 12.3 Define an Invariant

```json
{
  "invariants": {
    "agent_cannot_approve_own_action": {
      "rationale": "No agent may approve its own action",
      "always": {
        "not": {
          "approval.approver_id": "action.actor_id"
        }
      }
    }
  }
}
```

### 12.4 Evaluate an Agent Plan

```json
{
  "actor": "agent-support-17",
  "plan": [
    {
      "action": "issue_refund",
      "customer_id": "C123",
      "amount": 15000,
      "reason": "service outage"
    }
  ]
}
```

### 12.5 Symbolica Response

```json
{
  "decision": "requires_approval",
  "required_approval": "finance_manager",
  "reason": "Refund amount exceeds 10000",
  "policy": "refunds_over_10000_need_approval",
  "trace_id": "trace_abc123"
}
```

### 12.6 Counterexample Response

```json
{
  "decision": "unsafe_policy",
  "counterexample": [
    "Agent issues refund of 7500",
    "Agent issues second refund of 7500",
    "Total refund reaches 15000 without finance approval"
  ],
  "violated_intent": "Refunds above 10000 require finance approval",
  "suggested_fix": "Track cumulative refund amount per customer per incident"
}
```

## 13. MVP Scope

### 13.1 MVP Objective

Build a local open-source Symbolica runtime that can validate state-changing agent actions and simple multi-step plans against explicit rules and invariants, producing clear traces and approval/block decisions.

### 13.2 MVP Must-Haves

#### Insertion Surfaces

* SDK tool wrapper: `guard.wrap(tools)` one-line insertion into existing agents
* MCP gateway: proxy mode inserted via MCP client config, no code change
* Shadow (log-only) mode as the default for both surfaces; enforcement is opt-in per policy
* One policy format shared across both surfaces; switching surfaces requires no policy rework
* Action ledger: even with zero policies, wrapped agents produce a structured record of every action

#### Starter Policy Packs

* `symbolica init --pack <domain>` ships working, editable policies for the MVP example domains
* Templates convert "learn a DSL" into "edit a threshold"

#### Policy DSL

* JSON-based policy definitions (YAML rejected: humans never hand-write policies per §9.8, so authoring ergonomics are moot; JSON wins on parsing, LLM structured-output generation with schema-guaranteed validity, and canonicalization)
* Canonical form: sorted keys, stable formatting — policy versions are content hashes
* JSON Schema validation for every artifact (actions, policies, invariants)
* `rationale` fields carry plain-English intent inside the artifact (comments as structured data)
* Supports conditions, requirements, and decisions
* Supports allow, deny, require approval, require context

#### Action Schema

* Define action inputs
* Define action categories
* Define side effects
* Define actor requirements
* Define required state fields

#### Rule Engine

* Evaluate rules deterministically
* Support basic boolean logic
* Support numeric comparisons
* Support entity lookups
* Support missing-context detection

#### Plan Evaluator

* Accept a sequence of proposed actions
* Evaluate each action
* Track simulated state changes in memory
* Stop execution when policy is violated
* Return trace

#### Trace Output

* Explain decision
* Show triggered rules
* Show required approvals
* Show missing context
* Show policy version

#### CLI

Commands:

* `symbolica init`
* `symbolica gateway`
* `symbolica validate-policy`
* `symbolica eval-action`
* `symbolica eval-plan`
* `symbolica explain-trace`
* `symbolica test-policy`
* `symbolica suggest-policies` (learn mode, if trace data is available)
* `symbolica red-team` (LLM loophole hypotheses, solver-confirmed — authoring/CI time)
* `symbolica simulate --paths N --seed S` (adversarial fuzzing against invariants — authoring/CI time)

#### SDK

Initial SDK in TypeScript or Python.

Core functions:

* `guard.wrap(tools, actor=...)` — one-line tool wrapping with actor/session context
* `evaluateAction`
* `evaluatePlan`
* `validatePolicy`
* `explainDecision`

#### Examples

MVP examples should include:

* Refund approval workflow
* Database operations workflow
* Infrastructure change workflow
* PII/tool-use workflow

### 13.3 MVP Should-Haves

* Z3 or cvc5 integration for simple invariant checks
* Counterexample generation for bounded workflows
* Adversarial simulator, basic tier: random + boundary-value generation, invariants-as-oracle, shrinking, regression corpus (coverage-guided mutation and fault injection can follow)
* OpenTelemetry decision-span emitter, with Langfuse as the first connector
* Learn mode: draft baseline policies from observed traffic or imported Langfuse/OTel trace history
* Policy backtesting: replay historical traces against proposed policies to preview false positives before enforcement
* LangGraph integration (thin adapter over the SDK wrapper)
* OpenAI tool-call middleware (thin adapter over the SDK wrapper)
* Basic UI for traces (deferred wherever decision spans can render in existing observability tools)

Note: MCP integration moved from should-have to must-have — the gateway is a primary insertion artifact. Freeform natural-language policy authoring is post-MVP; learn mode is the MVP's LLM-assisted authoring.

### 13.4 MVP Non-Goals

* Full Lean 4 integration
* Full theorem proving
* General-purpose workflow engine
* Full hosted SaaS
* Enterprise RBAC
* SOC 2 controls
* Production-grade policy registry
* Arbitrary code verification

## 14. V1 Scope

### 14.1 V1 Objective

Launch Symbolica as a serious open-source project and early managed product for teams building agents that take consequential actions.

### 14.2 V1 Capabilities

#### Open-Source Runtime

* Stable policy DSL
* Action schema registry
* Plan evaluation
* Trace engine
* Local solver integration
* Counterexample generation
* SDKs
* Framework integrations

#### Managed Control Plane

* Hosted policy registry
* Policy versioning
* Audit logs
* Team access
* Environment separation
* Approval workflows
* Trace dashboard
* Policy test suite
* Drift detection

#### Integrations

* LangGraph
* OpenAI function/tool calling
* Anthropic tool use
* MCP
* Strata
* GitHub Actions
* CI/CD systems
* Webhook-based tool execution
* OPA import/export where feasible

#### Domains

Initial domain templates:

* Financial approvals
* Database operations
* Infrastructure changes
* Enterprise SaaS workflows
* Customer support actions
* PII handling

## 15. Future Scope

### 15.1 Lean 4 Integration

Potential uses:

* Prove properties about Symbolica’s policy language
* Prove runtime enforcement semantics
* Verify that certain classes of policies preserve invariants
* Generate machine-checkable policy proofs for high-assurance customers
* Support advanced users who want formal proofs

Lean should not be required for normal users.

### 15.2 Advanced Autoformalization

* Natural language to policy
* Policy docs to structured rules
* Compliance docs to invariants
* API specs to action models
* Agent traces to policy suggestions

### 15.3 Policy Drift Detection

Detect when:

* APIs change
* Tool side effects change
* Business policies change
* Agent permissions change
* Runtime behavior diverges from declared model

### 15.4 Agent Certification

Symbolica could certify that an agent satisfies a set of policies under a defined model.

Example:

> This support refund agent is verified against policy pack v3.2 for refund limits, approval routing, and customer notification constraints.

### 15.5 Marketplace

Policy packs and domain models:

* HIPAA workflows
* SOC 2 controls
* PCI handling
* Database operations
* Cloud infrastructure
* Support workflows
* Finance workflows

## 16. Competitive Landscape

### 16.1 Open Policy Agent

OPA is a general-purpose policy engine.

Symbolica differentiates by focusing on:

* AI agents
* Multi-step plans
* State transitions
* Branch simulation
* Counterexamples
* LLM-assisted policy authoring
* Agent framework integrations
* Solver-backed verification

### 16.2 Agent Frameworks

LangGraph, CrewAI, AutoGen, and similar tools orchestrate agents.

Symbolica differentiates by governing actions rather than orchestrating reasoning.

It should integrate with agent frameworks, not replace them.

### 16.3 Guardrail Products

Guardrail products often focus on content moderation, prompt injection, PII detection, and output filtering.

Symbolica focuses on:

* State-changing actions
* Tool-call safety
* Business invariants
* Plan validation
* Formalized policy enforcement

### 16.4 Formal Verification Tools

Lean, Coq, Isabelle, TLA+, Alloy, Z3, and cvc5 are powerful but too low-level for most AI developers.

Symbolica differentiates by providing:

* Practical developer workflow
* Agent-specific abstractions
* Policy DSL
* Trace UX
* LLM-assisted authoring
* Managed service
* Integrations

### 16.5 AWS Neurosymbolic AI (Bedrock Guardrails / AgentCore / Kiro)

The most significant named competitor (identified June 2026). AWS has a dedicated neurosymbolic team built on its Automated Reasoning heritage (Zelkova IAM analysis, network reachability, verified crypto) and the Lean talent pool, shipping Automated Reasoning Checks in Bedrock Guardrails, policy verification in Bedrock AgentCore — directly Symbolica's category — and correctness workflows in Kiro.

What this validates: the category is real and existential; AWS's market education benefits every vendor in it.

Where Symbolica differentiates:

* **Neutrality**: the layer attesting agent behavior should not be owned by the vendor whose runtime/models are attested (the Datadog-vs-CloudWatch / Okta-vs-IAM dynamic). Compliance buyers understand auditor independence.
* **Runs everywhere**: cross-cloud, framework-neutral, local-first, open-source — the product shape AWS rarely wins outside its platform (see Cedar's limited gravity beyond Verified Permissions). AgentCore governs agents in AWS's runtime; most agents live elsewhere.
* **Bottom-up adoption**: shadow mode, action ledger, one-line wrapper, learn mode — developer-first in five minutes, vs. AWS productizing formal methods top-down.
* **Domain depth where it's owned**: the database-operations beachhead (§6.0) is governed by expert-authored envelopes over live system state and an effect-category floor — verification AWS's per-request guardrails don't perform, in a domain the founder helped define.
* **Author-by-intent + circumvention pathways**: Symbolica compiles intent into an evasion-proof verifier and explains *how* an action circumvents policy (for real-time agent self-correction), not just pass/fail.

Posture: do not race AWS on theorem-proving depth (their Lean bench wins that game; progressive assurance means Symbolica doesn't need it for years). Position as the open, vendor-neutral verification layer that works everywhere — including on AWS. Track AgentCore policy verification as the feature-by-feature benchmark.

### 16.6 Internal Enterprise Platforms

Many enterprises will build custom policy layers for agents.

Symbolica differentiates by providing an open, reusable, inspectable standard that avoids every company reinventing this layer.

### 16.7 Adjacent Incumbents Moving In (GTM research, June 2026)

Two distribution-rich incumbents are edging into the conceptual space — validation that the category is real, and a reminder that neutrality + open-source + database-domain depth are the defenses, not the kernel tech:

* **LaunchDarkly** now markets feature flags as "runtime control for AI-era software… keep agents on track, mitigating bad behavior… in real time." It owns the developer relationship and the "control you own" framing Symbolica wants — but it is config-flag-shaped, not policy-verification-shaped, and not database-domain-aware.
* **AWS Bedrock Automated Reasoning Checks** (GA Aug 2025) brings invisible formal methods to *content* validation ("does this answer comply?"), Bedrock-locked. Symbolica's lane is *action* verification ("does this tool call satisfy policy given system state?"), cross-model/cross-cloud, open-source — none of which AWS will offer (see §16.5).

## 17. Key Differentiators

1. Agent-native **verification** layer — the `if`-condition in the agent's path; verdict + reasoning, caller enforces (§9.12)
2. Author-by-intent: the expert states intent, Z3 + LLM compile it into an evasion-proof verifier; users never hand-write policy
3. Circumvention-pathway explanation that drives real-time agent self-correction and engineer debugging — safe to expose because the evasion space is pre-closed
4. Deterministic, fast runtime verification with full traceability; solver and LLM at encode time only, never the hot path
5. Open-source core
6. Vendor neutrality and runs-everywhere (cross-cloud, framework-neutral, local-first)
7. Domain knowledge lives in the policy (expert-authored), enforced against live state — no overclaimed consequence prediction (§9.13)
8. Progressive assurance from rules to solver-backed gap-finding
9. Observability-native (OTel/Langfuse): decision spans, policy bootstrapping, backtesting
10. Managed control plane for enterprise governance

The durable moat at OSS stage is **speed, category language, the expert policy-pack corpus, the authoring UX, neutrality, and gap-finding** — not deep consequence-prediction technology (which is infeasible and explicitly out of scope). Be clear-eyed: the runtime verifier alone is clonable; the corpus and the encode-time reasoning compound.

## 18. Metrics

### 18.1 Developer Adoption Metrics

* GitHub stars
* SDK downloads
* Number of integrations
* Number of example apps
* Number of policy packs
* Community contributors

### 18.2 Product Usage Metrics

* Actions evaluated
* Plans evaluated
* Policies defined
* Invariants defined
* Traces generated
* Unsafe actions blocked
* Approvals triggered
* Counterexamples generated

### 18.3 Quality Metrics

* False positive rate
* False negative rate
* Policy evaluation latency
* Solver timeout rate
* Missing-context rate
* Policy test pass rate
* Counterexample usefulness rating

### 18.4 Enterprise Metrics

* Teams onboarded
* Agents governed
* Policy versions deployed
* Audit reports generated
* Managed ARR
* Conversion from OSS to managed

## 19. Technical Requirements

### 19.1 Runtime

* Rust core: a single evaluator shared by the SDK bindings, MCP gateway, and CLI — semantic drift between surfaces is structurally impossible
* Python SDK via PyO3/maturin with prebuilt wheels (`pip install symbolica` stays trivial); TypeScript bindings via napi-rs as fast-follow
* Gateway and CLI ship as static binaries
* StrataDB embedded as the runtime's state substrate: branch simulation, cumulative/session state for cross-call policies, append-only decision log, versioned policies — a library dependency (like SQLite), never external infrastructure
* Local-first execution
* Deterministic rule evaluation
* Portable runtime
* Embeddable in agent applications
* Shadow (log-only) and enforce modes, switchable per policy
* Strong typing for action schemas
* Canonical JSON policy format, schema-validated, content-hash versioned, stored natively in Strata's JSON store
* Trace generation
* OpenTelemetry-based trace emission (observability connectors pluggable; Langfuse first)
* Pluggable solver backend

### 19.2 Performance

MVP target:

* In-process kernel evaluation: sub-millisecond for simple policies (it is arithmetic over a session log); the 50 ms figure is a generous outer bound, not a target
* Gateway-mediated single action: under 10 ms of Symbolica-added overhead on top of the proxied tool call (the gateway hop has its own stated budget; the 50 ms ceiling absorbs network and ledger I/O)
* Plan evaluation: under 100 ms for simple workflows in-process; under 500 ms end-to-end including gateway and state reads
* Solver-backed checks allowed to take longer, with configurable timeout
* Graceful fallback on solver timeout

### 19.3 Security

* Policies should not require secrets
* Runtime should not leak sensitive state in traces by default
* Trace redaction support
* Explicit handling for PII and sensitive fields
* Safe defaults when context is missing
* Deny or escalate on unknown state for high-risk actions

### 19.4 Extensibility

* Custom functions
* Custom state adapters
* Custom approval providers
* Custom solver integrations
* Custom trace sinks
* Custom action registries

### 19.5 Deployment

Supported modes:

* Embedded library
* Local CLI
* Sidecar service
* API service
* Managed cloud control plane

## 20. Policy Language Requirements

The policy language should support:

* Equality checks
* Numeric comparisons
* Boolean logic
* Entity lookups
* Role checks
* Environment checks
* Time/window checks
* Approval checks
* Aggregations
* Cumulative thresholds
* Required context fields
* Policy composition
* Policy versioning
* Test cases

Example:

```json
{
  "policy": "production_optimizer_changes",
  "version": 1,
  "rationale": "Production optimizer-affecting changes on critical workloads need DBA sign-off, impact analysis, and a rollback plan",
  "when": {
    "all": [
      {"state.environment": "production"},
      {"action.effects.includes": "affects_optimizer"},
      {"state.workload.critical": true}
    ]
  },
  "require": {
    "all": [
      {"approval.role": "dba_lead"},
      {"artifact.exists": "impact_analysis"},
      {"artifact.exists": "rollback_plan"}
    ]
  },
  "else": {"decision": "deny"}
}
```

## 21. Verdict Vocabulary

Symbolica returns a **verdict**, not an enforcement action (§9.12). These are the standard verdict categories — a vocabulary that makes the caller's `if`-body easy to write. The caller decides what each one *does*; Symbolica only reports and explains.

### 21.1 Conform

The action satisfies the relevant policies. (The caller typically lets it proceed.)

### 21.2 Violate

The action violates policy — returned with the circumvention pathway / reasoning, which the agent can use to self-correct in real time and the engineer can review in a Langfuse trace. (The caller typically blocks, but may warn-and-log in dev.)

### 21.3 Require Approval

The action or plan may proceed only after specified approval.

### 21.4 Require Context

The system cannot evaluate the policy because necessary context is missing.

### 21.5 Unsafe Policy

The policy itself allows an unintended or unsafe pathway.

### 21.6 Unknown

The system could not determine safety within available model, solver timeout, or incomplete assumptions.

Recommended caller default for high-risk actions:

* Unknown should not mean allow.
* The caller should escalate (require approval) or block, by configuration. Symbolica reports the Unknown verdict honestly; the caller's `if`-body chooses the safe disposition.

### 21.7 Scope of Every Verdict

Every verdict is scoped to what the system verified and observed. Two qualifiers travel with the verdict and its trace:

* **Key provenance** (§9.10): whether the aggregation keys were verified or claimed.
* **Visibility** (§9.11): whether the cumulative state reflects a complete system-of-record view or only this chokepoint's observed stream.

A verdict derived from claimed keys or partial visibility is advisory on the dimension it cannot verify, and the trace says so. The product never presents a chokepoint-scoped result as a business-wide guarantee.

## 22. Example: Database Operations

### 22.1 Scenario

An AI database agent wants to improve performance for a slow workload.

Proposed plan:

1. Run explain
2. Create index
3. Runstats
4. Rebind package
5. Monitor query performance

### 22.2 Policy

Production optimizer-affecting changes require:

* Impact analysis
* DBA approval
* Rollback plan
* Maintenance window unless incident severity is P1

### 22.3 Symbolica Evaluation

Symbolica detects:

* `create_index`, `runstats`, and `rebind_package` affect optimizer behavior
* Environment is production
* Critical workload is affected
* Impact analysis is missing
* Approval is missing

Decision:

```json
{
  "decision": "requires_approval",
  "required": [
    "impact_analysis",
    "dba_approval",
    "rollback_plan"
  ],
  "blocked_steps": [
    "create_index",
    "runstats",
    "rebind_package"
  ]
}
```

### 22.4 Counterexample

If the policy only checked `create_index`, Symbolica could identify:

> The agent can skip index creation, runstats the table, rebind the package, and still change optimizer behavior without approval.

This helps the policy author fix the rule by modeling the broader category `affects_optimizer`.

## 23. Example: Customer Support Refunds

### 23.1 Scenario

A support agent can issue refunds.

Policy intent:

> Refunds over $10,000 require finance approval.

### 23.2 Unsafe Path

Agent issues two refunds:

* $7,500
* $7,500

Each individual refund is below the threshold.

### 23.3 Counterexample

Symbolica returns:

> The policy checks individual refund amount but not cumulative refund amount per customer per incident.

Suggested policy:

> Cumulative refunds over $10,000 per customer per incident require finance approval.

## 24. Example: PII Tool Use

### 24.1 Scenario

An agent wants to send customer data to an external enrichment API.

Policy:

> Customer PII cannot be sent to unapproved external tools.

Symbolica checks:

* Tool destination
* Data classification
* Customer consent
* Approved processor list
* Purpose of processing

Decision:

* Allow if approved
* Deny if unapproved
* Require context if data classification is missing

### 24.2 The Compositional Case (Flagship)

The single-call check above is table stakes — incumbents do it. Symbolica's differentiated value is the compositional leak no per-call scanner can see:

* **Mosaic / aggregation leak**: no single call contains PII, but quasi-identifiers sent across calls to a shared destination re-identify the user (ZIP + DOB + gender → 87% of the US population, per Sweeney). Symbolica tracks an information-disclosure budget per (user, destination); the invariant is "no external party can re-identify a user," a property of cumulative state.
* **Taint laundering**: PII written to an internal field is forwarded by an approved tool to an external one. The ontology tracks taint propagation across the tool→destination graph.

This is the flagship demo (§31). Per-call DLP and content filters — including Bedrock Guardrails — are structurally blind to both classes.

## 25. User Experience Requirements

### 25.1 Developer UX

The developer should be able to:

* Define actions quickly
* Write simple policies
* Run policy tests locally
* See clear traces
* Understand counterexamples
* Integrate with existing agent framework in less than one hour

### 25.2 Policy Author UX

Policy authoring is never hand-writing JSON (§9.8). The policy author should be able to:

* State intent in natural language and review what the system drafts
* Bootstrap policies from observed traffic (learn mode) or starter packs
* Review by consequence: plain-English restatement, generated test cases, and backtests against their own history ("this would have blocked 3 of last month's 12,000 actions — here they are")
* See red-team results: confirmed loopholes and proposed repairs
* Understand what is covered and not covered
* Compare versions as behavioral diffs, not just text diffs
* Edit the generated JSON directly as an expert escape hatch

### 25.3 Security/Compliance UX

Security teams should be able to:

* View all policies
* View all governed agents
* View blocked actions
* View approvals
* Export audit logs
* Review unsafe pathways
* Validate policy coverage

## 26. Open Questions

1. Should Symbolica’s primary public identity be a standalone product or the reasoning layer inside Strata?
2. ~~Should the first SDK be TypeScript or Python?~~ Resolved (June 2026): Rust core with PyO3 bindings — Python package ships first (where agent development concentrates), TypeScript via napi-rs as fast-follow. Both are thin bindings over the same evaluator, reusing strata-python's proven maturin/wheel pipeline.
3. ~~Should the first solver integration be Z3 or cvc5?~~ Resolved (June 2026): Z3 (MIT license, mature Rust bindings, strongest on the linear-arithmetic fragment), behind a `SolverBackend` trait so cvc5 stays swappable. Authoring/CI-time only, never the gateway hot path.
4. ~~Should the policy DSL be custom or compatible with Rego/OPA where possible?~~ Resolved (June 2026): custom JSON DSL; study Cedar (analyzability-by-design) over Rego. OPA/Rego import offered later as a migration funnel, never a constraint on semantics.
5. ~~Should branch simulation require Strata, or should Symbolica support an in-memory branch model independently?~~ Resolved (June 2026): Symbolica embeds StrataDB as a Rust crate dependency, so branch simulation always uses Strata's branch primitive without users deploying or adopting Strata; in-memory mode is Strata's cache mode.
6. ~~Which initial domain should be the flagship demo: refunds, database operations, infrastructure, or PII tool use?~~ Resolved (June 2026): PII leakage — the pain point visible to every AI agent developer. Specifically the mosaic/aggregation leak and cross-tool taint laundering (not the trivial per-call "don't send an SSN," which incumbents already own). See §31.
7. ~~How much LLM-assisted policy authoring should exist in the MVP?~~ Resolved (June 2026): learn mode — drafting baseline policies from observed or imported trace history — is the MVP's LLM-assisted authoring; freeform natural-language authoring is post-MVP.
8. ~~What is the default behavior when state is missing: deny, require approval, or configurable?~~ Resolved (June 2026): configurable, defaulting to escalate (`require_approval`/`require_context`), never allow, for high-risk actions. Implemented in the kernel via tri-state predicates (unknown → `require_context`).
9. How should Symbolica define and expose confidence or assurance levels? (Still open — see §26.1.)
10. How should policy authors test for false positives and false negatives? (Still open — see §26.1.)

### 26.1 Consolidated Open Questions

A single live ledger of what remains undecided across this PRD, the distribution doc, and the kernel spec — ordered by when a decision is needed. Resolved items above and in the other docs are not repeated here.

**Resolved by the GTM research (`symbolica-gtm-research.md`, June 2026):**

* **Insertion priority** — lead with the **MCP gateway in shadow mode** (the chokepoint that compounds, per the OPA lesson, *and* delivers friction-free observability value so it's wanted, not resented); the `verify()` SDK is the secondary on-ramp. Caveat: the gateway is a *manufactured* chokepoint (bypassable), not inherited like the K8s admission webhook — it must be engineered into the path of least resistance.
* **Pricing metric** — charge on governed agents / tool integrations / control-plane seats, **never** verify-per-action (per-action metering taxes the hot path and discourages the instrumentation we want everywhere). Platform/infra budget first; security/compliance budget as audit/gap-finding value matures (Snyk's two-budget path).
* **Open-core cut line** — kernel + SDK + gateway + baseline policy packs stay open (for a trust product, inspectability *is* the trust; relicensing the core is fatal — HashiCorp BSL → OpenTofu); managed control plane + curated corpus + compliance/SSO/RBAC are paid.
* **Dev → economic-buyer motion** — the Snyk two-motion play: developer love first (the circumvention-pathway self-correction loop as the headline benefit, framed LaunchDarkly-style as "the control you own"), then a parallel top-down motion to platform/security. The developer does not write the check.
* **Naming** — rename indicated (§27.8, pending primary-source verification); coin "agent action verification" but speak buyers' existing language in prospect copy.
* **Timing** — design-partner-led and capital-efficient until pull is unambiguous; go-signal = design partners report consequential autonomous agent actions on production + security gating rollouts on action-governance.
* **False-positive rate is the North-Star quality metric** — a blocking control that misfires is resented; shadow mode + high precision are mandatory for adoption.

Still open (the GTM research did not settle these): product identity (#8 below), assurance/confidence exposure (#9), FP/FN *methodology* (#10, distinct from FP-rate-as-metric), and the build-shaping/thesis-critical items.

#### Thesis-critical (resolve before kernel M3 — these determine whether the proof survives a red team)

1. **Verified-key binding** (PRD §9.10; kernel §4) — *promoted from open question to design requirement.* The proof scenario aggregates over agent-supplied `customer_id`/`incident_id`; an agent that varies the key bypasses the cumulative policy. The kernel must carry key provenance (verified vs. claimed) and the demo must aggregate over a verified key, or line 4 only fires against a polite attacker. **Decide the minimum verified-key mechanism before M3.**
2. **Commit-on-approval contract** (kernel §8, §14) — *promoted from deferrable to build-shaping.* If an approved action is not committed to the ledger, the next sub-threshold action bypasses — reproducing the exact loophole inside the product. The gateway's approval→commit semantics must be specified before M6, not bucketed with approval routing.
3. **Money & time representation** (kernel §14). Recommended `i64` minor units (cents) and logical-millis `LogicalTime`. Ratify before M3.
4. **Aggregate forward-compatibility** (kernel §14). Make `Aggregate.over` a list from day one so the mosaic's multi-action budget doesn't force a breaking change.

#### Build-shaping

5. **Visibility / state adapters** (PRD §9.11). What is the minimum adapter that lets cumulative state reflect more than this chokepoint's stream, for the cases where the guarantee must be business-wide?
6. **Build methodology**: a short throwaway Python spike of the DSL semantics before freezing them into Rust, or straight to Rust? Tied to team Rust fluency.
7. **Learn-mode quality** (distribution §6.1). Day-one value depends more on generated-policy quality than on the action ledger (which overlaps with Langfuse for the ICP). Generated-policy quality is on the critical adoption path and needs spec rigor comparable to the kernel.

#### Strategic (long-open, outward-facing)

8. **Product identity** (PRD §26 Q1): standalone product vs. "the reasoning layer inside Strata." Working lean is standalone with Strata as amplifier, but unresolved; drives positioning, naming, and the launch narrative.
9. **Assurance/confidence exposure** (PRD §26 Q9): the progressive-assurance ladder and scoped-claims principle exist, but how a user *sees* which tier of guarantee a given decision carries — including key provenance and visibility scope (§21.7) — is undefined. The product's core credibility surface.
10. **False-positive / false-negative methodology** (PRD §26 Q10): backtesting and the simulator find issues, but the metric for "is this policy set good?" is undefined. Prerequisite for any "certified" claim (§15.4).
11. **Approval experience** (distribution §11) — *promoted to MVP scope.* Most decisions resolve to `require_approval`; who is pinged, how the agent blocks or resumes, and how approval feeds back to `commit` (#2) is the product the buyer actually experiences. A blocked action with no approval path is operationally an error — the first-week trial-killer even under shadow-first.

#### Productization boundary

12. **Open-core cut line**: where the differentiating capabilities sit relative to the free tier — is large-scale adversarial simulation path-count-limited in OSS? Is ontology *learning* open or managed? Tied to §27.4: the clonable kernel means OSS-stage defensibility is speed, not technology. Affects architecture, not just pricing.
13. **Re-identification risk model**: the mosaic demo needs a concrete quasi-identifier threshold model and a measured false-positive profile (§31.3); currently "approximate and configurable."
14. **Collusion / identity-cluster detection**: the sock-puppet-approver and shared-destination grouping both assume identity clustering, referenced but not designed.

#### Deferrable (gateway / integration era)

15. Streaming / long-running MCP tool calls in v1 (distribution §11).
16. Approval routing *mechanism* (block-and-poll vs. webhook vs. HITL MCP response) — distinct from the approval *experience* (#11), which is MVP.
17. Learn mode: local exported trace files vs. live Langfuse API in MVP (distribution §11).
18. JSON Schema validation timing: kernel milestone M1 or M5 (kernel §14).
19. OPA/Rego import as a migration funnel — if and when.
20. **Name / trademark** (§27.8): clear "Symbolica" against Symbolica AI before public launch or handle/domain acquisition.

#### Tracked dependency (not a decision, a coupling)

21. Strata's graph/ontology primitive **already exists**, so the ontology layer is buildable today — this is not a blocking dependency. Strata's next-gen architecture adds a cross-primitive relationship overlay (e.g. KV↔JSON via relationship tags) that *enriches* the ontology but is not required for the basic version. The mosaic demo's gating constraint is therefore the false-positive profile (§31.3), not missing infrastructure.

## 27. Risks

### 27.1 Modeling Cost

Risk:

World-model construction may be too expensive for many users.

Mitigation:

* Start with narrow domains
* Provide templates
* Use LLM-assisted drafting
* Focus on high-risk invariants
* Do not require full formal modeling

### 27.2 Overclaiming Formal Guarantees

Risk:

Users may believe Symbolica proves more than it actually does.

Mitigation:

* Always state assumptions
* Separate rule checks from solver-backed verification
* Use scoped guarantee language
* Provide model coverage indicators

### 27.3 Developer Complexity

Risk:

Developers may not want to learn a new policy DSL. (This is the failure mode that sank prior rule engines: the people with the knowledge couldn't write the syntax; the people who could write it didn't have the knowledge.)

Mitigation:

* Users never write the DSL — all authoring paths are generative (§9.8); the DSL is a reviewable IR, not a UI
* Review by consequence: test cases and backtests, not syntax reading
* Simple, human-readable canonical JSON for the audit/diff/escape-hatch roles it retains
* SDK-first integration
* Clear traces and tests

### 27.4 Competitive Compression

Risk:

Existing policy engines or agent frameworks add similar features. Sharper form: the kernel is small and clonable by design, so the OSS artifact (wrapper + gateway + cumulative aggregates) is roughly what LangGraph or the OpenAI Agents SDK could bundle as middleware in a quarter. The durable moats — regression corpus, simulator at scale, learned ontology — are the components furthest from the MVP and possibly managed-only. **OSS-stage defensibility is therefore speed and category language, not technology**, and the launch plan is paced accordingly.

Mitigation:

* Move quickly on agent-native UX; treat time-to-category-ownership as the metric, not feature count
* Differentiate with branch simulation and the learned ontology — the parts that are not a quarter's work to copy
* Build strong OSS community
* Own the category language around verifiable agent actions

### 27.5 Solver Limitations

Risk:

Solver checks may be slow, incomplete, or difficult to explain.

Mitigation:

* Use solvers only where valuable
* Support timeouts
* Provide fallback decisions
* Keep initial constraints simple
* Invest heavily in counterexample UX

### 27.6 Untrusted Keys and Partial Visibility

Risk:

Cumulative policies (a side tool — §6.0) assume trustworthy aggregation keys and complete visibility, but keys are agent-supplied and the gateway sees only its own stream (§9.10, §9.11). An agent can vary a grouping key to bypass a cumulative policy, and out-of-band actions are invisible — so the verified property can be materially weaker than the business invariant the buyer hears.

Mitigation:

* Key provenance (verified vs. claimed) carried on every aggregate and surfaced in the trace
* Govern key-minting actions so the upstream move stays in the policed stream
* State adapters into systems of record to widen visibility where the guarantee must be business-wide
* Never present a chokepoint-scoped result as a business-wide guarantee (§21.7)

### 27.7 Mosaic Policy False Positives

Risk:

The flagship disclosure-budget policy may fire on the median enrichment request, reading as a broken tool rather than a leak detector (§31.3).

Mitigation:

* Measure the false-positive profile on real traces before any live enforcement demo
* Lead with the refund demo; frame mosaic findings as discovery until the profile is credible
* Tune threshold and approved-destination model; escalate ambiguous cases rather than block

### 27.8 Name Collision — Rename Indicated

Risk (GTM research, June 2026): "Symbolica" is crowded and collides directly in-niche. Two material collisions surfaced:

* **Symbolica AI** (George Morgan) reportedly active in 2026 and pivoted into agent infrastructure (an "Agentica" agent SDK + commercial platform) — a direct adjacency to "verification layer for AI agents," maximal confusion risk.
* **Siemens** reportedly holds a live US federal trademark on "SYMBOLICA" in Class 9 software — a likelihood-of-confusion exposure for an overlapping software/AI product.
* symbolica.ai / .io, the GitHub org, and the npm scope appear occupied.

**Verify before acting:** these specifics come from an LLM-driven research pass and must be confirmed against primary sources (USPTO TSDR for the Siemens Class 9 mark; Companies House / the live product for Symbolica AI's status and niche) before any rename spend or legal opinion — deep-research can state fabricated specifics confidently. The *direction* (rename) is robust regardless of any single citation.

Mitigation:

* Treat rename as the leading pre-launch action (§26.1 #20); confirm the two load-bearing facts against primary sources first.
* Coin a crisp category descriptor ("agent action verification" / "action governance") for ownership, but in prospect-facing copy ride the language buyers already search ("guardrails," "policy-as-code for agents," "AI governance") — per the Wiz "talk the way your prospect thinks" lesson.

## 28. Launch Strategy

### 28.0 Phase 0: Customer Discovery (gates everything below)

Before any engineering, validate the thesis with ~20–30 problem-discovery interviews with engineers building agents that take real actions. Full plan in `Symbolica-discovery.md`. Unlike Strata (a better mousetrap in a known category), Symbolica is a category-creation bet where the cost-bearer (developer) differs from the value-receiver (business/compliance) and the pain may be anticipated rather than felt — so discovery is designed to *kill* the thesis cheaply, not confirm it.

The existential question: are the dangerous failures developers actually face compositional/stateful (validating the cumulative-state wedge and the whole differentiated architecture), or mostly single-call (which a content filter handles)? Outcomes: **GO** (build the kernel), **PIVOT** (re-aim the wedge), or **WAIT** (right thesis, early market). The kernel spec stays ready but unbuilt until a GO signal; a refund demo may serve as a later reaction prop. Engineering spend on `symbolica-core` does not begin until Phase 0 resolves.

### 28.1 Phase 1: Open-Source Prototype

Launch with:

* GitHub repo
* Runtime verification kernel (`verify(tool_call) → verdict + reasoning`)
* SDK with one-line `verify()` insertion; MCP gateway as the opinionated block-on-violate deployment
* Database-operations policy pack (effect-category floor + live-state envelopes) — the beachhead
* Encode-time policy compiler (author-by-intent → compiled verifier)
* Verdict trace engine with circumvention-pathway explanations (agent self-correction + Langfuse review)
* CLI
* Blog post explaining the thesis

Positioning:

> Symbolica is the open-source verification layer for AI agents that take action — starting with agents that touch production databases.

### 28.2 Phase 2: Developer Adoption

Add:

* LangGraph integration
* OpenAI tool-call middleware
* Langfuse connector (OTel-based): decision-span write-back, trace import, learn mode, policy backtesting
* Agent framework examples
* Policy templates
* Counterexample generation
* Community docs

### 28.3 Phase 3: Managed Beta

Target:

* Startups building enterprise agents
* Internal platform teams
* AI automation teams
* Regulated workflow teams

Managed features:

* Hosted policy registry
* Audit logs
* Team access
* Approvals
* Dashboards
* Compliance exports

### 28.4 Phase 4: Enterprise Product

Add:

* SSO
* RBAC
* SOC 2
* Private deployment
* Advanced solver support
* Policy packs
* Enterprise connectors
* Agent fleet governance

## 29. Packaging

### 29.1 Open Source

Free:

* Core runtime
* CLI
* SDK
* Local policy evaluation
* Basic traces
* Local examples
* Basic solver integration

### 29.2 Managed Developer Tier

For small teams:

* Hosted policy registry
* Audit logs
* Hosted traces
* Team collaboration
* Limited managed solver checks

### 29.3 Enterprise Tier

For enterprises:

* SSO
* RBAC
* Private deployment
* Advanced audit
* Compliance exports
* Approval workflows
* Policy packs
* Dedicated support
* Managed high-assurance verification

## 30. Positioning

### 30.1 Primary Positioning

**Symbolica is the reasoning and verification layer for AI agents that take action.**

### 30.2 Alternative Positioning

* The control plane for state-changing agents.
* Open-source policy and verification for AI agents.
* Let agents act safely.
* Verified guardrails for agentic workflows.
* A neurosymbolic runtime for auditable AI actions.

### 30.3 Avoided Positioning

Avoid leading with:

* Formal methods platform
* Theorem proving for agents
* General neurosymbolic AI
* AI safety platform
* Enterprise governance platform

These are either too academic, too broad, or too crowded.

## 31. Demos: Launch Act and Vision Act

Demos sequenced by buildability and beachhead fit. The **launch/live demo is database operations** — the beachhead (§6.0), buildable on the kernel, viscerally real to the buyer. The refund-splitting and mosaic-PII demos are kept as *expansion/vision* illustrations of the same verification primitive applied to other domains; lead with databases.

### 31.1 Launch Demo: The Agent That Tried to Drop the Schema

The floor under a confidently-wrong agent — the 10-second gut punch, buildable on the kernel (`verify` + effect-category policy + live state):

1. A DBA states intent: destructive ops on production need approval; sort memory must stay within the host's safe envelope.
2. Agent, "fixing" a corrupted table, proposes `drop_schema(production)` → **Violate**, with the reasoning. Every DBA in the room flinches.
3. Agent raises `SORTHEAP` to clear query queuing → Symbolica evaluates the DBA's envelope against *live* concurrency and host memory → **Violate**, quoting the arithmetic. It caught a locally-reasonable change the agent couldn't foresee — not by predicting the cascade, but by enforcing the expert's envelope.
4. The verdict's reasoning lets the agent self-correct (propose a smaller value, or route to approval) in real time.
5. Replay against the team's Langfuse history; show it would have caught real near-misses.
6. Full verdict trace for audit.

Needs no ontology, no solver, no prediction. It makes the single point a DBA feels in their gut: your agent will confidently do something catastrophic, and this is the floor that stops it — and it carries the founder's Db2 credibility.

### 31.2 Expansion Illustrations: Refund Splitting and the Mosaic PII Leak

These show the *same verification primitive* applied to other domains, as the expansion story — not the launch demo.

**Refund splitting** (cumulative state, a side tool — §6.0): define "no >$10k per customer per incident without finance"; the agent splits into two sub-threshold refunds; Symbolica catches the second via a ledger-backed `State`. Small and incontestable, useful as a concept primer.

**The mosaic PII leak — No Single Call Was Wrong:**

The flagship *vision*: PII leakage, the pain point visible to every AI agent developer on the planet. The *obvious* PII demo ("agent sends an SSN externally, Symbolica blocks it") is a trap — it is a per-call content scan already owned by Presidio, Nightfall, Lakera, OpenAI moderation, and Bedrock Guardrails' PII protection. Leading with it makes Symbolica look like a weaker DLP filter.

The vision demo instead shows the loophole class no per-call scanner can catch by construction: the **mosaic (aggregation) leak**, plus cross-tool **taint laundering**.

### Scenario

A customer-support / data-enrichment agent — the most common agent archetype — answers questions, enriches CRM records, and calls external tools (geocoding, enrichment, analytics, summarizers, webhooks).

* **The real requirement (invariant):** no external party should ever receive enough information to re-identify an individual. This is a statement about cumulative state at a destination, not about any single call — which is precisely why per-call tools cannot enforce it.
* **What developers write today (all per-call):** don't send email/SSN/phone externally; PII fields need consent; external destinations must be allow-listed. Content filter on. Looks airtight.

### The Chain the Simulator Finds

Each call is individually compliant and passes every content filter:

1. ZIP code → geo-enrichment tool (not PII alone — allowed)
2. Birthdate → analytics tool for "cohort analysis" (not PII alone — allowed)
3. Gender → segmentation tool (allowed)
4. The ontology knows all three tools funnel to the same downstream vendor
5. That vendor now holds {ZIP, birthdate, gender} for one user — re-identifying them with ~87% probability

The 87% figure is Latanya Sweeney's foundational de-identification result (ZIP + date-of-birth + gender uniquely identifies 87% of the US population). It is citable and makes the leak mathematically incontestable.

Taint-laundering variant (same demo, second class): the agent writes a full name into an internal "notes" field (allowed); an approved summarizer pulls notes into its output; an approved webhook ships it externally. The ontology traced `notes → summarizer → webhook → external`. Every step clean per-call.

### Demo Flow

1. Shadow-deploy Symbolica over the existing support agent; import recent traces.
2. The ontology learns field classifications (quasi-identifiers) and the tool→destination graph.
3. The privacy lead states intent in plain English; Symbolica drafts the invariant and policies.
4. `symbolica simulate` runs millions of adversarial call orderings overnight.
5. Reveal: a 3-call sequence, each step green-checked against every written policy, with a re-identification meter climbing to threshold on the fourth beat — "every call was allowed; the outcome re-identifies your user."
6. Cite Sweeney; show the assembled mosaic.
7. Symbolica proposes the missing invariant: an information-disclosure budget per (user, destination) across all externally-reaching tools.
8. Re-simulate: clean.
9. Backtest against real traces: "this pattern occurred N times last month."
10. Full audit trace for the DPO.

### Why It Is Undeniable

* Universal pain — every agent developer touches user data plus external tools.
* Mathematically incontestable — the Sweeney result ends the argument.
* Structurally impossible for incumbents — per-call DLP, content filters, and Bedrock Guardrails' per-request PII detection are blind to the mosaic by construction; the leak lives in the sum of requests. The demo is the competitive argument against AWS.
* Exercises every Symbolica capability: ontology (quasi-identifier classification, destination graph, taint propagation), cumulative state (disclosure budget), simulator (finds the re-identifying combination), invariant-over-state, and the backtest kill-shot.

### Honesty Note

Precise re-identification risk is a research-grade problem (k-anonymity, information theory, differential privacy). The demo does not claim a proof — it performs structural detection: these quasi-identifiers, to this destination, cross a configured threshold. The risk model is configurable and approximate; when disclosure is ambiguous, tri-state semantics escalate rather than guess. This fits the "prove what's provable, escalate the rest" principle (§9.2, §9.7).

### 31.3 The False-Positive Gate (why the mosaic is the vision act, not the launch act)

The disclosure-budget policy may fire constantly on real CRM-enrichment traffic — sending ZIP/DOB/segment data to shared vendors is what those workflows *do*. The backtest line "this pattern occurred N times last month" is a kill-shot only if N is small; if N is in the thousands, the demo proves the flagship policy is unenforceable noise, not a leak detector. Before the mosaic is shown live:

* Measure the false-positive profile against real enrichment traces.
* Tune the threshold and the approved-destination model until findings are credible (a true leak should be rare and explainable, not the median request).
* Until then, frame mosaic findings as "here are the re-identifying flows you may not know about" (discovery), not "blocked" (enforcement) — and keep the refund bypass (§31.1) as the live demo.

A high N is not necessarily failure — it may be a real finding — but a policy that fires on the median request reads operationally as a broken tool, which is fatal in a trial. The threshold model and this measurement are open (§26.1 #9, #19).

## 32. Strategic Fit With Strata

Symbolica can be standalone, but it becomes more powerful when paired with Strata.

Strata provides:

* State
* Branches
* Events
* Memory
* Data model
* Agent runtime surface
* Commit/merge semantics

Symbolica provides:

* Rules
* Policies
* Invariants
* Traces
* Solver checks
* Counterexamples
* Explanations

Combined product:

> Strata is the verifiable state layer for AI agents, powered by Symbolica.

This creates a coherent platform for safe agent state mutation.

### 32.1 Architectural Pairing

The pairing is structural, not just strategic. Both are Rust: Symbolica's core depends on Strata's `executor` crate directly (in-process, no FFI boundary), and uses Strata's primitives as its runtime substrate:

* Branch primitive → plan simulation (fork, apply effects, diff, merge or discard)
* KV/JSON with version history → policy storage and versioning
* Event log → append-only decision ledger (the audit/compliance export)
* Time travel → "replay this decision as of policy v3"
* Cache mode → in-memory simulation and ephemeral session state
* Graph/ontology primitive (exists today; next-gen adds a cross-primitive relationship overlay, e.g. KV↔JSON via relationship tags) → the learned domain ontology (§10.2.1), with no graph infrastructure built by Symbolica

The gateway and CLI embed Strata the way an application embeds SQLite — users adopt Symbolica without ever deploying Strata. Symbolica also reuses Strata's proven distribution pipeline (PyO3/maturin wheels, npm bindings, cargo CLI, Homebrew tap).

## 33. Summary

Symbolica should become the open-source neurosymbolic reasoning layer for agents that take consequential actions.

The immediate product should focus on practical agent safety:

* Define actions
* Define policies
* Evaluate plans
* Produce traces
* Require approvals
* Generate counterexamples
* Integrate with existing agent frameworks

The long-term product should evolve toward solver-backed and proof-backed verification for high-risk workflows.

The opportunity is large because as agents become more autonomous, every enterprise will need a way to answer:

**Can this agent safely do what it is about to do?**

Symbolica is the layer that answers that question.
