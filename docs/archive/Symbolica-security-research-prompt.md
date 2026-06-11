# Deep Research Prompt: Agent-Action Verification — Threat Landscape, Defense Insufficiency, and Systems-Security Precedent

## Context

I am building **Symbolica**, a deterministic verification layer for autonomous AI agents, built *into* an open agent harness (OpenClaw or Hermes). It sits at the tool-execution step — between an agent deciding to act and the action firing — and answers one question: *is this action allowed, for this user, in this context?* It returns a verdict the runtime acts on. The verifier is **symbolic and model-independent** (so it cannot be jailbroken along with the agent), evaluated at runtime with no LLM in the path; an LLM + SMT solver compile policy from intent at authoring time only.

**Demand is already validated against primary sources.** The OpenClaw vulnerability taxonomy (arXiv 2603.27517, 470 advisories) names the core weakness as *"per-layer trust enforcement rather than unified policy boundaries."* Hermes's security audit (issue #7826) found 4 Critical / 9 High issues with a default ALLOW-ALL posture (unrestricted shell; reads `/etc/passwd`, SSH keys, `.env`; persistent skill injection; **"LLM auto-approval systems" and "regex-only threat detection" flagged as weaknesses**). OpenClaw's allowlist is bypassable via lexical reformulation (line continuation, busybox multiplexing, GNU option abbreviation). The leading defense tools occupy a *naive tier*: input-side delimiters (OpenClaw #62939, which explicitly does **not** verify tool calls), detection-only suites (clawsec, which defers pre-execution action verification "to platform builders"), and coarse sandboxing. Deterministic pre-execution per-action verification is the uncontested gap.

**What this research is for.** Two thrusts:
1. **Deepen the documented present** — the full agent-harness threat taxonomy and a rigorous account of *why every current defense class is insufficient*, so Symbolica's catastrophe floor and use-case priority are evidence-driven, not assumed.
2. **Learn from the past** — agent-action verification is, structurally, *mandatory access control / capability security for agent actions*: a powerful, untrusted, manipulable executor constrained by a deterministic policy boundary. Computer security has spent **decades** on exactly this shape. Its hard-won lessons — especially the **policy-authoring usability problem** that got SELinux disabled across the industry — speak directly to Symbolica's hardest open question (how to get precise per-user policy from people who won't author it).

**We are NOT asking what to build.** The thesis is set. We need rigorous, cited grounding and transferable lessons — including the cautionary ones.

---

## Decisions This Research Must Inform

1. **Catastrophe floor** — the defensible universal set of actions a deterministic layer should gate by default, derived from documented incidents and security precedent, not intuition.
2. **Use-case priority** — confirm/refine that system/code-access actions (shell, secret-file reads, self-modification/skill-injection, RCE paths) are the lead, vs. consumer-lifestyle actions.
3. **Interception architecture** — where in the agent loop verification belongs: input-side (data/instruction separation), action-side (pre-execution tool-call verification), or both; and how this maps to LSM/seccomp/reference-monitor placement.
4. **Authoring/personalization model** — what the history of security-policy authoring (SELinux, AppArmor, capabilities) says about getting usable per-context policy from non-experts, and which mechanisms (learning mode, profile generation, sensible defaults) actually worked.
5. **Differentiation/positioning** — Symbolica's precise lane vs. input-delimiting, detection-only, sandboxing, and model-based guards, stated in terms a security audience respects.
6. **Lab relevance** — how the thesis maps to what frontier labs publish on agent/computer-use/tool-use safety, so the work speaks to their open problems.

---

## Research Questions

For each: study the named subjects concretely, extract the **causal mechanism**, surface **anti-patterns and failures**, and end with **"what this means for Symbolica"** — explicitly flagging where the analog **breaks** so a lesson doesn't falsely transfer.

### 1. The agent-harness threat taxonomy (the documented present)

