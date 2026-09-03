# Shared Context Research V7 — Initial Design Freeze

Status: `FROZEN`

Freeze ID: `SCR-V7-INITIAL-2026-09-02`

Frozen on: 2026-09-02 (America/Santo_Domingo)

Hermes reference: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

CAMEL reference: `camel-ai/camel@5cd0d0f4bda29893bdbf90c707c4ee59e36c829c`

Issue under study: <https://github.com/NousResearch/hermes-agent/issues/377>

Prior evidence:

- V4: no demonstrated increment for the evaluated scratchpad treatment.
- V6: the 4,096-character startup projection cap was reachable, but current
  Hermes recovered the complete parent result through `kanban_show`.

This document freezes the initial research design. It is not an
implementation proposal and does not authorize production changes.

## 1. Scope boundary

The research is limited to evaluating CAMEL-derived cooperation and shared
context behavior for Hermes issue #377.

Three source layers must remain distinct:

1. The 2023 CAMEL paper defines role-playing, task specification, multi-turn
   cooperation, and explicit termination. It does not define a shared
   key-value store.
2. Current CAMEL Workforce provides task-result dependencies, parallel task
   execution, and optional sharing of complete conversation/tool-call memory
   among supported workers at workflow lifecycle boundaries.
3. Declared keys, active writes, namespaces, and durable scratchpad behavior
   are Hermes #377 adaptations inspired by CAMEL memory-pool ideas. They must
   not be represented as behavior proved by the original paper or by current
   Workforce unless separately verified.

The research must not expand into a generic distributed database, general
workflow engine, broad authorization redesign, or remote-filesystem project.

## 2. Common comparison frame

Each scored track selects only the arms necessary for its hypothesis:

- `R` — pinned CAMEL Workforce reference behavior.
- `A` — explicit parent relay.
- `B` — the strongest relevant mechanism already available in current Hermes.
- `C` — a harness-only simulation of the applicable CAMEL behavior.
- `D` — the minimal declared-key adaptation proposed by Hermes #377, only
  where that adaptation is the subject of the track.

`B` must be allowed to use all existing reachable Hermes mechanisms,
including parent-result projection, `kanban_show`, genuinely shared artifacts,
cross-task comments, and live comment steering.

No harness-only treatment may be described as production code.

## 3. Common evidence contract

Before scored observations:

- freeze source revisions, fixtures, model cohorts, arm order, thresholds,
  stopping rules, controls, and expected oracles;
- publish or otherwise timestamp a protocol seal;
- use a fresh `HERMES_HOME`, board, session, and task graph per observation;
- use exact executable external oracles rather than agent self-reports;
- record prompt bytes, input/cache/output tokens, calls, latency, tool traces,
  task transitions, and result digests;
- retain terminal failures and provider failures without replacing adverse
  observations;
- quarantine provider/infrastructure failures from product observations;
- prohibit post-result fixture or threshold tuning;
- sanitize public evidence while retaining private raw receipts when needed.

Cross-family confirmation is required before an implementation opportunity can
be claimed.

Unless a track freezes a justified exception, the resource gate is:

- equal externally verified success;
- at least 15% lower median token use or 20% lower median latency;
- no regression on the other resource metric; and
- repetition across two model cohorts.

## 4. Independent research tracks

### Track 1 — Context cost and volume

Question: when current Hermes and a targeted retrieval path produce the same
exact result, does targeted retrieval materially reduce context volume, token
use, or latency?

Design:

- generate a large structured producer result containing opaque records;
- reveal the required subset only to the consumer after producer completion;
- compare complete parent retrieval with CAMEL dependency behavior and the
  minimal declared-key projection;
- include an all-records-required control where selective retrieval should not
  have an artificial advantage.

Primary gate: the common resource gate with exact result equality.

Disposition rule: if a compact/delta `kanban_show` mode yields the same
benefit, issue #95561 owns the smaller-footprint solution.

### Track 2 — Selective key access

Question: is there a real context size or signal-to-noise boundary at which
current Hermes fails an external oracle while declared-key retrieval succeeds?

Design:

- test increasing payload sizes under the same real model budget;
- use opaque values and consumer-only key selection;
- include an all-keys-required control;
- prevent producer tailoring and hidden artifact access.

Primary gate: a repeated `D`-only exact success across at least two seeds and
two model families, or the common resource gate.

This track evaluates the #377 adaptation; selective declared keys are not to
be attributed to current CAMEL Workforce without new source evidence.

### Track 3 — Isolation and permissions

Purpose: safety qualification, not an efficacy claim.

