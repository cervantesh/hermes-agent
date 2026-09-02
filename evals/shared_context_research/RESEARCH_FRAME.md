# Research frame: workflow-scoped context handoff for Hermes

Status: frozen before scored observations.

## Product question

Determine whether a workflow-scoped scratchpad improves externally verified
correctness, information fidelity, parent-token usage, or latency over the
handoff mechanisms already present in Hermes.

The decision is deliberately narrower than issue #377's proposed architecture.
This study evaluates a product hypothesis. It does not presume that shared
memory, new model tools, or a core change should exist.

## Evidence frame

- Target repository: `NousResearch/hermes-agent`
- Current upstream revision: `180291162ff4df0d42b5dc4fecd08005cf7cebf9`
- Harness base revision: `34931694f2f44597a862bea48114b316cb09ab71`
- Issue under evaluation: #377, last updated 2026-07-26
- Existing parent-link implementation/documentation: PR #83061, merged as
  `d3560b82c4c49735f839a67a1379b833ec49638d`
- Related open proposal: PR #82157 at
  `722fcc12d843c725e487e7d9a4dbea7a2cad4c37`

All code claims are evaluated against the pinned upstream revision. Later
upstream changes require a new evidence frame rather than silent reuse of this
one.

## Strict scope

Compare three ways to move authoritative output between dependent workers:

1. **A — parent relay:** the producer returns a handoff, the parent model
   reads/reformats it, and a downstream worker consumes the relay.
2. **B — existing Hermes handoff:** use existing artifacts where a filesystem
   is shared and the real Kanban parent-link summary/metadata projection where
   producer and consumer workspaces are isolated.
3. **C — simulated workflow scratchpad:** the harness publishes validated,
   immutable, workflow-scoped values and injects only declared reads into the
   downstream worker. This arm exists only in the evaluation package.

The study does not add production tools, change `delegate_task`, implement a
workflow engine, publish a PR, or edit issue #377.

## Primary endpoint

`verified_workflow_success`: every externally executable oracle for the
dependent workflow passes. Model prose, a completion marker, or a plausible
summary is not authoritative.

## Secondary endpoints

- exact field and digest fidelity across the handoff;
- false success: claimed completion while an external oracle fails;
- parent and total model tokens;
- end-to-end latency;
- scope expansion beyond the declared files, keys, or dependencies; and
- integrity failures at workflow and authority boundaries.

## Decision outcomes

1. `NO OPPORTUNITY`: the pilot exposes no baseline failure or measurable relay
   burden on eligible workflows.
2. `EXISTING HANDOFF SUFFICIENT`: arm B matches or exceeds C on verified
   outcome and integrity; a new shared-context surface is not justified.
3. `IMPLEMENTATION OPPORTUNITY`: C clears every frozen integrity gate and
   improves an externally verified outcome that B cannot provide.
4. `INCONCLUSIVE`: provider failures, insufficient discordance, or an invalid
   control prevent adjudication.

## Directed falsifiers

- current Kanban parent-link handoff already carries enough bounded context;
- a shared artifact is sufficient when workspaces share storage;
- C appears better only because it receives fuller or more favorable inputs;
- C leaks data across workflows or lets downstream overwrite upstream truth;
- partial publication is mistaken for committed data;
- independent tasks improve only because they were accidentally given context;
- token savings move cost to workers without improving total utility;
- an apparent success is only a self-report; or
- the result depends on one lucky ordering or provider response.

## Product constraints

- Per-conversation prompt caching remains untouched.
- No new core model tool is presumed.
- Inputs and token budgets are comparable across arms.
- Existing Hermes behavior is represented by its real entry points where
  practical, not by a favorable reimplementation.
- Raw provider traces remain private; public-shaped evidence is sanitized.
- Shared-storage and detached-source topologies are reported separately.
- SSH/Modal, container, and truly non-shared-filesystem execution are explicitly
  unverified unless actually exercised.

## Units

| Unit | Responsibility |
|---|---|
| ownership audit | establish current capabilities and overlap |
| frozen protocol | tasks, arms, metrics, thresholds, exclusions |
| task fixtures | independent dependent-workflow inputs |
| real-path runner | invoke Hermes delegation and Kanban handoff paths |
| scratchpad simulator | implement only the C treatment in the harness |
| executable graders | adjudicate output, fidelity, false success, and scope |
| integrity suite | isolation, immutability, atomic publication, negative controls |
| evidence sanitizer | emit hashes, commands, revisions, and aggregate receipts |
| adversarial review | try to falsify fairness, reachability, and causal claims |
| decision memo | choose one frozen outcome without broad architectural claims |

## Verification

- Deterministic tests prove namespace isolation, write-once authority, atomic
  publication, declared-read enforcement, negative-control gating, and
  evidence sanitization before any model observation is accepted.
- Producer and consumer effects are graded from files by executable oracles.
- The isolated arm B path imports and exercises current main's Kanban database
  functions rather than reproducing their behavior in the harness.
- The runner rejects mixed repository identities and records fixture, protocol,
  and receipt hashes.
- A blind adversarial pass challenges fairness and reachability before the
  protocol is sealed; a second falsification pass reviews the resulting
  evidence before adjudication.
- SSH, Modal, and multi-host behavior is reported as unverified unless it is
  actually exercised.

## Closure predicate

The research is complete only when the ownership audit and protocol are frozen,
the integrity suite passes, the pilot is either completed or stopped by a
predeclared rule, evidence is sanitized and reproducible, and an adversarial
review supports a bounded verdict. A production implementation is not part of
this closure predicate.
