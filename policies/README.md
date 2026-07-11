# policies/

Compiled-policy JSON, **versioned in git** — Verity has no separate data layer
(PRD §8.4–8.5). The encode-time compiler (`encode/`) emits these; `verity-core`
reads them at runtime as pure data.

## `floor.json` — the catastrophe floor (kernel-spec M0)

Hand-written first (JSON before Rust, kernel-spec §3); the compiled form the
encode-time compiler will eventually emit. Six floor classes, each as a pair:

| kind | fires on | disposition |
|---|---|---|
| **provenance envelope** (`no_tainted_*`) | the floor action on a tainted path — provably illegitimate | `deny` |
| **effect floor** (`*_floor`) | the floor action itself, any provenance | `require_approval` (the corpus's `confirm`) |

Illegitimacy is established either by **taint** (injection — the envelope
denies) or by **the human at the confirmation gate** (hallucination — the floor
confirms); the kernel never judges legitimacy semantically. Floor criterion:
*a reasonable user would never want this done silently* (corpus-spec §4.1's
four-quadrant model).

Structure: `capabilities` (the normalized taxonomy the adapter maps tool calls
onto), `context_fields` (the context contract — taint per argument, harness
memory like allowlists/payees/threshold; a missing field is Unknown, never a
silent default), `predicates` (the named floor predicates with their data —
pattern sets are RE2-compatible regex), `policies` (the twelve rules), and
`resolution` (highest-severity-wins, Kleene tri-state).

Alignment with the eval corpus is checked mechanically (every
`ground_truth_secret` matches `is_secret`; controls don't; same for the
destructive-command and self-modification pattern sets) — see the M0 PR for
the alignment report and the known, deliberate deltas.
