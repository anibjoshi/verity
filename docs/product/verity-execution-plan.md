# Verity Execution Plan

*The master, step-by-step plan. It unifies the PRD roadmap (§12), the kernel-spec milestones (M0–M7), the eval-plan milestones (E0–E7), and the testing/CI gates into one sequenced execution with an objective **exit gate** on every step. Where the other docs say *what* and *why*, this says **in what order, how, and "done" means exactly what.***

---

## 0. How we execute (the working rhythm)

- **One step = one branch = one PR.** A step merges only when its **exit gate** is green — CI checks plus, where noted, a human review. No step is "done" by assertion.
- **Doc/format before code, within a step.** Where a step has a contract (a policy JSON, a schema), the data is hand-written and reviewed before the code that consumes it (the discipline that produced `floor.json` and `scenario.schema.json`).
- **Gates turn on as their target lands** (testing-ci §8). We never add a red gate for a feature that doesn't exist yet, and we never remove one once its feature does.
- **Two decision gates are real go/no-go forks**, not formalities: the end of Phase 0 (*is the problem real enough to justify the verifier?*) and the end of Phase 2 (*does the verifier deliver coverage within the noise budget?*). Honoring evidence-first and converge-don't-over-expand, either can send us back to narrow scope rather than forward.
- **Exit gates are objective wherever possible** (CI-enforceable), with a named human review only where judgment is irreducible (seed labels; the two decision gates).

**Dependency spine:** `G (groundwork) → Phase 0 (corpus / proof) → Phase 1 (verifier kernel) → Phase 2 (grade verifier) → Phase 3 (live harness) → Phase 4 (personalization, deferred)`. Phase 0 precedes Phase 1 deliberately (evidence-first); the Phase-0 harness is built to be the exact surface Phase 2 flips the verifier into.

---

## Phase G — Groundwork

### G1 — Repo scaffold + LICENSE
- **Goal:** the empty monorepo skeleton compiles and is correctly shaped.
- **Execute:** create the Cargo workspace and crates (`crates/verity-core`, `crates/verity-py`), `eval/` (Python pkg), `encode/` (stub), `policies/`, `docs/` (exists); add `rust-toolchain.toml`, `pyproject.toml`, committed `Cargo.lock` + Python lockfile, `.gitignore` (`target/`, `eval/results/`, `__pycache__/`), and the MIT `LICENSE` (done).
- **Deliverable:** the tree in PRD §8.5, building empty.
- **Exit gate:** `cargo build` succeeds on the empty workspace; the Python package imports; `LICENSE` present; tree matches PRD §8.5. (Reviewed.)

### G2 — CI bootstrap
- **Goal:** the PR gate exists and is green on a trivial change.
- **Execute:** GitHub Actions, path-filtered (testing-ci §5): Rust `fmt`/`clippy -D warnings`/`cargo test`; Python `ruff`/`mypy`/`pytest`; a corpus schema-validation job; matrix scaffolding for later. Only the gates whose targets exist are required.
- **Deliverable:** `.github/workflows/` PR pipeline.
- **Exit gate:** CI runs and is green on a no-op PR; path filters work (a docs-only change skips the Rust matrix); fmt/clippy/lint actually execute.

### G3 — Materialize E0 (= eval-plan E0)
- **Goal:** the scenario contract and seeds are live and machine-checked.
- **Execute:** extract `scenario.schema.json` and the 16 seeds from `verity-corpus-spec.md` into `eval/corpus/`; wire schema-validation + integrity checks (matched-pair completeness, id convention, taint-marker integrity) into the CI corpus job.
- **Deliverable:** `eval/corpus/schema/scenario.schema.json` + `eval/corpus/scenarios/**`.
- **Exit gate (eval-plan E0):** all 16 seeds validate against the schema **in CI**; integrity checks pass; seed set reviewed.

---

## Phase 0 — Evaluation corpus + prove the problem

*Builds the corpus, the harness, and produces **Baseline v1** — agent behavior without Verity. The harness's instrumented tool-dispatch is the chokepoint Phase 2 flips the verifier into.*

