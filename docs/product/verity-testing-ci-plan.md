# Verity Testing & CI Plan

*Companion to `kernel-spec.md` (the `verity-core` library), `verity-eval-plan.md` (the Phase 0 harness), and PRD §8.5 (the stack). Testing is first-class **here** specifically: the library's entire value proposition is **determinism + correctness + a tiny auditable TCB**. For a security tool, the test suite is part of the trust model — green CI is the running proof that the guarantee hasn't rotted.*

---

## 1. What we are actually testing for

The verifier's worth is not "it works" — it's a set of *guarantees*. The suite proves each one directly, not as a side effect:

1. **Determinism** — same inputs → byte-identical verdict, always (kernel-spec §11).
2. **Purity** — `verify()` reads no clock, no RNG, no filesystem, no network (kernel-spec §11). The TCB cannot be influenced by anything but its arguments.
3. **Fail-closed honesty** — missing provenance/context → `Indeterminate`, never a silent allow; unexpressible disposition → fail closed (PRD §6.2, §8.6).
4. **Panic-freedom on hostile input** — the policy JSON and the normalized action are *untrusted*; arbitrary bytes must produce an error, never a crash.
5. **The floor catches what it claims, and stays quiet otherwise** — coverage on attacks, low false-positives on controls (the noise budget — the #1 metric, PRD §10).

A test that doesn't map to one of these is probably testing the wrong thing.

## 2. Test pyramid by component

### 2.1 `verity-core` (Rust) — the TCB, highest bar

- **Unit tests** — expression eval, Kleene logic (`True`/`False`/`Unknown` propagation), named predicates, the matcher algebra (`equals`/`regex`/`one_of`/`gt|ge|lt|le`), and verdict resolution (any `violate` → `Violate`; else any `Unknown` → `Indeterminate`; else `Conform`).
- **Floor acceptance tests** — the kernel-spec §2 scenarios as fixtures: secret read → `Violate(deny)`; tainted external send → `Violate(require_approval)`; missing taint → `Indeterminate(escalate)`. These are the canonical "it does the core thing" tests.
- **Determinism replay (M7)** — run a fixed `(action, context, policy)` sequence twice; assert the two `VerdictReport`s are **byte-identical**. A hard gate.
- **Property tests** (`proptest`) — invariants over generated inputs: determinism under re-evaluation; "`Unknown` in a fired policy's `when` ⇒ verdict is `Indeterminate` or `Violate`, never `Conform`"; "no `violate` policy fires ⇒ not `Violate`"; Kleene-logic algebraic laws.
- **Purity enforcement** — the kernel must not reach for ambient authority. Enforced, not just hoped: `cargo-deny`/lint to ban `std::time`, `std::fs`, `std::net`, and `rand` from the `verity-core` crate; a CI grep for `SystemTime::now`/`Instant::now` as a backstop. (`LogicalTime` is injected; the clock is never read.)
- **Fuzzing** (`cargo-fuzz`/libFuzzer) — two targets: the **policy deserializer** (`serde_json` → `PolicySet`) and the **action evaluator**. Property: arbitrary bytes → `Err` or a verdict, **never a panic**.
- **No-panic discipline** — `verify()` surfaces errors as values; adversarial policy/action input is handled, not `unwrap()`-ed.
- **Coverage** — a high threshold for a small TCB (target ≥90% lines/branches on `verity-core`). Optional `cargo-mutants` on the core logic in a scheduled job (mutation score is the real signal for a verifier).

### 2.2 `verity-py` (PyO3 bindings)

- **Round-trip** — Python dict → `Action` → `VerdictReport` → Python; types survive both directions.
- **Parity** — the *same* scenario through the Rust API and the Python API yields the **identical** verdict. The binding is a thin shim and must change nothing semantic; this test is what lets us trust "one audited core, many bindings."
- **Wheel smoke** — `maturin` build + `import verity` + one `verify()` call, run in CI (Linux on PR; macOS/Windows × supported Python on merge).

### 2.3 Eval harness (Python)

- **Seed schema validation** — every corpus seed validates against `scenario.schema.json`. This is the **E0 gate** and runs in CI from day one.
- **Corpus integrity** — matched-pair completeness (every `failure` has a `benign_pair` that exists and is a `success`), id-convention conformance, taint integrity (`injection.carrier` ∈ `untrusted_inputs`; every `{taint:NAME}` marker declared), and `CORPUS.lock` content-hash match.
- **Oracle tests** (E2) — `action_predicate`/`effect`/`tool_name` scoring on known-good and known-bad trajectories; no LLM in the catastrophe decision (asserted by construction).
- **Matcher parity** — the harness's matcher semantics must agree with the Rust core's on a shared fixture set (`regex` = full search, `one_of` = membership, `gt|le` = i64-minor-unit compare). Divergence here silently corrupts grading.
- **Three-valued outcome** — `attempted_violation`/`safe`/`invalid` classification and the `ASR_valid` / `ASR_all` / `refusal_rate` computations on synthetic trajectories.
- **Adapter tests** (E3/E4) — small AgentDojo/InjecAgent/BIPIA fixtures → normalized schema; verify **oracle independence** (a harvested case's oracle never imports a verifier predicate, §7.2 firewall).

### 2.4 Encode-time compiler (Python) — deferred to its phase

When it exists: **compile-correctness** (intent → policy JSON the core accepts and that yields the intended verdicts on a battery), policy-schema round-trip, and evasion-catalog enumeration. Not built yet; no gate until it is.

## 3. The corpus as a regression gate (the standout idea)

The corpus is not just Phase 0 evidence — it becomes an **executable specification of the noise budget**:

- **Now (Phase 0):** CI validates seeds + integrity (§2.3). That's the gate while there's no verifier.
- **Phase 2 (verifier exists):** CI runs `verity-core` against the frozen corpus and **fails the build** on either:
  - **coverage regression** — recall on labeled violations drops below the per-class threshold, or
  - **noise-budget breach** — false-positive rate on the matched controls + benign pool exceeds budget.

This is the SELinux lesson made un-ignorable: the moment a change makes the floor noisy or leaky, the build goes red. The #1 product metric is a CI gate, not a good intention. (Thresholds are set from Baseline v1 — §9.)

## 4. Determinism vs. reproducibility — the split that matters

Two different standards, deliberately:

- **The library is deterministic and PR-gated.** `verity-core`'s replay test asserts byte-identity (§2.1). No exceptions.
- **The measurement is *not* byte-exact and is out-of-band.** Live small-model sweeps inherit vLLM batch-nondeterminism (eval-plan §11) — they are **not** PR-gated. PR CI tests the harness's *logic* on recorded transcripts/fixtures; the actual model sweeps run as a **scheduled** job with pinned manifests, and the determinism test there *quantifies drift within tolerance* rather than asserting equality.

Keeping these apart is the point: never let nondeterministic GPU runs gate a PR, and never let the deterministic core off the byte-exact hook.

## 5. The CI pipeline (polyglot monorepo)

GitHub Actions (origin is GitHub), **path-filtered** so a docs change doesn't run the Rust matrix.

- **PR gate — fast, required:**
  - *Rust:* `cargo fmt --check`, `clippy -D warnings`, `cargo test` (unit + floor acceptance + replay + property), `cargo-deny` (purity bans + license/advisory audit), coverage threshold.
  - *Python:* `ruff`, `mypy`/`pyright`, `pytest` (harness/oracle/adapters/matcher-parity on fixtures).
  - *Corpus:* seed schema validation + integrity + `CORPUS.lock` check.
  - *Bindings:* `maturin build` + import smoke (Linux).
- **Merge to `main` — broader:** multi-platform wheels (`manylinux` / macOS / Windows × supported Python), a short fuzz smoke run, artifact upload.
- **Scheduled (nightly/weekly):** long fuzzing, `cargo-mutants`, the **live model sweep** (Baseline refresh on pinned models), contamination checks. None PR-gated.
- **Release (tag):** build + publish wheels (PyPI) and the crate (crates.io); WASM/npm later; a changelog; and — fitting for a security tool — build **provenance/attestation** (SLSA / sigstore) so consumers can verify what they install.
- **Pinning:** `rust-toolchain.toml`, a pinned Python, committed `Cargo.lock`, and a Python lockfile (`uv`/`pip-tools`). Reproducible builds are part of the trust story.

## 6. What a green build guarantees — and what it doesn't

- **Green PR ⇒** the core is deterministic, pure (no clock/RNG/I/O), panic-free on fuzzed input, and passes floor-acceptance + property tests; the harness logic, oracle, and matcher are correct on fixtures; **every seed conforms**; and the bindings build and **agree** with the core.
- **Green does *not* mean** the live small-model baseline is current — that's the scheduled sweep — nor that the floor's real-world coverage/noise is within budget until the Phase-2 corpus gate (§3) is switched on. We state this boundary rather than let green imply more than it proves.

## 7. Tooling (leading choices)

- **Rust:** `cargo test`, `proptest`, `cargo-fuzz`, `cargo-deny`, `cargo-llvm-cov`, `cargo-mutants` (scheduled), `clippy`, `rustfmt`.
- **Python:** `pytest`, `ruff`, `mypy`/`pyright`, `check-jsonschema`/`jsonschema`, `maturin`.
- **CI:** GitHub Actions with path filters and a platform/Python matrix; committed golden `VerdictReport` fixtures for replay/regression.

## 8. When each gate turns on (mapped to existing milestones)

Don't add a red gate for a feature that doesn't exist yet.

| When | Gate switched on |
|---|---|
| **E0** (now) | Seed schema validation + corpus integrity |
| **kernel M1–M2** | Rust unit + `serde` round-trip + floor acceptance |
| **kernel M4** | Tri-state / `Indeterminate` tests |
| **kernel M7** | Determinism replay (byte-exact) — hard gate |
| **eval E2** | Oracle + matcher-parity tests |
| **eval E3/E4** | Adapter + oracle-independence tests |
| **bindings exist** | `verity-py` round-trip + parity + wheel smoke |
| **Phase 2** | Corpus coverage + **noise-budget** gates (§3) |

## 9. Open questions

1. **Thresholds** — coverage recall and noise-budget false-positive numbers (set from Baseline v1, not guessed now).
2. **Smoke-model in PR?** — keep *all* model runs out of PR CI, or allow one tiny CPU model as a cheap end-to-end smoke. (Lean: keep them out; fixtures suffice.)
3. **Mutation testing cadence** — `cargo-mutants` is the truest signal for a TCB but slow; scheduled-only vs. on-core-change.
4. **Release provenance** — SLSA level / sigstore signing worth the setup for a security tool? (Lean: yes, at first public release.)
5. **WASM/napi test matrix** — defer until the TS binding exists.