Candidate declared-read policy:

- own task: allowed;
- declared completed parents: allowed;
- unrelated task in the same workflow: denied;
- different workflow: denied;
- different tenant: denied;
- different board: denied;
- undeclared key: denied.

Design:

- use a unique canary for every boundary;
- run deterministic handler-level probes before real-agent probes;
- search results, transcripts, tool outputs, and memory for unauthorized
  canaries;
- include positive controls for every allowed relationship.

Current CAMEL full-memory sharing is all-to-all among participating supported
workers. A conflict with the candidate Hermes boundary is an adoption
incompatibility, not a CAMEL defect.

A current-Hermes cross-task read must be reproduced and its intended policy
adjudicated before it is called a vulnerability.

### Track 4 — Active writes

Current CAMEL Workforce memory synchronization is task-boundary-oriented.
Active writes are therefore a #377-derived extension, not a direct
reproduction of current CAMEL shared-memory behavior.

The track may advance beyond discovery only after identifying a real workflow
where:

1. a producer remains active;
2. another participant needs a checkpoint before producer completion;
3. waiting for the terminal result causes an observable failure; and
4. current `kanban_comment` plus live steering does not satisfy the need.

Only then compare current Hermes with a structured, versioned, harness-only
write/read path. Synthetic convenience alone cannot open this gate.

### Track 5 — Concurrency

This track is conditional on Track 4 demonstrating a real need for writable
shared state.

Required cases:

- two writers to disjoint keys;
- two writers to the same key;
- a reader overlapping a commit;
- writer death before and after commit;
- idempotent retry of the same write; and
- deterministic version/ordering observation.

Invariants:

- no lost updates;
- no partially serialized read;
- explicit conflict or enforced single-writer policy;
- operation-level idempotency; and
- no success inferred from model prose.

Use independently scheduled processes and deterministic barriers. An
in-process lock or CAMEL TaskChannel claim lock alone is not distributed-state
evidence. Any lost update rejects the candidate; it does not authorize a new
distributed store.

### Track 6 — Remote backends

Remote terminal execution and remote agent runtimes are separate topologies.

The portability matrix is:

- Docker terminal backend;
- SSH terminal backend;
- Modal ephemeral backend;
- separate agent containers sharing coordination state; and
- true multi-host agent runtimes.

Verify exact result reachability, digest equality, absence of unusable host
paths, and coherent task ownership. Run this track only after a local treatment
demonstrates value.

Do not add distributed infrastructure merely to make the experiment pass.
Route reproduced failures to existing owners when applicable, including
#56656, #81984, and #101015.

## 5. Execution order and dependency gates

1. Freeze sources and ownership audit.
2. Run Track 1, Track 2, and the Track 3 preflight.
3. Stop if there is neither a current-Hermes RED nor a repeated material
   resource advantage.
4. Conduct Track 4 discovery; do not score it without a real workflow witness.
5. Run Track 5 only if Track 4 opens the writable-state gate.
6. Run Track 6 only for a treatment that already demonstrated local value.
7. Open or revise an implementation-ready issue only for the smallest
   mechanism supported by replicated evidence.

## 6. Valid dispositions

Each track must end independently as one of:

- `IMPLEMENTATION OPPORTUNITY`
- `EXISTING HERMES MECHANISM SUFFICIENT`
- `EXISTING OWNER`
- `NO DEMONSTRATED INCREMENT`
- `CAMEL-INCOMPATIBLE WITH REQUIRED BOUNDARY`
- `INCONCLUSIVE`

No disposition applies automatically to the other tracks.

## 7. Planned evidence layout

```text
evals/shared_context_research_v7/
├── INITIAL_DESIGN_FREEZE.md
├── DESIGN_SEAL.json
├── CAMEL_REFERENCE_CONTRACT.md
├── OWNERSHIP_AUDIT.md
├── common/
├── context_cost/
├── selective_access/
├── isolation/
├── active_writes/
├── concurrency/
└── remote_backends/
```

Every scored track owns its protocol freeze, seal, fixtures, controls, public
sanitized receipt, private raw evidence boundary, result, and disposition.

## 8. Change control

This initial design is immutable after sealing.

Future work must refer to it by Freeze ID and digest. A correction or design
change must be recorded in a separate amendment containing:

- amendment ID and timestamp;
- exact section affected;
- reason and evidence discovered after the freeze;
- whether observations already exist;
- whether a new protocol seal and fresh repetition are required; and
- an explicit statement that the original freeze remains historical evidence.

Never edit this file to make later results look preregistered.
