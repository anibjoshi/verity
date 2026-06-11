# Symbolica Distribution Strategy

Companion to the PRD (`Symbolica-new.md`). The PRD defines what Symbolica is; this document defines how it gets into existing agentic products. For a control layer, distribution is the product decision: a policy engine nobody wires in is shelfware.

## 1. The Lesson From Prior Policy Engines

OPA won Kubernetes because admission controllers gave it a free chokepoint — every cluster change already flowed through a narrow waist OPA could attach to. OPA never won application authorization, because every application required custom integration work.

The governing question for Symbolica is therefore:

**Where do agent actions already flow through a narrow waist that Symbolica can attach to without anyone restructuring their agent?**

There are two such narrow waists in 2026 agent stacks:

1. **The tool abstraction.** Every framework — LangGraph, OpenAI Agents SDK, CrewAI, Pydantic AI, custom loops — converges on the same shape: tools are a list of callables/schemas handed to a loop.
2. **MCP.** The cross-vendor protocol through which agents reach tools, supported by every major host (Claude Desktop, Claude Code, Cursor, custom runtimes).

Symbolica's insertion strategy targets both, with one policy format across them.

## 2. Insertion Surfaces

| Surface | Insertion cost | Enforcement strength | Who it reaches |
|---|---|---|---|
| SDK tool wrapper | One line of code | Advisory (developer must wrap) | Any Python/TS agent |
| Framework hooks (LangGraph, OpenAI Agents SDK, Claude Code hooks) | A few lines, per framework | Advisory-plus | That framework's users |
| MCP gateway/proxy | Config change, zero code | Strong chokepoint | Every MCP host |
| REST sidecar | Infra deployment | Strong if network-enforced | Polyglot / enterprise |
| CI / offline trace testing | A GitHub Action | None (pre-deployment) | Teams with recorded traces |

Strategic read (revised per the GTM research, June 2026): **lead with the MCP gateway in shadow mode; the SDK wrapper is the secondary on-ramp.** The OPA lesson is decisive — products that own a chokepoint (Kubernetes admission control) compound; products that ask developers to call `verify()` at every site (application authorization) stall for a decade. The gateway is Symbolica's potential chokepoint. Running it in *shadow mode* resolves the tension with the Snyk/LaunchDarkly lesson (developers resent what blocks them): a shadow gateway is the chokepoint *and* friction-free observability of every agent action — wanted, not resented — and it earns the right to enforce later.

Two caveats that keep this honest:
* The MCP gateway is a **manufactured** chokepoint, not an inherited one. Unlike the K8s admission webhook, it is bypassable — an agent can call tools directly. Symbolica must engineer the gateway into the path of least resistance; the OPA analogy transfers only if it does.
* Both surfaces still ship in the MVP, share one policy format, and graduation is a config migration — never a rewrite. The SDK remains the fast trial for teams not yet behind a gateway.

## 3. Primary Insertion Artifact 1: SDK Tool Wrapper

The five-minute path. Operates below the framework, at the universal tool-callable layer:

```python
import symbolica

guard = symbolica.Guard("policies/")          # or a starter pack
tools = guard.wrap(tools, actor="agent-support-17")
# hand wrapped tools to LangGraph / OpenAI Agents SDK / CrewAI as before
```

Behavior:

* Calls `verify()` on each tool call and returns a verdict; the developer's `if`-body decides what happens (pass through, raise, escalate, let the agent self-correct, or — in shadow — log only). Symbolica verifies; it does not enforce (PRD §9.12).
* Requires no agent restructuring and no framework buy-in.
* Threads actor/session context explicitly (`actor=`), which stateful cross-call policies require.

Framework-specific adapters (`SymbolicaMiddleware` for LangGraph, a guardrail for the OpenAI Agents SDK, a PreToolUse hook for Claude Code) are thin veneers over this same core. Frameworks are numerous and churn quarterly; Symbolica maintains veneers, not engines.

Limitation to be honest about: the wrapper is advisory. A developer must remember to wrap, and a bypassed wrapper enforces nothing. It is the trial surface, not the security story.

## 4. Primary Insertion Artifact 2: MCP Gateway

The production path, and where the real bet is placed.

