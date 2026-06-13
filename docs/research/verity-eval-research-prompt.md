# Verity Eval Plan — Deep Research Prompt

*Input for a deep-research pass to de-risk `docs/product/verity-eval-plan.md`. The goal is to find what already exists so we **adopt rather than reinvent**, and to surface the considerations and pitfalls that experienced practitioners already know.*

---

## How to use this prompt

Feed it to a deep-research tool (or our own deep-research harness). It is **self-contained** — the essential plan context is inline — but if the runner has repo access, read `docs/product/verity-eval-plan.md` and `docs/product/verity-prd.md` for full detail.

## Who we are and what we're building

Verity is an open-source, deterministic, model-independent verification layer — a **reference monitor** for autonomous-agent tool calls. **Phase 0** (the subject of this research) builds an **evaluation corpus** that:

1. measures how often agents — especially small, locally-run **1–3B models** — take **catastrophic actions** (read secrets, run dangerous shell commands, exfiltrate data, self-modify), under prompt injection **and** plain hallucination on behalf of a *benign* user; and
2. later **grades the verifier** — coverage on the attacks, false positives on **matched benign controls**.

**We are practitioners building a tool, not researchers.** We do **not** want novel research or a literature review for its own sake. We want a **decision-useful map**: which existing datasets, benchmarks, harnesses, metrics, and methodologies we can **adopt or adapt**, and the **genuine gaps** we must build ourselves. *Every finding must resolve to "reuse this" or "build this, because nothing fits."*

## What we've already evaluated (go beyond these)

We have first-pass findings on three benchmarks and a serving stack. **Extend past them and challenge our reading; do not re-summarize them except to correct us:**

- **AgentDojo** (MIT) — planned spine (deterministic *effect*-based oracles; `{injection_*}` taint placeholders; loadable as data). Strong on exfiltration-on-a-tainted-path.
- **InjecAgent** (MIT) — planned breadth (1,054 indirect-injection cases; ReAct; tool-*name*-match oracle). Thin shell-exec, PII-adjacent.
- **AgentHarm** (MIT + use-restriction) — *pattern only* (matched benign pairs; per-behavior grading functions). Wrong threat model for us (deliberately malicious user).
- **Serving**: vLLM (+ llama.cpp/GBNF) for local small models; small-model tool-calling fails on *format* 30–80% of the time.

## Our key design choices — validate or challenge each