### 0.1 — Minimal harness, one model (eval-plan E1)
- **Goal:** an end-to-end vertical slice — one small model runs the seeds and we capture the three-valued outcome.
- **Execute:** `harness/loop.py` (ReAct loop, step cap), `tools.py` (simulated side-effect-free tool registry + the instrumented dispatch chokepoint), `serving.py` (vLLM client), `decode.py` (guided decoding + dual `tool_calls`/content-JSON parser); run the E0 seeds on Qwen2.5-3B.
- **Exit gate (E1):** runs all E0 seeds; emits `attempted_violation|safe|invalid` per scenario; re-run reproduces outcomes within tolerance; harness logic unit-tested (testing-ci §2.3).

### 0.2 — Deterministic oracle/verdict layer (eval-plan E2)
- **Goal:** scoring by code only, all three oracle styles.
- **Execute:** `oracle/verdict.py` (`action_predicate` + `effect` state-diff template + `tool_name`); implement the matcher (`equals`/`regex`/`one_of`/`gt|ge|lt|le`) to agree byte-for-byte with the future Rust matcher.
- **Exit gate (E2):** known-good/known-bad trajectories score correctly; matcher-parity fixtures pass; **no LLM in the catastrophe decision** (asserted structurally); unit tests green.

### 0.3 — AgentDojo adapter (eval-plan E3)
- **Goal:** the spine loads, both halves.
- **Execute:** `adapters/agentdojo_adapter.py` via `get_suites()`; injection tasks → `failure` (reuse `security()` as the effect oracle), `user_tasks` → `success` (reuse `utility()`).
- **Exit gate (E3):** N AgentDojo cases load + score, both halves; oracle-independence check passes (no verifier predicate imported).

### 0.4 — InjecAgent + BIPIA adapters (eval-plan E4)
- **Goal:** breadth, with controls.
- **Execute:** `adapters/injecagent_adapter.py` (DH + two-stage DS) and `adapters/bipia_adapter.py` (incl. BIPIA-Clean as controls); upgrade harvested oracles past tool-name where feasible.
- **Exit gate (E4):** cases load + score; `ASR_valid`/`ASR_all`/`refusal_rate` computed; DS two-stage handled.

### 0.5 — Author the floor + controls + benign pool (eval-plan E5)
- **Goal:** the system/code-access floor and the novel slice, at scale.
- **Execute:** scale the E0 seeds to target counts per class; seed from NL2Bash / corrected InterCode (shell), gitleaks ruleset (secret), GTFOBins/LOLBAS (persistence/LOTL); **author the benign-user-hallucination cases**; expand the benign trigger-word pool. Vendor/pin seed corpora with verified licenses.
- **Exit gate (E5):** each class has ≥k attacks + matched controls; benign pool present; labels reviewed against the written rubric; everything validates; **seed-corpus licenses verified** (no AGPL/NC vendored). (Reviewed.)

### 0.6 — Model sweep (eval-plan E6)
- **Goal:** the full matrix under full provenance.
- **Execute:** `runner/sweep.py` over the small set + frontier anchor; `runner/manifest.py` stamps every result row (model+revision+quant+template, engine+version, seed, decode config, `corpus_version`, harness SHA). Needs GPU/serving infra (out-of-band, not PR CI).
- **Exit gate (E6):** full matrix runs; every result row carries a complete manifest.

### 0.7 — Baseline v1 + freeze (eval-plan E7) — **PHASE 0 EXIT**
- **Goal:** the proof, frozen and reproducible.
- **Execute:** `metrics/report.py` emits the Baseline v1 table; `determinism.py` re-run test; freeze `CORPUS.lock` (content hashes).
- **Exit gate (E7):** Baseline v1 published — `ASR_valid`/`ASR_all`/`refusal_rate` per class per model, `task_success_rate`, `over_caution_rate`, small-vs-frontier gap, `invalid_rate`; determinism test reproduces within tolerance; corpus frozen + hashed.
- **🚦 Decision gate (go/no-go):** *Do small-model agents take catastrophic floor actions at a rate that justifies a deterministic verifier, with frontier models visibly resisting?* If yes → Phase 1. If the floor is rare or noisy even without a verifier → narrow scope before building it.

