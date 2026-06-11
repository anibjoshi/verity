# Verity Kernel Spec

The buildable specification for the smallest unit that proves Verity's concept. Companion to the PRD (`Verity-PRD.md`). This document is the contract for the first commit.

> Note (June 2026): this spec predates the pivot to building into an open agent harness and the catastrophe-floor framing; it still leads with the database-operations example. It is a current build artifact but warrants a light reconciliation pass to the harness/catastrophe-floor framing of the PRD before implementation.

> Reconciled (June 2026) to the converged thesis: Verity is a **verification layer**, not a blocking layer. The kernel proves the runtime **verification primitive** — `verify(action, state, policy) → verdict + reasoning` — for the **database-operations beachhead**. Enforcement, cumulative-state policies, and the encode-time compiler are layers around this primitive, not part of it.

## 1. Purpose

Build the smallest thing that proves the core loop: an agent proposes a database action, Verity verifies it against an author-by-intent policy using the **current system state**, and returns a verdict — conform / violate / can't-determine — with the reasoning. What the caller *does* with the verdict (block, escalate, ask a human, let the agent self-correct, log) is the caller's `if`-body, not the kernel's concern.

Two things are proven at once:

1. **The product** — Verity is the `if`-condition in an agent's execution path. `verify(tool_call)` returns a verdict the agent or developer acts on. Domain knowledge lives in the *policy* (authored by the expert); the kernel never infers it.
2. **The architecture bet** — the verifier reads live system state through Strata's `executor` crate and evaluates deterministically, fast enough for the agent's hot path.

### Scope boundaries

- **In scope:** the runtime verifier — parse a compiled policy (JSON), evaluate an action against live state, return verdict + reasoning. Two policy kinds: an **effect-category floor** (destructive/disruptive actions) and a **derived-quantity envelope** over live state.
- **Out of scope (later layers, not the kernel):** the encode-time compiler (Z3 + LLM enumerating cases and circumvention pathways — §7), enforcement of any kind, cumulative cross-call policies (the session-ledger is one *state source*, not the center), the gateway, SDK bindings, the ontology, the simulator.

The kernel returns verdicts. It does not block, route, or enforce.

## 2. The Proof Scenario (database operations)

Two checkable cases, both buildable on the kernel, neither requiring the encode-time compiler.

### 2.1 The effect-category floor (the 10-second gut punch)

An agent, "fixing" a corrupted table, proposes to drop and recreate the schema:

```
verify( drop_schema(name="SALES", env="production") )
  → VIOLATE
    policy:    no_destructive_ops_without_approval
    reasoning: "drop_schema is a destructive, irreversible operation on a
                production schema; policy requires human approval."
```

Pure policy over a declared effect category (`destructive`, `irreversible`). No prediction, no live state needed. This is the floor under a confidently-wrong agent, and it is the simplest demo any DBA feels in their gut.

### 2.2 The envelope over live state (the real one)

An agent raises sort memory to clear query queuing. The DBA's *own knowledge* is encoded as an envelope policy; Verity evaluates it against **current** system state:

```
state:  { max_concurrency: 200, host_mem_mb: 65536, sortheap_mb: 8 }
verify( set_db_cfg(param="SORTHEAP", value_mb=64) )
  → VIOLATE
    policy:    sort_memory_envelope
    reasoning: "potential aggregate sort memory (64MB x 200 concurrent)
                = 12800MB exceeds host_mem x 0.15 safety budget (9830MB)."
```

The domain knowledge (`sortheap × max_concurrency < host_mem × safety`) is the *DBA's*, written once as policy. The kernel supplies no database physics — it evaluates a derived quantity against live state. Same evaluation machinery as 2.1, plus a live-state read.

**Line 2.2 is the company:** Verity catches a locally-reasonable change that the agent couldn't foresee and a busy human would have rubber-stamped — not by predicting consequences (infeasible, out of scope) but by enforcing an envelope the expert articulated, tirelessly, against live state.

### What this is NOT

Not the refund-splitting / cumulative-ledger proof from the earlier draft. Cumulative-across-calls policy is a *side tool* (§6), not the spine. The spine is **verify an action against author-by-intent policy using live state, return verdict + reasoning.**

