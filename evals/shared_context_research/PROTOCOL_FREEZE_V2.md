# Frozen protocol V2: common-producer shared-context study

Status: **FINAL PRE-SEAL PROTOCOL** after five adversarial closure passes and
executable two-topology preflights. No V2 scored observation may run until
this exact file and its decision-critical source manifest are hashed in
`PROTOCOL_SEAL_V2.json`. V1 remains immutable and excluded. After the final
provenance-bound preflight, this file may not change; the separate seal is the
authorization boundary.

Pinned target: `main@180291162ff4df0d42b5dc4fecd08005cf7cebf9`. A
2026-09-01 refresh confirmed that this is still upstream `main` and that no
new issue or PR owns the bounded experiment.

## Reason for replacement

V1 independently regenerated the producer for A, B, and C and made exact
completion-summary reproduction a paired admission gate. That stochastic
upstream step invalidated every dependent pair despite exact artifacts. V2
changes only the experimental unit and upstream admission rule. Tasks, model,
provider, oracles, metrics, resource thresholds, expansion rules, integrity
rules, evidence privacy, and the pinned target remain those in V1 except where
this document explicitly replaces them.

## V2 experimental unit

For each `(fixture_id, schedule_seed)`:

1. Run one real dispatcher-owned producer worker.
2. Admit the fixture only if `kanban_show` is first, `kanban_complete` occurs,
   the declared artifact exists, parses, and equals the deterministic source.
3. Preserve that one producer's completion summary and validated artifact.
4. Randomize A/B/C consumer order.
5. Run each consumer as a real dispatcher-owned worker named `consumer`, but
   under a distinct temporary `HERMES_HOME`, Kanban DB, board, session store,
   and workspace root. The three roots contain byte-identical config files and
   begin empty. This isolates history without making profile identity or
   configuration a second treatment.

The producer's summary need not equal the artifact. Its fidelity is measured,
not used to invalidate one arm. For detached-source fixtures, A and B derive
their input from the same persisted producer summary; C receives the validated
artifact. For shared-storage fixtures, A derives its input from that summary,
B reads the validated artifact, and C receives the same artifact through its
declared projection. This is the treatment difference claimed by issue #377.

The common producer runs in B's isolated environment under profile `producer`.
B retains that DB so the real parent link remains reachable. A and C run in
separate environments in which the producer card does not exist. All three
consumer tasks use the same model and provider overrides, the same body except
for the handoff clause, and the same byte-identical profile config. The harness
records and compares the config digest, overrides, active profile name,
workspace policy, effective tool-schema digest, and empty pre-run session/task
counts. The identical consumer config disables `terminal`, `code_execution`,
`delegation`, `memory`, and `session_search`; the tasks require only file and
Kanban lifecycle tools. It also pins `platform_toolsets.cli` to `file`; Hermes
then adds the task-scoped Kanban lifecycle surface. This is an experimental
contamination control applied equally to every arm, not a proposed product
configuration.

## V2 arms

- **A — parent relay:** a real parent model receives the common producer
  summary and attempts a lossless relay once. The relay is placed in consumer
  A's own task body. This deliberately gives parent mediation its strongest
  fidelity baseline rather than asking it to discard fields.
- **B — existing handoff:** for detached-source fixtures, consumer B is linked
  to the common producer and receives current main's real parent-link context;
  for shared-storage fixtures, it reads the exact file object written by the
  producer in a declared shared directory inside B's root. The harness never
  copies or rematerializes that artifact after producer completion. B does not
  receive a parent link in that topology.
- **C — scratchpad simulation:** the harness atomically publishes the common
  validated artifact under declared write-once keys; the declared projection
  is placed in consumer C's own task body.

Handoff fidelity is always computed against the authoritative common artifact,
not against the producer's prose. A summary loss is therefore a scored A/B
limitation, not an invalid fixture.

## Environment, workspace, and contamination controls

- Detached-source: delete the producer workspace after capturing the common
  artifact and before dispatching any consumer.
- Shared-storage: the producer writes the canonical artifact directly to an
  absolute path in a declared directory inside B's independently created
  temporary root. B is instructed to read that same object. The receipt records
  path, digest, size, writer task, creation observation, file identity where the
  host exposes one, and B's read call. No post-producer copy is permitted. A/C
  roots do not contain that artifact.
- Each consumer has its own workspace and output file.
- Before each dispatch, B's context manifest must contain parent results when
  applicable and contain no prior attempts, consumer-role history, or comments.
- No consumer prompt, environment, DB, or task link exposes another consumer's
  home, workspace, result, or task link. Its Kanban DB must contain only its own
  consumer card, except B's DB, which also contains the common producer card.
- Before scoring, a deterministic sentinel probe calls the real
  `kanban_show(task_id=<producer-id>)` path under A and C. Both must return
  `task not found`; B must resolve the same producer ID. This proves that the
  current unrestricted explicit-ID read path cannot cross the experimental
  DB boundary.
