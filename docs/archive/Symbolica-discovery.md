# Symbolica Customer Discovery Plan

Product work before engineering work. Unlike Strata — a better mousetrap in a known category (embedded multi-primitive DB with branching), where demand pre-existed and the buyer, value-receiver, and cost-bearer were one person — Symbolica is a riskier bet on three counts that compound:

1. **Category creation, not a better mousetrap.** Nobody is shopping for a "verification layer for agent actions." We bet a problem becomes acute, not that demand exists.
2. **Cost-bearer ≠ value-receiver.** Symbolica imposes a constraint (integration, latency, false positives on the developer) while the value (safety, audit) accrues to the business and compliance. Developers don't seek a layer that blocks their agent.
3. **Pain may be anticipated, not felt.** Much of mid-2026 agent work is still read-mostly or human-gated. The autonomous-consequential-action-at-scale world is partly ahead. Right thesis + too early = dead company.

Discovery is therefore not a box to check. It tells us whether to **build now, pivot the wedge, or wait.**

## 1. Principle: Design Discovery to Kill the Thesis

The thesis is seductive — smart engineers will nod along and call it valuable. That politeness is poison. Ask only about what people have **actually done and experienced** (the Mom Test): past behavior, real incidents, current tools. Never ask "would you use a verification layer?" The more compelling the pitch, the more rigorously we avoid giving it. The exercise has value only if we go in willing to hear "not yet" or "wrong wedge" and act on it.

Founder note: Strata credibility gives privileged access to exactly these engineers — but the founder is also now the person most in love with this thesis. That is the discovery trap. Hold the PRD and demo *back* in early interviews; they are leading material and become reaction props only in later solution-validation rounds.

## 2. Riskiest Assumptions, Ranked (what discovery must test)

Each is a falsifiable hypothesis with a kill condition. The order is by lethality to the current plan.

### A. The Wedge — pain is compositional/stateful, not single-call *(existential)*

The entire differentiated architecture (cumulative state, ontology, simulator, the "OPA can't do this" claim) rests on the belief that the loopholes that matter are cross-call, multi-step, cumulative.

- **Test:** "Walk me through a time your agent did something wrong — or that you actively guard against. What exactly happened?" Classify each real incident/fear as single-call vs. multi-step/cumulative.
- **Kill condition:** if the large majority of real pain is single-call (wrong recipient, one bad delete), a content filter or per-call check handles it, and the stateful wedge solves a problem people don't yet have. → Reconsider the wedge or the timing.

### B. Felt vs. Anticipated *(timing)*

- **Test:** "Tell me about a time an agent did something in production you wish it hadn't." Can they? With real consequences?
- **Kill condition:** if pain is uniformly hypothetical across segments → we are early; consider waiting or narrowing to the one segment where it's felt.

### C. Current Harness / Workaround Baseline *(insertion + competition)*

- **Test:** "Show me how you keep your agent from doing the wrong thing today." Prompt instructions? Hardcoded checks? Approval gates? Human-in-the-loop? Where in the stack?
- **Reveals:** the workaround we must beat, and the real insertion points (wrapper vs. gateway vs. framework hook).
- **Kill condition:** if "good enough" hacks satisfy them and no incident is forcing change → adoption trigger is absent.

### D. Who Owns the Problem *(buyer)*

- **Test:** "When the agent does something bad, whose job was it to prevent it?" Developer, platform, security, compliance?
- **Reveals:** the buyer — and whether they are the same person as the integrator. A mismatch (security feels the pain, developer bears the cost) is a known adoption killer; quantify it.

### E. Build vs. Buy *(defensibility)*

- **Test:** "If you needed this, would you build it or buy it? Have you started building anything like it?"
- **Kill condition:** if competent teams reflexively build it in a sprint, the clonable-kernel / OSS-compression risk (PRD §27.4) is fatal — defensibility must move to the parts that aren't a sprint (simulator-at-scale, ontology, corpus).

### F. Adoption Trigger *(GTM)*

- **Test:** "What would have to happen for you to adopt something like this?" Incident? Compliance mandate? Scale threshold? Auditor demand?
- **Reveals:** the GTM trigger and whether it is reachable, or whether we must wait for the market to generate it.

### G. Friction Tolerance *(product cost)*

- **Test:** current tolerance for added latency, integration effort, and especially false positives ("how would your team react to a guardrail that blocked a legitimate action once a day?").
- **Reveals:** the FP/latency budget — directly informs the mosaic-demo FP gate (PRD §31.3) and the shadow-mode default.

## 2.5 Beachhead Signal: Database Operations (founder-market fit)