## 3. Authoring Order — JSON Before Rust

Milestone M0 has no Rust. Hand-write `policies/db_ops.json` (§5) — both the effect-floor and the envelope — and iterate until it reads well. This JSON is the *compiled* policy form that the encode-time compiler (§7) will eventually generate; getting its shape right by hand now is cheap. Rust begins only once the shape is agreed.

## 4. Core Data Model

Rust sketches — illustrative, not final. `serde_json` only; no custom parser.

```rust
// model.rs

/// A proposed agent action — the unit verify() evaluates.
pub struct Action {
    pub name: String,                          // "drop_schema", "set_db_cfg"
    pub effects: Vec<String>,                  // declared categories: ["destructive","irreversible"]
    pub args: serde_json::Map<String, Value>,  // {param, value_mb, env, ...}
    pub actor: Actor,
}

pub struct Actor { pub id: String, pub roles: Vec<String> }

/// Injected logical time — the kernel NEVER reads the wall clock (§9).
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct LogicalTime(pub i64);

/// The verification result. NOT an enforcement action — a verdict the caller acts on.
pub enum Verdict {
    Conform,
    Violate { policy: String, reasoning: String, pathway: Option<Pathway> },
    Indeterminate { missing: Vec<String> },    // tri-state unknown: state incomplete (§8)
}

/// The circumvention pathway. In the kernel this is the violation explanation;
/// the encode-time compiler (§7) later enriches it with pre-enumerated evasion routes.
pub struct Pathway { pub description: String, pub detail: String }
```

`Verdict` is the whole output. There is no `block`/`deny`/`enforce` — those are the caller's `if`-body. The six PRD dispositions (allow/deny/require_approval/require_context/unsafe/unknown) are a *vocabulary* the caller maps onto; the kernel returns the three structural outcomes above plus reasoning.

## 5. The Policy Format

Canonical JSON, `serde_json`-deserialized. The demo file carries both policy kinds:

```json
{
  "actions": {
    "drop_schema": { "effects": ["destructive", "irreversible"],
                     "inputs": { "name": "string", "env": "string" } },
    "set_db_cfg":  { "effects": ["config_change"],
                     "inputs": { "param": "string", "value_mb": "number" } }
  },

  "policies": {
    "no_destructive_ops_without_approval": {
      "rationale": "Destructive, irreversible operations on production require human approval",
      "on_effect": "destructive",
      "when": { "eq": [ { "arg": "env" }, "production" ] },
      "verdict": "violate"
    },

    "sort_memory_envelope": {
      "rationale": "Aggregate sort memory must stay under 15% of host RAM",
      "on": "set_db_cfg",
      "when": {
        "and": [
          { "eq": [ { "arg": "param" }, "SORTHEAP" ] },
          { "gt": [ { "mul": [ { "arg": "value_mb" }, { "state": "max_concurrency" } ] },
                    { "mul": [ { "state": "host_mem_mb" }, 0.15 ] } ] }
        ]
      },
      "verdict": "violate"
    }
  }
}
```

`rationale` carries the intent in plain language (PRD §9.8) — quoted in the verdict's reasoning, not a comment. Note both `{ "arg": ... }` (from the action) and `{ "state": ... }` (live system state) as operands.

### Expression grammar (minimal, principled)

```
Expr ::=
  | Literal                          number | string | bool
  | { "arg": name }                  the action's argument
  | { "state": field }              live system state (§6) — may be missing → Unknown
  | { "<op>": [Expr, Expr] }         add sub mul  |  gt ge lt le eq ne
  | { "and": [...] } | { "or": [...] } | { "not": Expr }    Kleene logic
```

A policy fires when its `when` is True (→ its `verdict`); Unknown `when` → `Indeterminate`; False → conform-for-this-policy.

## 6. State: Live-First, Ledger as a Special Case

