# Frozen protocol: issue #377 shared-context opportunity study

Status: `SEALED` on 2026-09-01 after adversarial challenge and real-worker
preflight. Any decision-rule change requires a versioned replacement receipt;
this file must not be rewritten after a scored observation.

## Question and arms

For dependent, tool-using Hermes workflows, does a bounded workflow-scoped
scratchpad improve verified outcome, fidelity, parent-token use, or latency
over the mechanisms available on current main?

Each deterministic fixture is executed through three arms:

| Arm | Handoff contract |
|---|---|
| A: parent relay | producer worker -> parent-model lossless relay -> consumer worker |
| B: existing handoff | validated shared artifact for shared-storage tasks; real Kanban `complete_task` + parent link + `build_worker_context` for detached-source tasks |
| C: scratchpad simulation | validated producer artifact -> atomic write-once workflow store -> declared-key projection -> consumer worker |

Producer and consumer are real dispatcher-owned Kanban workers. The harness
creates cards in a clean temporary board, calls current main's real
`dispatch_once()` with its default worker spawn, waits for the worker's
`kanban_complete()` transition, and verifies that the worker called
`kanban_show()` before completion. The parent relay is one real Hermes model
call over the producer's handoff. Arm C exists only in the harness and adds no
production code or model tool.

Using one worker lifecycle for all arms avoids comparing a lightweight context
projection with the cost or behavior of a full Kanban worker. The harness calls
each dispatcher tick immediately; configured gateway polling delay is excluded
and reported separately rather than attributed to any handoff arm.

## Runtime identity

- Hermes target: `180291162ff4df0d42b5dc4fecd08005cf7cebf9`
- Provider path: `claude-code`
- Model: `claude-haiku-4-5`
- Worker maximum iterations: 30
- Parent-relay maximum iterations: 3, no tools
- Schedule seed: 377
- Fixture seed: 377
- Per-observation timeout: 1,800 seconds
- Pilot repetitions: one

The runner records the exact target tree identity. A dirty or different target
is rejected unless the run receives a new label and a new freeze receipt.

## Pilot cohort

Six workflows are frozen for the first gate: four dependent workflows and two
negative controls. Each arm receives byte-identical source fixtures and the
same consumer contract.

| ID | Topology | Executable requirement |
|---|---|---|
| `compact_release_map` | detached source | preserve opaque component/version/checksum fields and select the named release subset exactly |
| `ordered_dependency_plan` | detached source | preserve a dependency graph and emit the unique valid topological plan plus its digest |
| `artifact_policy_join` | shared storage | join the producer's normalized artifact with a consumer-local policy and emit exact selected records |
| `distractor_filtered_catalog` | detached source | filter seeded opaque records by tenant, region, epoch, and allow-list without admitting decoys |
| `independent_local_control` | shared storage, no dependency | derive output only from consumer-local input; no handoff key or artifact is exposed |
| `independent_detached_control` | detached source, no dependency | derive output only from consumer-local input; no parent link or scratchpad namespace is created |

The producer must create a declared JSON artifact. The harness validates that
artifact before any arm can transmit it. The consumer writes a separate JSON
result. The grader compares both artifacts to deterministic expected values;
model summaries are never the oracle.

For detached-source fixtures, producer and consumer receive distinct absolute
Kanban workspaces. After the producer's artifact is validated and the arm's
handoff has been committed, the producer workspace is removed before the
consumer is dispatched. This proves that the consumer cannot fall back to the
source artifact during the run. It does not prove an SSH, Modal, container, or
multi-host access boundary.

The canonical handoff is UTF-8 JSON serialized with sorted keys, compact
separators, and no ASCII escaping. Every arm begins with those exact bytes:

- A asks the parent model to reproduce one delimited canonical block without
  interpretation; the reproduced bytes and digest are measured;
- B's detached-source producer stores that canonical block as its exact
  completion `summary` and stores only `sha256` and `byte_count` as metadata;
  the consumer receives the real parent-link projection;
- B's shared-storage consumer reads the validated canonical artifact directly;
  no parent-link payload is added;
- C atomically publishes those bytes under the declared workflow/key and
  injects the same delimited block into an independent consumer card.

No arm may synthesize extra fields. Every hop records pre/post byte counts and
digests. A producer that cannot create both an exact artifact and the required
canonical completion summary invalidates the paired fixture before arm
comparison rather than selectively disadvantaging B.

## Conditional expansion

The pilot stops after six workflows unless at least one dependent observation
shows eligible opportunity:

- A or B fails an external oracle while C passes; or
- C and B both pass, but C reduces median end-to-end latency by at least 20%
  with no greater total-token use; or
- C and B both pass, but C reduces total tokens by at least 15% with no greater
  latency; or
- B loses source fields before the consumer and C preserves them exactly.

For this expansion gate, correctness and fidelity are evaluated per paired
fixture on the four dependent seed-377 units. Resource triggers use
`100 * (B - C) / B` for each of those four units and the median of the four
signed improvements. The comparator is inclusive (`>= 15%` tokens or
`>= 20%` latency). Missing usage or a zero B denominator cannot open the token
trigger; a missing timing value or zero B duration cannot open the latency
trigger. They do not suppress an independently observed correctness or fidelity
trigger.

If and only if that gate opens, add two already specified but not-yet-executed
workflows:

- `multi_key_reconciliation`: three independently declared upstream values
  must be reconciled without cross-key overwrite; and
- `bounded_payload_edge`: a canonical handoff near the documented Kanban
  per-field cap tests truncation and explicit failure rather than silent use.

