# Shared Context Research V7 — Second Corrected Repetition Protocol

Status: `FROZEN_PROSPECTIVE_NO_REPETITION_002_OBSERVATIONS`

Protocol ID: `SCR-V7-REPETITION-002-2026-09-03`

Parent design: `SCR-V7-INITIAL-2026-09-02`

Prior repetition: `SCR-V7-REPETITION-001-2026-09-03`

Hermes target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

This is a clean prospective repetition of only the two questions left
unresolved by Run 002. It repairs two demonstrated harness defects without
changing the parent hypotheses, cohorts, seeds, opaque inputs, external
oracles, or decision thresholds. Run 002 remains immutable, has disposition
`INCONCLUSIVE_PROTOCOL_IMPLEMENTATION`, and must not be pooled with this run.

## Decision value and kill conditions

- **Track 2:** determine whether the strongest ordinary Hermes worker route
  still has a valid selective-access RED after it can follow `kanban_show`
  spill references with the normal CLI file and terminal capabilities. If all
  three B-first sizes are exact, stop without confirmation and record
  `EXISTING HERMES MECHANISM SUFFICIENT`. Only a valid strict-oracle B failure
  may open confirmation.
- **Track 3:** determine whether both model cohorts can complete the frozen
  declared-parent positive control when the terminal tool instruction clearly
  targets the current worker. If either positive control is invalid or
  inexact, stop the policy inference at `INCONCLUSIVE`.

No result from this protocol can reopen Track 1 or authorize Tracks 4–6.

## Track 1 — not repeated

Run 002's all-records control showed the same resource advantage as its subset
case. The prospective control-artifact veto therefore closed Track 1 as
`INCONCLUSIVE` under this design. Additional provider observations cannot
change that disposition without a new research question and protocol.

## Track 2 — strongest existing Hermes baseline

The B arm uses the same real child task, worker startup context, opaque corpus,
`kanban_show` retrieval instruction, durable terminal outcome, strict JSON
oracle, sizes (`32`, `128`, `512`), cohort, and seed as the parent protocol.
Its enabled surface changes from the artificial `kanban`-only restriction to
the repository's ordinary `hermes-cli` toolset. At the pinned target this
surface includes `kanban_show`, `kanban_complete`, `terminal`, and `read_file`.
That lets the worker use the existing production recovery path when a complete
tool result spills to a local file.

The D arm remains tool-free and receives only the declared projection. A D
tool call invalidates the row. B is still scored from its durable task outcome;
D is scored from its final response.

The B-first gate runs in ascending size order and stops at the first invalid
row or first valid RED. An invalid row does not open confirmation. A valid RED
opens exactly eight paired confirmation observations at that size: two seeds,
two model cohorts, and arms B/D. `IMPLEMENTATION OPPORTUNITY` requires all four
D rows to be valid and exact and all four B rows to be valid failures.

## Track 3 — unambiguous current-worker completion

Track 3 preserves the two relationships, both model cohorts, seed, canary,
Kanban-only access surface, classification, and strict external oracle. The
prompt now instructs the model to call `kanban_complete` **without a
`task_id`**, so the tool defaults to the current worker task. This removes the
Run 002 ambiguity that caused Anthropic to pass the inspected owner task id to
the terminal operation. It does not change which task may be read or what
constitutes success.

Both declared-completed-parent controls must be valid and exact before the
unrelated-same-board rows support any reachability statement. Visible
unrelated rows remain `POLICY_UNADJUDICATED`, not a vulnerability finding.

## Observation budget and retention

- up to 3 Track 2 B-first observations;
- exactly 8 Track 2 confirmation observations only after a valid B-first RED;
- exactly 4 Track 3 observations;
- therefore at most 7 observations without expansion, or 15 with expansion.

The append-only journal is the source of truth. Any escaping exception writes
`ABORTED.json` with the exception class, message, and retained row count. An
aborted or protocol-invalid frame is preserved and is not silently repaired,
replaced, or pooled.

## Execution condition

This protocol and its executable harness may be built, tested, and sealed
without provider calls. A credentialed Run 003 requires a new explicit
authorization because the authorization used by Run 002 has been exhausted.
Before execution, verify the complete seal chain, exact target revision,
credential freshness, and absence of production changes outside the evaluation
package.

Any semantic change requires a new prospective amendment or protocol and fresh
observations. This file must not be edited after sealing.
