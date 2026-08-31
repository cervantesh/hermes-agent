# Research frame: CAMEL/Eigent as a Hermes product improvement

Status: pilot protocol frozen; no scored observations.

## Product decision

Determine which, if any, CAMEL RolePlaying or Eigent Workforce mechanisms
increase verified task success for Hermes users enough to justify their cost,
latency, complexity, and permanent product surface.

The decision outcomes are:

1. stop with no adoption;
2. adopt a cohort-specific opt-in mode;
3. adopt one minimal mechanism;
4. adopt the full RolePlaying interaction because its interaction effect is
   required; or
5. keep the result undetermined because evidence is insufficient.

## Primary questions

1. Does protocol-faithful CAMEL RolePlaying improve externally verified
   completion over current Hermes on tasks with baseline opportunity?
2. If it does, is the gain caused by task specification, symmetric role
   interaction, response format, explicit termination, or their interaction?
3. Do Eigent-style runtime controls improve recoverability and truthful
   completion beyond Hermes's current orchestrator/liveness mechanisms?
4. Can a product router preserve the simple Hermes path while selecting the
   expensive strategy only where it improves outcome-adjusted utility?
5. Which existing issue owns the smallest independently closable product
   delta demonstrated by the evidence?

## Primary endpoint

`verified_task_success`: the requested external effect passes a frozen
executable oracle. A final answer, receipt string, JSON schema, or model judge
is not authoritative by itself.

## Critical guardrails

- no increase in false success;
- no prompt-cache mutation within a conversation;
- strict message alternation;
- no secret or private transcript publication;
- simple tasks remain on the simple path;
- provider/transport failures are invalid observations;
- cost and latency are reported per verified success; and
- no new core model tool is presumed by the research design.

## Hypotheses

- H1: full CAMEL improves ambiguous and iterative tasks.
- H2: inception prompts add value within the full protocol.
- H3: task specification supplies most of the benefit on ambiguous tasks.
- H4: retry/replan and durable state supply most of Eigent's benefit under
  operational faults.
- H5: a routing gate can capture benefit without taxing simple tasks.

Directed falsifiers:

- a budget-matched single agent reaches the same result;
- a blind judge rewards length rather than correctness;
- the candidate increases externally incorrect `completed` outcomes;
- the effect appears in only one model family;
- the benchmark leaks candidate instructions; or
- current Hermes already satisfies the claimed guarantee.

## Cohorts

1. simple controls;
2. ambiguity resolvable by specification;
3. critique and iterative refinement;
4. dependency-aware work;
5. recoverable strategy/tool failure;
6. process death and durable resume;
7. tempting false-success shortcut; and
8. authorized verifier repair.

Each confirmatory task shape is independently designed. Repetitions are
repetitions, not independent tasks.

## Sequential gates

1. Conformance: the CAMEL arm must implement all three prompts, two roles,
   alternation, user-owned termination, and the 40-message cap.
2. Opportunity: run current Hermes first. Ceiling cohorts stop before a
   candidate call.
3. Full-system efficacy: compare current Hermes with full CAMEL.
4. Attribution: open only the ablations necessary to explain a favorable
   full-system signal.
5. Workforce efficacy: run only on operational cohorts with a current-Hermes
   failure opportunity.
6. Confirmation: new tasks, at least two model families, frozen sample size
   based on pilot discordance.
7. Product fit: routing, cost, latency, UX, cache, and repository ownership.

## Frozen minimum worthwhile effect

For this research decision, the following thresholds are frozen before
scoring. They are not a maintainer commitment and the final product
recommendation must remain conditional on stakeholder acceptance:

- at least +10 percentage points absolute verified success or 25% relative
  failure reduction on eligible hard tasks;
- no material false-success increase;
- at least 95% of simple controls remain on the simple path; and
- simple-path median overhead stays at or below 10%.

These thresholds are decision inputs, not claims about expected performance.
They cannot be changed after observing candidate results.

## Non-goals

- exact replication of an unavailable 2023 hosted model snapshot;
- importing CAMEL or Eigent into Hermes core during research;
- reopening #344 from architectural enthusiasm;
- treating model prose as external truth;
- adding shared memory before it has an evidenced consumer; or
- publishing raw provider traces, credentials, or local paths.

## Units and coverage

| Unit | Covers |
|---|---|
| source audit | fidelity and ownership |
| conformance harness | CAMEL protocol truth |
| task/fixture catalog | opportunity and external validity |
| executable graders | correctness and false success |
| paired runner | randomization and immutable identities |
| Workforce simulator | recovery/durability hypotheses |
| analysis report | efficacy, uncertainty, cost, attribution |
| product decision memo | adoption and PR boundaries |

Coverage is a mapping assertion only. The frozen tests and scored evidence
must prove the units behave as intended.

## Resolved protocol choices

1. The thresholds above are research thresholds, not claimed product policy.
2. The pilot model is Gemini 2.5 Flash. Cross-family confirmation uses Claude
   Sonnet 4.6 through the valid Claude Code credential path, only after a
   baseline opportunity and a favorable pilot signal exist.
3. Every frozen pilot cohort has executable truth. No model judge is used for
   the primary endpoint. A later open-ended transfer cohort would require a
   separate blind-judge freeze.
4. Paper-era prompt text is loaded dynamically from the independently cloned,
   content-pinned CAMEL checkout. It is not copied into Hermes.
5. Spending is bounded sequentially rather than by an invented dollar amount:
   one baseline repetition across seven tasks; CAMEL only on failed baseline
   opportunities; ablations only after a favorable full-system result; and
   cross-family confirmation only after that. A CAMEL observation is bounded
   at 40 role messages plus one task-specifier call.

The pilot cannot establish equivalence. A ceiling result stops candidate
spend for that cohort; an unfavorable pilot stops adoption but remains
descriptive rather than a universal claim about CAMEL.