- The preflight resolves the effective tool schema for each consumer profile.
  The three schema digests must match, and `terminal`, `process`,
  `execute_code`, `delegate_task`, `memory`, and `session_search` must be
  absent. Every remaining schema name must be a file tool or `kanban_*`. A
  scored observation is invalid if a forbidden tool appears in its trace, or
  if it invokes a Kanban operation other than `kanban_show`,
  `kanban_complete`, or `kanban_heartbeat`.
- In every consumer trace, `kanban_show` may target only the active consumer
  card (or omit `task_id`). Every `read_file`, `write_file`, `patch`, and
  `search_files` path is resolved using current main's
  `tools.file_tools._resolve_path_for_task` semantics and the worker's recorded
  workspace. A/C paths must remain inside their own workspace. B has one extra
  read-only allow-list entry for the exact shared artifact path. `..`, absolute
  paths, tilde expansion, globs, and relative paths are judged by the resolved
  target rather than lexical mention. An unresolvable or forbidden access is
  scope expansion even when the final result is correct.
- `patch(mode="patch")` is not judged from the optional `path` argument. Every
  V4A Update/Add/Delete header and both Move endpoints are extracted using the
  same accepted header family as pinned main, resolved independently, and
  allow-listed. Missing or unparseable V4A targets invalidate the trace.
- The equal consumer instruction states that no file operation may inspect a
  parent directory and that every target must remain in the assigned workspace,
  except B's single declared read-only shared artifact. This makes the resolved
  allow-list an explicit compliance contract rather than a hidden grader rule.

Actual SSH, Modal, container, and multi-host access boundaries remain
unverified. Local temporary-root separation plus observable tool restrictions
is an experimental contamination control, not a claim of OS-level access
control against a malicious process or arbitrary code running outside the
worker tool contract.

If an admitted producer has an empty, altered, or truncated summary, A and
detached-source B receive that same persisted summary and may fail fidelity.
C still receives the validated artifact. Shared-storage B remains artifact
based. This is a scored handoff outcome, not producer invalidation.

## Frozen schedule

The schedule is blocked so provider/host position is not systematically tied
to an arm. Before results, a seeded Python 3.11 RNG produced a constrained
random assignment from all six A/B/C permutations. The four pilot-dependent
fixtures give every arm a first/second/third-position count differing by at
most one. The remaining two permutations are reserved for the predeclared
expansion fixtures, so all six dependent fixtures use every permutation once.
The table below is authoritative; a deterministic generator test is only a
guard against transcription drift.

| seed | fixture | consumer order |
| --- | --- | --- |
| 377 | `distractor_filtered_catalog` | A, C, B |
| 377 | `compact_release_map` | B, C, A |
| 377 | `artifact_policy_join` | C, A, B |
| 377 | `ordered_dependency_plan` | A, B, C |
| 377 | `multi_key_reconciliation` | B, A, C |
| 377 | `bounded_payload_edge` | C, B, A |
| 377 | `independent_detached_control` | C, A, B |
| 377 | `independent_local_control` | B, C, A |
| 378 | `artifact_policy_join` | C, B, A |
| 378 | `compact_release_map` | A, B, C |
| 378 | `distractor_filtered_catalog` | C, A, B |
| 378 | `ordered_dependency_plan` | B, C, A |
| 378 | `multi_key_reconciliation` | B, A, C |
| 378 | `bounded_payload_edge` | A, C, B |
| 378 | `independent_detached_control` | C, B, A |
| 378 | `independent_local_control` | B, A, C |

Fixture execution order is also frozen. Seed 377 pilot:
`independent_detached_control`, `independent_local_control`,
`artifact_policy_join`, `ordered_dependency_plan`,
`distractor_filtered_catalog`, `compact_release_map`; seed 377 expansion:
`bounded_payload_edge`, `multi_key_reconciliation`; seed 378 confirmation:
`independent_local_control`, `independent_detached_control`,
`bounded_payload_edge`, `ordered_dependency_plan`, `compact_release_map`,
`multi_key_reconciliation`, `distractor_filtered_catalog`,
`artifact_policy_join`.

## Cost and latency accounting

The common producer's tokens and worker duration are added identically to each
arm's workflow total. Each arm then adds only its own handoff and consumer
cost. The reported duration is a constructed per-arm workflow duration, not
the wall time of the sequential blocked harness.

| segment | included | boundary |
| --- | --- | --- |
| common producer | every dependent arm, identical receipt | immediately before producer dispatch through worker exit and receipt readback |
| A handoff | A only | immediately before the parent model call through its completed response |
| B detached handoff | B only | parent-link/card creation and context construction, included in the consumer segment |
| B shared handoff | B only | no post-producer setup; the producer-written object is read during the consumer segment |
| C handoff | C only | begin/stage/atomic commit/view/projection serialization |
| consumer | every arm | immediately before card creation through worker exit and result readback |
| harness setup/order gap | excluded from every arm | temp-root/profile creation and time waiting between sequential arms |
| failed provider attempt | excluded and reported | only the one V1-permitted classified retry may replace it |