* **Insertion is a config edit, not a code change.** The user points their MCP client config at `symbolica-gateway`, which proxies the real tool servers behind policy. Teams whose tools already speak MCP adopt Symbolica without touching agent code.
* **It is the only true enforcement chokepoint.** The agent cannot reach the tools except through policy. This is what the security/compliance buyer requires — a control they can attest to, not a library developers are trusted to call.
* **Distribution compounds.** Every MCP host becomes addressable with zero per-framework work, and MCP registries/directories are a free discovery channel.
* **Structural data advantage.** The gateway sees connection-level identity and the full action stream — exactly the session context that stateful cross-call policies (cumulative thresholds, per-incident tracking) need. The wrapper has to ask for this context; the gateway gets it for free. Connection-level identity is also the cheapest source of a *verified* aggregation key (PRD §9.10): the actor is authenticated by the connection, not claimed in the payload.
* **Two honesty boundaries.** The gateway sees only its own stream, so the enforced property is "≤ threshold *via this chokepoint*," not a business-wide invariant (PRD §9.11) — widening it needs state adapters into systems of record. And payload-supplied grouping keys remain agent-claimed even at the gateway; only connection/session-derived keys are verified. Both scopes must be stated to the buyer, not glossed.
* **Single static binary.** The gateway is a Rust binary embedding StrataDB for its own state (cumulative counters, session state, append-only decision ledger, versioned policies). No Python runtime, no external database — `brew install` / `curl | sh` / a small container image. This reuses Strata's existing distribution pipeline (cargo, Homebrew, prebuilt binaries).

## 5. Adoption Mechanics

Two mechanics matter more than any individual surface.

### 5.1 Shadow Mode Is the Default

Nobody enables blocking on day one — not for feature flags, not for WAFs, not for admission controllers. The first-run experience must be: install, wrap (or repoint config), **nothing breaks**, and the team sees a ledger of everything the agent did plus what *would have been* blocked under the active policies.

Enforcement is a flag flipped after a week of confidence, per policy or per surface. This single decision is expected to be the largest driver of trial-to-production conversion.

### 5.2 Value Before Authoring