Study the OpenClaw vulnerability taxonomy (arXiv 2603.27517), the Hermes security audit (NousResearch/hermes-agent #7826 and related), OWASP's LLM Top 10 and any OWASP Agentic-AI threat work, and incident reports across other harnesses (OpenHands/OpenDevin, Goose, AutoGPT-style, computer-use agents).

- What are the empirically dominant attack classes (prompt injection, exec/allowlist bypass, data exfiltration, privilege escalation, supply-chain/skill injection, RCE, cross-layer composition)? Rank by documented frequency and severity.
- Which actions show up repeatedly as the *dangerous* ones — the raw material for a catastrophe floor?
- Where do incidents cluster: system/code-access vs. consumer-lifestyle (smart home, payments, messaging)?

### 2. Why every current defense class is insufficient

Study, with their documented failure modes: structural delimiters / spotlighting (OpenClaw #62939), detection-only suites (clawsec), sandboxing (gVisor, containers, OpenClaw `workspaceOnly`), approval gates and blocklists (Hermes `tools/approval.py`), regex/lexical allowlists, and LLM-as-judge / model-based approval.

- For each: what does it catch, what does it miss, and what's the *documented* bypass? (e.g., lexical allowlist evasion; the 50–84% prompt-injection success rate cited for training-based defenses; LLM auto-approval flagged as a vulnerability.)
- Why is *detection* (after the fact) structurally weaker than *pre-execution verification* for irreversible actions?
- Why does input-side defense (separating data from instructions) not remove the need for action-side verification?

### 3. Systems-security precedent — deterministic policy boundaries for powerful untrusted execution (the goldmine)

Study, as direct structural analogs: **seccomp / seccomp-bpf** (syscall filtering), **SELinux** and **AppArmor** (mandatory access control), **capability-based security** (Capsicum, the object-capability model, EROS/seL4), the **Linux Security Module (LSM)** framework and the reference-monitor concept, **browser sandboxing** (Chrome site isolation), **eBPF runtime security** (Falco, Cilium Tetragon), and **container isolation** (gVisor, Firecracker).

- For each: what is the policy model, where is the enforcement point (the reference monitor), and how is least privilege expressed?
- What made each adoptable or not? Which became invisible infrastructure (seccomp in every browser/container) and which stayed marginal?
- **What transfers to agent action verification, and — critically — where does the analogy break?** (Agents act in an open natural-language/tool space, not a closed syscall set; the "action surface" is unbounded and semantic in a way syscalls are not. Name this disanalogy precisely.)

### 4. The policy-authoring usability problem (the cautionary core)

This is the most important question for Symbolica's hardest open problem. Study **SELinux's authoring crisis** (the `setenforce 0` phenomenon — policy so hard to write that operators disable enforcement), **AppArmor's profile learning mode** (learn-from-observed-behavior), **Falco/OPA rule authoring**, capability-system adoption friction, and any work on **auto-generating least-privilege policy** from observed behavior.

- Why did fine-grained MAC fail to get authored correctly in practice, and get turned off? What is the precise usability failure?
- What mechanisms made policy authoring tractable: learning/permissive modes, profile generation, sane defaults, audit-to-policy pipelines?
- **For Symbolica:** this *is* the personalization problem (precise per-user policy from people who won't author one). What does this history say about catastrophe-floor-plus-learned-from-corrections vs. asking users to specify? What's the analog of `setenforce 0` that Symbolica must avoid (the failure where verification gets disabled because it's too noisy/strict)?

### 5. Deterministic & formal verification that succeeded in production security

Study **seL4** (formally verified microkernel), **AWS automated reasoning** (Zelkova → IAM Access Analyzer; Bedrock Automated Reasoning Checks), **smart-contract verification** (Certora, formal EVM verification), **control-flow integrity (CFI)**, and **information-flow control (IFC)** systems.

- Where did deterministic/formal verification reach production and real adoption, and what made it adoptable (invisible to users, asking the question on their behalf, bounded scope)?
- What kept others academic? Recurring reason?
- **For Symbolica:** the productization pattern (keep the solver invisible; surface only the verdict) and the scope discipline (verify what's bounded and crisp, escalate the rest).

### 6. Prompt-injection & tool-use safety research (academic + practitioner)

Study the research and practitioner literature: indirect prompt injection (Greshake et al.), Simon Willison's prompt-injection writing and the **dual-LLM / privileged-vs-quarantined** pattern, Google's **CaMeL** and **spotlighting**, **AI control** work (Redwood Research), and studies on **LLM-as-judge reliability** and jailbreak robustness.

- What does the evidence say actually constrains agent actions vs. what only reduces deception probability?
- What is the documented reliability ceiling of model-based guards, and why does that imply a deterministic outer boundary?
- **For Symbolica:** which research patterns Symbolica complements (e.g., it is the deterministic enforcement layer the "privileged LLM" pattern assumes exists) and which it competes with.

### 7. Frontier-lab agent-safety priorities (lab relevance)

Study what **Anthropic** (Claude computer use; agentic safety; responsible-scaling/ASL framing as it touches autonomous action), **OpenAI** (Operator/agents; tool-use and computer-use safety), and **Google DeepMind** publish on agent action safety, computer-use guardrails, and tool-use verification.

- What open problems do they explicitly name around autonomous agents taking real actions safely?
- Where does a deterministic, model-independent, per-context action-verification layer fit their stated roadmaps and gaps?
- **For Symbolica:** the framing and vocabulary that maps the thesis onto their open problems (this is the lens that makes the work legible to that audience).

### 8. The discriminating boundary — deterministic vs. model judgment

Synthesize from 1–7: a rigorous, evidence-grounded account of **where deterministic verification is necessary** (adversarial robustness, crisp boundaries, irreversibility) **vs. where model/LLM judgment is appropriate** (subjective, reversible, non-adversarial). Symbolica must claim the former and explicitly cede the latter; the credibility is in the honesty of the line.

### 9. Failure modes & disconfirming evidence (mandatory)

Hunt for where deterministic policy layers **failed, were bypassed, or were abandoned**: SELinux disabled in practice; sandbox escapes; allowlist/seccomp-filter bypasses; capability-system adoption failures; reference-monitor gaps (TOCTOU, confused-deputy). For each, the precise mechanism — and whether Symbolica is exposed to the same one (especially: the confused-deputy problem, where the agent is tricked into using its legitimate privileges; and the authoring-noise → disablement failure).

---

## Output & Synthesis Requirements

- **Cited**, primary sources preferred: security advisories and CVEs, the vulnerability paper, harness source/issues, the seminal systems-security papers (the SELinux, Capsicum, seccomp, seL4, CaMeL, indirect-injection papers), and lab publications.
- **Mechanism, not lore** — name the specific causal mechanism for each success and failure.
- **Transfer honesty (adversarial)** — for every lesson cited for Symbolica, state where the analogy *breaks*. The biggest one to interrogate: syscalls are a closed, finite, semantically-stable set; agent actions are open-ended and semantic. Does deterministic policy even scale to an unbounded action surface, or only to a catastrophe-floor subset? Answer honestly.
- **Decision-oriented** — close with concrete, ranked recommendations against the six decisions: the catastrophe floor (a concrete candidate list), use-case priority, interception architecture, authoring/personalization approach, positioning, and lab-relevance framing. Plus the top risks and cheapest experiments to de-risk each.
- **The one-question test** — end with: "The single most important lesson from decades of constraining powerful untrusted execution, for Symbolica, is ___ — because ___."