Gateway dispatcher polling delay inside producer/consumer completion remains
included symmetrically because the real worker lifecycle includes it. Parent
tokens are the A relay's model usage; B/C parent tokens are structurally zero
because no parent model call occurs. Worker token usage that is absent from a
provider receipt remains missing, never zero.

For A, usage is read from the actual top-level counters returned by Hermes's
conversation result. Consumer usage normally resolves from the run's
`worker_session_id`. A lifecycle terminal such as `kanban_block` may omit that
metadata; only in the experimentally guaranteed fresh consumer profile may the
harness fall back to the sole persisted session. Zero or multiple sessions do
not resolve and remain missing usage. The receipt records which identity path
was used.

Missing token usage is unverified, never zero. V1's paired improvement formula,
inclusive 15% token threshold, inclusive 20% latency threshold, no-regression
condition, and per-seed confirmation rule remain unchanged.

## Pilot and gate

Run the same four dependent workflows and two independent controls at seed 377.
Controls have no producer or handoff state. The expansion gate is evaluated on
the four admitted common-producer pairs:

- C-only correctness where A or B fails;
- C exact fidelity where B loses authoritative fields;
- median C-vs-B token improvement `>= 15%` without latency regression; or
- median C-vs-B latency improvement `>= 20%` without token regression.

If a common producer fails admission, that fixture is invalid. If fewer than
all four dependent pilot fixtures are admitted, the pilot is `INCONCLUSIVE` and
does not expand. Provider retry and exclusion rules remain V1's rules.

If the gate opens, run both predeclared expansion fixtures at seed 377, then all
eight workflows at seed 378. Every dependent confirmation fixture must have an
admitted common producer in both seeds.

## Integrity gates added for V2

Before scoring:

1. prove exactly one producer run exists per dependent fixture/seed;
2. for detached-source fixtures, prove A and B reference that producer's same
   persisted summary; for shared-storage fixtures, prove B reads the same
   producer-written file identity and digest and receives no parent link;
3. prove C's committed digest equals that producer's artifact digest;
4. prove consumer homes, DBs, and result workspaces are pairwise distinct while
   profile names and semantic config digests are equal;
5. prove consumer order is recorded and follows the seeded schedule; and
6. prove common producer cost is identical in every arm receipt;
7. prove the cross-DB producer-ID sentinel fails in A/C and succeeds in B; and
8. prove every recorded cost segment follows the included/excluded table;
9. prove effective consumer tool schemas match and omit unobservable local
   execution surfaces; and
10. prove all file-tool targets resolve inside the arm allow-list.

The final preflight uses two trivial `preflight_*_echo` fixtures, one per
topology. They exercise the same real producer, relay, parent-link,
shared-object, scratchpad, consumer, oracle, accounting, and isolation paths,
but are not members of `TASKS`, the pilot, expansion, or confirmation cohorts.
Their only operation copies one declared upstream and one local scalar. This
keeps mechanical admission separate from stochastic product difficulty; no
preflight outcome is ever pooled. The scored fixtures remain unchanged and can
still record scope expansion, false success, or missing usage.

The corresponding executable receipt keys are
`same_summary_reference`, `scratchpad_digest_exact`, `overrides_equal`, and
`cost_segments_exact`; they are admission gates, not narrative inferences.
The scratchpad readback digest is computed only from bytes returned by the
declared read-only view (reconstructed from those bytes for multi-key tasks),
never from the expected fixture input.

All V1 store, atomicity, immutability, declared-read, negative-control,
sanitization, external-oracle, false-success, and scope-expansion gates remain.

## Provenance binding

Before a preflight or scored batch starts, the harness hashes every
decision-critical protocol, fixture, runtime, analysis, sanitizer, verifier,
and test file, including the imported V1 lifecycle runtime. Each observation
carries the canonical manifest digest; the public receipt carries both the
manifest and digest. The runner aborts if the manifest changes during a batch,
and the public verifier recomputes it from the supplied source package. Target
code is independently bound by the exact clean upstream Git SHA. A packet
without both bindings is not admissible evidence.

## Adjudication

V1's final thresholds and four outcomes remain unchanged:

- `NO OPPORTUNITY`
- `EXISTING HANDOFF SUFFICIENT`
- `IMPLEMENTATION OPPORTUNITY`
- `INCONCLUSIVE`

V2 may not claim equivalence, remote-backend support, or a general CAMEL/Eigent
result. It answers only whether the simulated scratchpad adds measured value
over current Hermes handoffs in the admitted fixtures.

Outcome precedence is explicit: a valid pilot whose gate does not open is
`NO OPPORTUNITY` under the tested cohort and stops. `EXISTING HANDOFF
SUFFICIENT` is available only after the expansion gate opened and the
confirmation cohort then showed B matching C within the frozen thresholds.
Any integrity, admission, missing-usage, or material seed-discordance condition
routes to `INCONCLUSIVE` before either negative label.