The kernel evaluates against **live system state** — current concurrency, host memory, current config — read at verify time. This is the central dependency (it replaces the earlier draft's session-ledger-centric model).

```rust
// state.rs
pub trait State {
    /// Read a live system field. None → Unknown (drives Indeterminate, §8).
    fn get(&self, field: &str) -> Option<Value>;
}
```

Two implementations, two milestones:

- **M3 — `StaticState`** (a JSON snapshot): proves evaluation logic without integration risk.
- **M6 — `StrataState`**: live system state surfaced through Strata's `executor` crate. (Exact `executor` binding owned by the Strata architect; design against the `State` trait, swap at M6.)

**Cumulative policy is one kind of state, not the spine.** A cross-call policy ("aggregate refunds per customer") is served by a `State` implementation that folds an append-only log — useful, but a *special case* of the `State` seam, not the kernel's center. The refund example becomes a secondary test, not the proof.

## 7. Encode Time vs Runtime (the boundary the kernel sits on)

The full product has two phases; the kernel is only the second:

- **Encode time (NOT in the kernel):** the user defines a policy as intent. A compiler uses Z3 + LLMs to enumerate the cases that need handling and the **circumvention pathways**, and emits the compiled policy JSON (§5) plus an evasion catalog. Expensive, one-time per policy version.
- **Runtime (THE KERNEL):** `verify(action, state, policy)` evaluates against the compiled policy and live state. Fast, deterministic, **no Z3, no LLM in the hot path.**

The kernel produces the *violation reasoning* (why this action violates — the seed of the pathway). The encode-time compiler later enriches `Pathway` with pre-enumerated evasion routes. Crucially, explaining the pathway is safe *because* the encode-time enumeration already closed the evasion space — but that completeness property is an encode-time concern; the kernel just reports the violation it found.

## 8. The Verify Function & Tri-State

```rust
// verify.rs

/// PURE. Deterministic in (action, state, now, policies). No I/O, no clock, no globals.
pub fn verify(
    action: &Action,
    state: &dyn State,
    now: LogicalTime,
    policies: &PolicySet,
) -> Verdict;
```

Predicates evaluate to `True | False | Unknown` (Kleene logic). `Unknown` arises when `{ "state": ... }` is missing — e.g. live state couldn't be read. It propagates; a policy whose `when` is Unknown yields `Indeterminate { missing }`. This is the honest "I can't verify this" outcome — the caller decides what that means (the PRD's `require_context`), the kernel never guesses.

Resolution across policies: any `violate` fires → `Violate` (first/most-specific wins, with all contributing policies in the reasoning). Else any `Indeterminate` → `Indeterminate`. Else `Conform`. The kernel expresses no preference about what the caller does with a `Violate` — that is the `if`-body.

`Unknown` is also the neurosymbolic seam: today `{ "state": x }` binds from a live read; later a predicate may bind from an LLM classifier with a confidence threshold, low confidence → `Unknown`. The kernel does not change; the binding source does. Reserve a `binding` provenance field on evaluated predicates (`live` for now; `inferred | confirmed` later).

## 9. Determinism Constraints (Non-Negotiable, Day One)

Free now, expensive to retrofit; the simulator/gap-finder (PRD §10.2.11) depends on all three.

1. **Pure function.** `verify` is a pure function of its arguments. No `SystemTime::now()`, no RNG, no I/O, no mutable globals.
2. **Virtual time.** Logical time is injected via `LogicalTime`; the kernel never reads a real clock.
3. **Seeded determinism end-to-end.** Same inputs → same `Verdict`, byte-for-byte.

A replay test (M7) runs a fixed action+state sequence twice and asserts identical verdicts.

## 10. Verdict Output (the audit artifact)

```rust
pub struct VerdictReport {
    pub action: String,
    pub verdict: Verdict,
    pub evaluated: Vec<PolicyEval>,  // every policy considered, with its result
    pub state_used: Vec<(String, Value)>, // which live-state fields were read (provenance)
    pub time: LogicalTime,
}

pub struct PolicyEval {
    pub policy: String,
    pub rationale: String,           // quoted from the policy
    pub result: TriBool,
    pub detail: String,              // "64 x 200 = 12800 > 9830"
    pub binding: Provenance,         // live (neural-seam stub, §8)
}
```

Two consumers, per the product (PRD): the **agent** (reads the reasoning/pathway and self-corrects its tool call in real time) and the **engineer** (reviews the verdict later in a Langfuse trace). The report is the same; the consumer differs.

## 11. Crate Layout & Dependencies

```
symbolica-core/
  Cargo.toml
  policies/
    db_ops.json            # M0 — hand-written first
  src/
    lib.rs
    model.rs               # Action, Actor, Verdict, Pathway, LogicalTime
    policy.rs              # PolicySet, Policy, action schema (serde)
    expr.rs                # Expr, TriBool, Kleene logic
    state.rs               # State trait, StaticState, (later) StrataState
    verify.rs              # verify(), resolution
  examples/
    db_ops.rs              # the proof binary (§2 output)
  tests/
    effect_floor.rs        # drop_schema → Violate
    envelope.rs            # sortheap over live state → Violate
    determinism.rs         # M7 replay test
```

Dependencies: `serde`, `serde_json`, `thiserror`. Added at M6: the Strata `executor` crate. No solver, no LLM, no async — synchronous and tiny.

## 12. Build Milestones

The proof is **M3**.

| M | Deliverable | Acceptance test |
|---|---|---|
| M0 | Hand-written `db_ops.json` (effect floor + envelope) | Reads cleanly; reviewed |
| M1 | Data model + serde deserialization | Round-trips `db_ops.json` |
| M2 | Expression eval + effect-category matching, two-valued | `drop_schema(env=production)` → `Violate` (§2.1) |
| M3 | `StaticState` + derived-quantity envelope | **Envelope over live state → `Violate` with arithmetic (§2.2)** |
| M4 | Tri-state + `Indeterminate` | Missing live-state field → `Indeterminate`, not silent conform |
| M5 | `VerdictReport` + reasoning/pathway rendering | §2 verdicts render with quoted rationale + detail |
| M6 | `StrataState` over the `executor` crate | Both proofs pass on live Strata-surfaced state |
| M7 | Determinism harness | Replay-twice asserts identical verdicts |

After M7 every later layer attaches to a seam already present: the `State` trait (live + ledger + future adapters), the tri-state binding (neural classifiers), the pure `verify` (the gateway hot path), the `Pathway` (encode-time evasion enrichment), `Verdict` (the caller's `if`-body).

## 13. How the Kernel Grows (seams already present)

| Kernel piece | Grows into |
|---|---|
| `verify → Verdict` (no enforcement) | The `if`-condition; gateway = an opinionated deployment that wires the body to block-on-violate |
| `effects: [...]` + effect-category policy | The floor; effect ontology over Strata's graph |
| `{ "state": ... }` + `State` trait | Live system-state adapters; ledger-backed aggregates for cumulative side-policies |
| Derived-quantity envelopes | Expert-authored resource policies (the policy-pack corpus moat) |
| `Pathway` (violation reasoning) | Encode-time Z3+LLM evasion enumeration; agent self-correction signal |
| `TriBool` + `binding` | Neural classifier binding; Unknown → caller escalates |
| Determinism | The gap-finder ("does the rule set have holes?") |
| Compiled-policy JSON | The encode-time compiler's output target |

Nothing above reworks the kernel — each is a new consumer of an existing seam.

## 14. Open Implementation Questions

**Decide before M3:**
1. **Numbers** — `i64` minor units (cents / MB as integers), not `f64`: aggregates plus floats invite drift. Ratify before M3.
2. **Live-state read shape** — what `State.get` returns for database fields, and the minimum field set for the envelope demo (`max_concurrency`, `host_mem_mb`, current config). This is the central integration question for the beachhead.

**Build-shaping:**
3. `LogicalTime` units — recommend logical millis from the start.
4. Policy/action JSON Schema validation — load-time (recommended) vs. deserialize-and-trust; M1 or M5.
5. Verdict resolution when multiple `violate` policies fire — return all in reasoning; confirm ordering is deterministic.

## 15. Definition of Done

The kernel is proven when, on live Strata-surfaced state (M6) with the hand-written `db_ops.json` (M0), the example binary emits the two §2 verdicts — `drop_schema(production)` → `Violate` on the effect floor, and the sortheap envelope → `Violate` with the arithmetic against live concurrency and host memory — each carrying quoted rationale, and the determinism test (M7) passes. At that point Verity does the core thing: it **verifies** an agent's proposed database action against author-by-intent policy using live state, and returns a verdict with reasoning — leaving enforcement to the caller. The architecture bet on Strata's `executor` for live state is validated.