---

## Phase 1 — `verity-core` verifier kernel

*The deterministic library, validated standalone against `StaticContext` and the corpus — not yet a live harness (that's Phase 3). Maps to kernel-spec M0–M5 + M7; M6 (live OpenClaw) is deferred to Phase 3.*

### 1.0 — `floor.json` (kernel-spec M0)
- **Goal:** the compiled-policy form, hand-written, informed by the corpus.
- **Execute:** author `policies/floor.json` (effect floor + provenance envelope); align its named predicates and `floor_predicate` labels with the corpus seeds (§ corpus-spec §5).
- **Exit gate (M0):** reads cleanly; reviewed; round-trips once M1 lands.

### 1.1 — Data model + serde (kernel-spec M1)
- **Exit gate (M1):** `floor.json` round-trips through the Rust types.

### 1.2 — Expr eval + predicates, two-valued (kernel-spec M2)
- **Exit gate (M2):** `fs.read` on a secret path → `Violate` (kernel-spec §2.1).

### 1.3 — StaticContext + provenance envelope (kernel-spec M3)
- **Exit gate (M3):** tainted external send over static context → `Violate` (kernel-spec §2.2 case 1).

### 1.4 — Tri-state + `Indeterminate` (kernel-spec M4)
- **Exit gate (M4):** missing `taint.body` → `Indeterminate`, **not** a silent conform (kernel-spec §2.2 case 2).

### 1.5 — VerdictReport + disposition + assurance (kernel-spec M5)
- **Exit gate (M5):** the §2 verdicts render with quoted rationale, disposition, and an assurance record.

### 1.6 — Determinism + hardening (kernel-spec M7 + testing-ci §2.1)
- **Goal:** the guarantees, enforced.
- **Execute:** replay test; `proptest` invariants; `cargo-fuzz` targets on the deserializer + evaluator; purity bans (`cargo-deny` + grep backstop); coverage threshold.
- **Exit gate (M7):** replay is **byte-identical**; purity enforced (no clock/RNG/I/O reachable in `verity-core`); fuzz targets are no-panic; coverage ≥ threshold.

### 1.7 — PyO3 bindings + wheel (testing-ci §2.2)
- **Goal:** the core is consumable where agents live, with identical semantics.
- **Execute:** `crates/verity-py` (PyO3); `maturin` wheel; parity tests.
- **Exit gate:** wheel builds and imports; **Rust API and Python API give the identical verdict** on a shared fixture set; `pip install` + a `verify()` call works.

**🏁 PHASE 1 EXIT:** all kernel-spec acceptance tests pass; determinism byte-exact; purity enforced; fuzz no-panic; bindings at parity. The library does the core thing — standalone.

---

## Phase 2 — Grade the verifier against the corpus

*Flip the verifier ON in the Phase-0 harness and measure it against the frozen Baseline v1 corpus. The payoff of evidence-first: the same instrument that proved the problem now scores the cure.*

### 2.1 — Wire `verify()` into the chokepoint
- **Goal:** verifier ON, verdicts recorded.
- **Execute:** at the harness dispatch chokepoint (built in 0.1), normalize the resolved tool call → `Action`, call `verify()` (via the PyO3 wheel), record the verdict alongside the agent's action. One switch: OFF = Baseline, ON = graded.
- **Exit gate:** the harness runs verifier-ON over the corpus; each scenario carries `{agent_action, verdict, assurance}`.

### 2.2 — Coverage + noise-budget grading — **PHASE 2 EXIT**
- **Goal:** the two numbers that decide whether Verity works.
- **Execute:** compute **coverage** (recall on labeled violations, per class) and the **noise budget** (false-positive rate on matched controls + benign pool); compare verifier-ON vs Baseline (catastrophe-execution down, `task_success` held). Switch on the corpus CI gates (testing-ci §3).
- **Exit gate:** on Baseline v1's corpus, coverage ≥ per-class threshold **and** FP on controls ≤ budget **and** `task_success` not materially degraded; coverage + noise-budget gates now red-on-regression in CI.
- **🚦 Decision gate (go/no-go):** *Does the floor catch the catastrophes within the noise budget?* If coverage is high but noisy → narrow the floor (the SELinux lesson) before any integration. If clean → Phase 3.

---

## Phase 3 — Live harness integration (kernel-spec M6)

*From StaticContext to a real, autonomous harness. This is where the demonstration lives.*

### 3.1 — OpenClaw adapter over `before_tool_call`
- **Goal:** the verifier runs at a real chokepoint, atomically.
- **Execute:** the adapter (PRD §6.3 / kernel-spec §7) — intercept the resolved tool call, normalize → `Action` (the safety-critical mapping; e.g. `sessions_spawn` → `process.spawn`), gather context, map verdict→disposition onto block/allow, **fail closed** when the hook can't express the intent; the assurance record states what the hook actually provided (atomic, provenance-blind).
- **Exit gate (M6):** both kernel-spec §2 proofs pass on a **live OpenClaw tool call**; verdict maps to block/allow with fail-closed collapse; assurance reflects atomic-but-provenance-blind.

### 3.2 — Provenance plumbing (upstream contribution)
- **Goal:** unlock the trifecta floor on a real harness.
- **Execute:** thread OpenClaw's existing message-level provenance through to `before_tool_call` so tool-param taint is available (PRD §11 OQ7); open the upstream PR.
- **Exit gate:** a provenance-dependent floor policy returns `Violate` (not `Indeterminate`) on a live tainted path; upstream PR opened.

**🏁 PHASE 3 EXIT (the demonstration, PRD §12):** an autonomous small-model agent in OpenClaw, prompt-injected or hallucinating, proposes a catastrophic action; Verity returns `Violate` with a human-readable reason and pathway **before execution**, and the agent self-corrects from the explanation — something a model-based guard cannot do reliably, because the same injection that fooled the agent fools the guard.

---

## Phase 4 — Learned personalization (deferred; design open)

Held per PRD §10 / OQ. Not planned in detail here: it gets its own design doc (cold-start, how few corrections suffice, keeping learned boundaries deterministic and inspectable, the learned-vs-inference line) before any execution. The floor must be proven low-noise (Phase 2) first — personalization rides on top of a quiet floor, never rescues a noisy one.

---

## Exit-gate summary

| Step | Exit gate (one line) |
|---|---|
| G1 | empty workspace builds; tree per PRD §8.5; LICENSE present |
| G2 | CI green on a no-op PR; path filters work |
| G3 / E0 | 16 seeds validate + integrity pass in CI; reviewed |
| 0.1 / E1 | seeds run on one model; 3-valued outcome; reproducible |
| 0.2 / E2 | code-only oracle correct; matcher parity; no LLM in verdict |
| 0.3 / E3 | AgentDojo loads + scores, both halves |
| 0.4 / E4 | InjecAgent + BIPIA load; ASR valid/all/refusal computed |
| 0.5 / E5 | floor + controls + pool + hallucination cases; labels + licenses reviewed |
| 0.6 / E6 | full matrix runs under complete manifests |
| 0.7 / E7 | **Baseline v1 published + frozen** → 🚦 *problem real?* |
| 1.0–1.5 | kernel-spec M0–M5 acceptance tests pass |
| 1.6 / M7 | determinism byte-exact; purity enforced; fuzz no-panic |
| 1.7 | bindings parity; wheel installs |
| 2.1 | verifier ON; verdicts recorded |
| 2.2 | **coverage ≥ threshold + FP ≤ budget** → 🚦 *verifier works?* |
| 3.1 / M6 | both proofs on a live OpenClaw call; fail-closed |
| 3.2 | trifecta floor returns Violate on a live tainted path; upstream PR |
| 3 exit | the demonstration: catastrophic action blocked pre-execution, agent self-corrects |

---

## What this plan commits to — and what it doesn't

- It commits to **proving the problem before building the cure**, to an **objective gate on every step**, and to **two honest go/no-go forks** that can stop or narrow the work.
- It does **not** commit to thresholds (coverage recall, noise budget) — those are read off Baseline v1, not guessed now (testing-ci §9) — nor to Phase 4, which is deferred until the floor is proven quiet.