Day-one value must not require writing policies (modeling cost is the PRD's top-ranked risk). Three mitigations, in order of leverage:

1. **The action ledger is the hook.** Even with zero policies, a wrapped agent produces a structured ledger — who did what, with what arguments, in what sequence. Symbolica is useful as an agent action flight recorder before it is a policy engine.
2. **Starter packs.** `symbolica init --pack refunds` (or `database-ops`, `infra`, `pii`) ships working policies for the MVP domains. Templates convert "learn a DSL" into "edit a threshold."
3. **Learn mode.** `symbolica suggest-policies` drafts a baseline from observed behavior — "this agent has never called `delete_table`; deny it," "refunds observed up to $4,200; flag above $5,000." Firewall-learning-mode pattern. This is the priority use of the LLM assistant in the MVP, ahead of freeform natural-language authoring.

## 6. The Observability Data Path (OTel / Langfuse)

Decision: observability integration is built on **OpenTelemetry GenAI semantic conventions**, with **Langfuse as the first concrete connector**. Langfuse, LangSmith, Phoenix/Arize, Braintrust, and Datadog LLM observability have converged on OTel conventions — building at the OTel seam makes Langfuse the first connector rather than a dependency, with the others reachable nearly for free.

Critical framing: observability tools are post-hoc — by the time a span lands in Langfuse, the refund has been issued. Therefore:

**Observability is the data path. Enforcement is the wrapper/gateway path. They are never conflated.**

The data path provides three capabilities:

### 6.1 Retroactive Cold-Start Kill (Learn Mode via Import)

Teams already running Langfuse have months of agent action history — every tool call with arguments, actors, sequences. `symbolica import --from langfuse` reads that history and drafts baseline policies immediately. The onboarding pitch becomes: *"Connect your Langfuse project, get a draft policy pack from your agent's actual behavior in five minutes"* — value before writing a single policy or even deploying the wrapper.

### 6.2 Policy Backtesting

Before enforcing, replay historical traces through a proposed policy: "This policy would have blocked 3 of last month's 12,000 actions — here they are." False positives are what make teams afraid to flip from shadow to enforce; backtesting turns that moment into a data-backed decision. It also gives learn mode something concrete to validate its drafts against.

### 6.3 Decision Write-Back Instead of Dashboards

Symbolica decision traces (rules evaluated, approvals required, counterexamples) are emitted as OTel spans attached to the team's existing execution traces — policy decisions appear in the observability pane teams already live in. This is also scope discipline: the OSS product defers dashboard-building because early adopters' dashboards already exist. Symbolica stays the decisioning brain; rendering is a solved problem elsewhere.

### 6.4 Two Trace Types, Linked but Distinct

* **Execution trace** — what happened. Owned by the observability tool.
* **Decision trace** — why it was allowed/blocked/escalated. Owned by Symbolica; this is the audit and compliance export.

The integration links them (decision span as child of the tool-call span); it never merges them.

### 6.5 Targeting Benefit

Teams running Langfuse are precisely the ICP: serious enough about agents to instrument them, with agents already in production taking real actions. The Langfuse integrations directory is a free discovery channel aimed at exactly that audience.

## 7. Graduation Path by Persona

| Stage | Persona | Surface | Mode |
|---|---|---|---|
| Trial | AI application developer | SDK wrapper (or Langfuse import, no deployment at all) | Shadow |
| Team adoption | Developer + platform engineer | MCP gateway | Shadow → enforce per policy |
| Production governance | Platform engineer | MCP gateway + sidecar | Enforce |
| Enterprise | Security/compliance | Managed control plane over gateways | Enforce + audit exports |

Each step is a config migration over the same policy format. The product must feel like one system that tightens as it is promoted — never two products with two mental models.

## 8. Channels

* MCP registries and directories (gateway listing)
* Langfuse integrations directory (connector listing)
* Framework integration pages (LangGraph, OpenAI Agents SDK) via the thin adapters
* GitHub: starter packs and example repos per MVP domain
* The "Before Agents Act" demo (PRD §31) as the launch narrative, extended with the Langfuse-import onboarding ("draft policies from your real traffic in five minutes")

## 9. Implications for MVP Scope

* The MVP centers **two insertion artifacts** — `guard.wrap()` and `symbolica gateway` — both defaulting to shadow mode, sharing one policy format. The CLI and DSL are supporting tooling, not the lead.
* Starter packs and the action ledger are must-haves; they carry the first-session experience.
* The OTel emitter + Langfuse connector (import, backtest, write-back) are the highest-leverage should-haves.
* The REST sidecar and managed registry come later; they serve the platform-engineer persona who arrives after developers have proven value.
* The basic trace UI is deferred wherever decision spans can render in existing observability tools.

## 10. Risks

* **Advisory-surface complacency.** Teams may stop at the wrapper and never reach the chokepoint. Mitigation: position the wrapper explicitly as the trial surface; make gateway migration trivially cheap; have shadow-mode reporting highlight "unenforced" status.
* **MCP coverage gaps.** Not all tools speak MCP. Mitigation: the wrapper covers in-process tools; the sidecar covers everything else later.
* **OTel convention drift.** GenAI semantic conventions are still maturing. Mitigation: keep the connector seam thin; treat Langfuse's concrete API as the contract until conventions stabilize.
* **Identity threading.** Stateful policies need actor/session identity, which the wrapper must ask developers to provide. Mitigation: make `actor=` required in `wrap()`, infer session where possible, and lean on the gateway where identity is structural.

## 11. Open Questions

1. ~~Gateway deployment shape: single binary, container, or both at launch?~~ Resolved (June 2026): single static Rust binary, with a thin container image wrapping the same binary. Reuses Strata's release pipeline.
2. Does the gateway support streaming/long-running MCP tool calls in v1, or defer?
3. The approval *mechanism* at the gateway (block-and-poll, webhook, HITL MCP response) — deferrable. But the approval *experience* (who is pinged, how the agent blocks/resumes, how approval feeds back to commit) is **MVP-scope**, not deferrable: most decisions resolve to `require_approval`, and a blocked action with no approval path is operationally an error — a first-week trial-killer even under shadow-first. See PRD §26.1 #11.
4. Should learn mode run locally against exported traces only, or call the Langfuse API directly in MVP?
5. Minimum viable identity model for `actor`/session in the wrapper before the gateway exists?