The founder was the founding/Principal PM for **IBM Db2 Genius Hub** (autonomous Db2 management; IBM's own framing: "initially advisory by design, evolved so AI agents propose and execute database operations with user approval"). This is firsthand evidence that the pain is **felt, not anticipated**, in the database-operations segment — and it confers founder-market fit there: credibility with DBAs and buyers, a warm network (Db2 Genius Hub users, IBM ecosystem), and lived knowledge of the exact failure modes.

Implication: **database operations is the leading beachhead candidate**, with PII as the universal expansion/vision. Universal-pain-without-access loses to felt-pain-with-unfair-advantages at the seed stage. The §22 optimizer loophole (create_index + runstats + rebind, each fine alone, together shifting optimizer behavior without impact analysis) is already compositional, real, and founder-validatable — a stronger beachhead demo than refunds (keep refunds as the concept primer).

Two disciplines still apply:
- The founder is a **discovery subject**, not a substitute for discovery: mine the Db2 Genius Hub experience for the wedge question (were dangerous failures compositional or single-call?), the buyer (founder's team vs. customer DBA/security?), and the workaround baseline (what safety was actually built — approval gates, allowlists, blast-radius limits, dry-runs?).
- Founder conviction validates one segment and felt pain; it is not yet the wedge answer, and the founder is now at maximum bias risk. The network makes database-ops discovery fast and cheap — lean into it, don't skip it. Warm DBA / platform-owner intros are the highest-quality, lowest-cost path to the wedge answer (assumption A).

Note: Db2 Genius Hub (IBM) and AgentCore (AWS) make the database-agent space active — validation, not threat. Db2 Genius Hub is the customer *archetype*, not a competitor; Symbolica is the vendor-neutral cross-database governance layer such agents need.

## 3. Who to Talk To

Sample three segments deliberately; do not over-index on the easiest to reach.

| Segment | Why | Notes |
|---|---|---|
| Vertical-agent startups | Feel pain early, low process, fast to act | Easiest access; risk of non-representative "move fast" bias |
| Platform teams rolling agents out internally | Compliance pressure + build-vs-buy tension | Closest to the eventual buyer mismatch |
| Regulated / high-stakes builders (fintech, infra, healthcare) | Consequences are concrete and felt | Where the wedge, if real, is realest |

Plus, at a handful of orgs, interview the **adjacent owner** (security/platform/compliance) separately to test assumption D directly.

**Count:** ~20–30 conversations. Patterns emerge by ~15; the wedge answer (A) often sooner. Not 5 (anecdote), not 100 (paralysis).

## 4. Interview Guide (behavior-focused, no pitch)

Open: "Tell me about the agent you're building and what it can actually *do* — what actions does it take?"

Then, by assumption:
- (B) "Tell me about a time it did something you wish it hadn't." → consequences? caught how?
- (A) For each incident/fear: "Was that one bad action, or a sequence that was individually fine?"
- (C) "How do you prevent that today? Walk me through the actual mechanism."
- (D) "Whose job is it when that goes wrong?"
- (E) "Have you built anything to catch this? Would you build or buy?"
- (F) "What would make you prioritize fixing this?"
- (G) "How does your team feel about a check that occasionally blocks a legitimate action?"

Close: "Who else should I talk to?" (referral chain).

Never: "Would you use a tool that...", "Does this sound valuable?", or any description of Symbolica before the behavioral questions are exhausted.

## 5. Decision Signals

After ~20–30 conversations, read the evidence against three outcomes:

- **GO (build the kernel as specced):** real, felt, *compositional* pain in at least one segment; an identifiable buyer; a reachable trigger; workarounds visibly inadequate.
- **PIVOT (re-aim the wedge):** pain is real and felt but mostly single-call, or concentrated in a different failure class than cumulative loopholes. → Re-scope the product around what actually hurts (which may still use the same kernel substrate).
- **WAIT (thesis right, market early):** pain is anticipated not felt, no trigger, workarounds satisfy. → Stay close to the segment closest to felt pain; revisit on a defined cadence rather than building ahead of demand.

Define the rough thresholds *before* interviewing (e.g. "if fewer than ~1 in 4 real incidents are compositional, that's a PIVOT signal"), so the conclusion isn't fitted to the hope.

## 6. What Discovery Unblocks

Discovery directly resolves open questions already logged in the PRD (§26.1) and the demo/positioning forks:

- The wedge answer (A) → confirms or redirects the entire technical architecture, and chooses between the refund (compositional) and incident-driven demos.
- Buyer (D) → resolves product identity (§26.1 #8), positioning, and who the SDK-vs-gateway surfaces target.
- Friction tolerance (G) → informs the mosaic FP gate (§31.3), the assurance-exposure surface (#9), and shadow-mode defaults.
- Current harness (C) → validates the insertion strategy (wrapper vs. gateway priority, distribution doc).
- Build vs. buy (E) → calibrates the open-core cut line (#12) and the pace of the launch plan.

## 7. Sequencing With Engineering

1. **Discovery first.** Gates the engineering commitment.
2. **Kernel spec stays ready, unbuilt.** Not wasted — a working refund demo can later serve as a *reaction prop* in solution-validation interviews.
3. **Build `symbolica-core` only after a GO signal** (or a PIVOT that redefines what to build).

The cheap version of being wrong is ~25 conversations. The expensive version is six months of Rust. Spend the cheap one first.