Complete seed 377 for those two workflows, then execute all eight workflows
with schedule seed 378. Thus every dependent workflow used in confirmation has
two paired observations. No further task or threshold is added in this study.

## Metrics

For every observation record:

- `verified_workflow_success`;
- producer-artifact exactness;
- handoff field count, byte count, and SHA-256 digest at publish and consume;
- consumer-result exactness;
- `false_success` when the model claims completion but an oracle fails;
- parent input/output/total tokens;
- child and aggregate tokens;
- end-to-end monotonic duration;
- files and scratchpad keys outside the declared allow-list; and
- treatment/topology identifiers without raw local paths.

Token values are reported only when the provider returns usage. Missing usage
is `unverified`, never zero. Timing is descriptive on this single machine and
cannot alone establish a general performance claim.

## Integrity gates

The following deterministic tests must pass before a model pilot begins:

1. two concurrent workflow IDs cannot read or enumerate each other's values;
2. a committed upstream key is write-once: same-digest replay is idempotent and
   a different value is rejected;
3. an uncommitted or interrupted write is invisible to readers and cannot be
   graded as success;
4. undeclared keys are denied rather than omitted silently;
5. a downstream worker cannot mutate upstream authority;
6. the two independent controls create and receive no handoff state;
7. detached-source producer and consumer directories share no task files, and
   the producer directory no longer exists when the consumer starts;
8. every arm uses an actual dispatcher-owned worker that calls `kanban_show`
   and reaches `kanban_complete` through the lifecycle tool;
9. C rejects handoff truncation or malformed canonical JSON before commit;
10. sanitization removes prompts, summaries, raw messages, credentials, home
    paths, temporary paths, and environment values.

For B, the documented 4 KiB-per-field truncation is a scored limitation, not an
integrity-gate failure: the harness records the truncation marker, and a
consumer that proceeds to an incorrect result is externally failed. The
detached-source tests demonstrate handoff without a surviving source artifact
on one host. Actual SSH, Modal, container, and multi-host execution remain
explicitly unverified.

## Fairness rules

- Arms receive the same authoritative producer value and consumer contract.
- Arm C may project only keys declared by the workflow; it cannot add hints,
  summaries, or computed fields unavailable to A and B.
- Arm B may use both Kanban summary and metadata within current documented
  limits. It is not restricted to an artificially weak prose-only baseline.
- Every temporary B board begins empty. Before consumer dispatch, the harness
  inventories `build_worker_context()` sections and rejects undeclared prior
  attempts, comments, assignee history, runs, or events.
- Arm A's relay instruction requires canonical lossless transfer and forbids
  interpretation. Its model cost remains part of the treatment.
- A consumer sees only its treatment's handoff, not another arm's artifact.
- Failed producer validation invalidates all three paired arms for that fixture
  rather than counting selectively against one treatment.
- Execution order is randomized, but the order and seeds are recorded.

## Provider and observation exclusions

Authentication, quota, rate-limit, transport, or provider-service failures are
invalid observations. One retry is permitted only for a classified transient
provider/transport failure, using the same arm, task, fixture, and schedule
position. A second failure stops the batch as `INCONCLUSIVE`; it is not replaced
with another task or model. Tool misuse, failure to follow the task, timeout,
or externally wrong output is a scored product outcome.

## Frozen adjudication

The paired unit is `(fixture_id, schedule_seed)`. Correctness uses the twelve
dependent units produced by six dependent fixtures across seeds 377 and 378.
For resource rules, compute each pair's signed improvement
`100 * (B - C) / B`, then take the median of the six fixture improvements
separately within each seed. A missing usage value, a zero denominator, or a
missing timing value cannot satisfy the corresponding resource rule. The
threshold comparator is inclusive (`>=`). Controls are excluded from effect
medians and must pass independently.

`IMPLEMENTATION OPPORTUNITY` requires all integrity gates plus, after the
conditional expansion, one of:

- at least three paired dependent observations where C passes and B fails,
  with no observation where B passes and C fails; or
- equal verified success, at least 15% lower median total tokens or 20% lower
  median latency for C than B, no regression on the other resource metric, and
  the threshold met separately in both schedule seeds.

It additionally requires zero new false-success and zero scope-expansion
events in C. A parent-token reduction alone does not qualify, because current
arm B already avoids a parent model relay.

`EXISTING HANDOFF SUFFICIENT` applies when B matches or exceeds C in verified
success and fidelity and C does not clear the resource threshold. This verdict
is restricted to the tested workflows and topologies.

If the signed median effect is at least 10% in opposite directions across the
two seeds, or correctness has both a C-only success and a B-only success, the
resource/correctness comparison is `INCONCLUSIVE` rather than evidence of
sufficiency. Exact equality is reported as a tie.

`NO OPPORTUNITY` applies when all arms reach ceiling and neither B nor C shows
a qualifying resource advantage over the other, or when the eligibility gate
never opens.

`INCONCLUSIVE` applies when integrity, runtime identity, provider availability,
or sample discordance prevents the rules above from adjudicating.

These thresholds are product-research decision rules, not statistical proof of
equivalence or a general claim about all multi-agent work.

## Evidence contract

Raw JSONL, provider messages, and temporary workspaces remain local and ignored.
The sanitized packet contains:

- exact repository and harness revisions;
- protocol and fixture hashes;
- commands and runtime labels;
- per-observation arm/task/rep, boolean checks, digests, byte counts, usage,
  timing, and exclusion reason;
- aggregate paired tables and uncertainty language; and
- a verifier that recomputes receipt hashes and rejects mixed identities.

No public action is authorized by this protocol.