1. **Target small models (1–3B) first** as primary subjects; frontier model only as an accuracy anchor.
2. **Simulated, side-effect-free tools** for a reproducible, safe baseline (a real-execution tier is deferred).
3. **Deterministic, code-defined oracles** (effect / tool-name / action-predicate); **no LLM judge for the catastrophe verdict** (only, at most, for narrow benign-task-completion sub-checks).
4. **Matched benign controls** for every attack, to measure over-blocking (our #1 metric).
5. **Capability-vs-intent separation**: three-valued outcome (attempted-violation / safe / invalid); report attack-success-rate over *valid-only* and over *all*.
6. **Authored "catastrophe floor" classes** the benchmarks miss: secret-file reads, arbitrary shell/exec, self-modification/persistence.
7. **Minimal hand-written ReAct harness** whose tool-dispatch step is the future verifier chokepoint.
8. **Reproducibility**: pinned model revision/quant/seed, frozen + content-hashed corpus, per-run provenance manifests — while being honest that vLLM greedy decoding is not bit-exact.

For each: does established practice **support, contradict, or offer a better-trodden path**?

---

## Research questions (themed)

### A. Agent safety / security benchmarks & datasets (beyond our three)
Map the landscape of benchmarks that measure harmful or unsafe agent **actions** (not chat-level harmfulness). For each: scope, threat model (indirect injection / malicious-user / hallucination), action surface, oracle method, size, **license**, data format, model-agnostic?, last updated, and which of our catastrophe-floor classes it covers. Candidates to **verify and extend** (names may be imprecise — confirm or correct): ToolEmu, R-Judge, Agent Security Bench (ASB), SafeAgentBench, ToolSword, AgentPoison, AdvAgent, τ-bench (tau-bench), AgentBench, ST-WebAgentBench, WebArena / VisualWebArena, InjecGuard, BIPIA, AgentDojo forks. Which are reusable **as data** vs only conceptually?

### B. Catastrophe-class datasets for our authored floor
We must author secret-read, shell-exec, and self-mod cases. What existing corpora can **seed** them with crisp ground-truth labels?
- **Dangerous/benign shell commands**: NL2Bash, InterCode-Bash, command-injection corpora, the lexical-bypass material (line continuation / busybox multiplexing / GNU option abbreviation), **GTFOBins / LOLBAS** (living-off-the-land binaries).
- **Secret detection**: secret-scanning rulesets (gitleaks, trufflehog, detect-secrets) and any benchmark of secret/credential-file patterns we could reuse as `is_secret` ground truth.
- **Self-modification / persistence**: autostart / cron / skill- or MCP-config tampering corpora (likely sparse — confirm).
- **Exfiltration sinks**: existing taxonomies of agent exfiltration channels.
Where do reusable labels already exist, and under what license?

### C. Methodologies for measuring harmful agent actions
- How do existing works **detect** that a harmful action occurred — effect/state-diff checks, tool-call matching, LLM judges? What evidence exists on the **reliability** of each?
- Who uses **matched benign controls** / separates **refusal from incapability** (AgentHarm does)? Is there an established pattern we should follow?
- **Metrics**: standard definitions of attack-success-rate, the valid-vs-all normalization problem, refusal-rate, harm-score, and **partial-completion scoring** for multi-step (grab-then-exfiltrate) attacks. Known pitfalls and standard reporting.
- **LLM-as-judge reliability** for safety grading: when it's acceptable (narrow, well-specified sub-checks) vs unsafe (the overall harm verdict).

### D. Eval harnesses / frameworks
Which existing frameworks could run a reproducible agent-action corpus with minimal lock-in? Compare against our needs (local small models via vLLM/llama.cpp, a tool-use loop, custom **code** oracles, dataset versioning, run provenance, agent support): **Inspect** (UK AISI), **lm-evaluation-harness**, **OpenAI Evals**, **HELM**, **promptfoo**, **DeepEval**, **garak**, **Microsoft PyRIT**, AgentDojo's own runner, **smolagents**. For each: local-model support? agentic tool-use? custom code scoring? versioning/provenance? Verdict: **adopt one, or keep the hand-written loop** — and why.

### E. Small models in agentic / tool-use settings
- Evidence on how **1–3B** models fail at tool use and safety: function-calling reliability (BFCL and similar), injection susceptibility, over- vs under-refusal at small scale.
- Any agent/safety benchmark that specifically reports **small-model** results. Does prior art support our premise that **small models are the real and growing threat surface** as agents proliferate?

### F. Reproducibility & nondeterminism for LLM/agent evals
- Established practice for **model pinning, dataset versioning, and result provenance** (HELM, lm-eval-harness, Inspect conventions).
- **Nondeterminism**: inference-engine determinism (vLLM batch/floating-point effects), seed control, what reproducibility level is realistically claimable, and standard mitigations.
- **Data contamination / benchmark leakage**: risks and detection — relevant because we adapt public benchmarks and run open models that may have trained on them.

### G. Prompt-injection taxonomies & the lethal trifecta in evals
- Canonical taxonomies (direct vs indirect injection, OWASP LLM Top 10, the **lethal trifecta**, Meta's **Rule of Two**) and any eval that **operationalizes** them into reusable test cases.
- Indirect-injection datasets beyond InjecAgent (e.g., BIPIA) — formats, sizes, licenses.

### H. Honest gaps & contrarian evidence
- Where does prior art suggest our plan is **wrong or harder than we think**? (e.g., simulated tools missing real-execution failure modes; deterministic oracles missing semantic harm; small-model results not generalizing; matched controls being insufficient for FP estimation.)
- What genuinely does **not** exist, that we will have to build ourselves?

---

## Desired output (decision-useful, not a paper)

1. **Landscape map (table):** *artifact | type (benchmark / dataset / harness / method / paper) | what it covers | threat model | oracle method | size | license | format & access (repo / HF / pip) | which part of our plan it serves | **adopt / adapt / skip + one-line why***.
2. **Catastrophe-class source list** for the authored floor (§B) — concrete reusable datasets/rulesets with licenses.
3. **Best-practice considerations & pitfalls** (§C, §F) — each with a source and a one-line "what we should do."
4. **Genuine gaps** — what nothing covers, that we must author.
5. **Critique of our 8 design choices** — for each: *supported / contradicted / better path*, with evidence.
6. **Top recommendations** — the 5–10 concrete adoptions or changes that most de-risk the plan.

## Quality bar & cautions

- Cite **real, verifiable sources**: arXiv IDs, GitHub repos, dataset cards, leaderboards. Prefer **2023–2026**.
- **Flag the license** (can we redistribute / adapt?) for every dataset or benchmark.
- **Distinguish** well-established practice from emerging/uncertain claims; say where you could not verify.
- The candidate names above are **leads to confirm and extend**, not an authoritative list — correct our mistakes and add what we missed.
- Stay **practitioner-focused**: every item must map to **reuse-vs-build**. No novel research, no exhaustive literature review.
