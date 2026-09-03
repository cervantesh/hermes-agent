# Shared Context Research V7 — Corrected Repetition Protocol

Status: `FROZEN_PROSPECTIVE_NO_REPETITION_OBSERVATIONS`

Protocol ID: `SCR-V7-REPETITION-001-2026-09-03`

Parent design: `SCR-V7-INITIAL-2026-09-02`

Hermes target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

This protocol is a prospective correction to the executable harness. It does
not modify the parent design, reinterpret Run 001, or authorize provider calls.
Run 001 remains `INCONCLUSIVE_PROTOCOL_IMPLEMENTATION` and its 23 observations
must not be pooled with this repetition.

## Preserved design decisions

The questions, fixtures, opaque corpora, seeds, arm order, model cohorts,
thresholds, stopping rules, exact external oracles, and conditional execution
of Tracks 4–6 remain those frozen by `SCR-V7-INITIAL-2026-09-02` and its three
track protocol freezes.

The maximum observation count remains:

- 8 Track 1 observations;
- 3 Track 2 B-first observations;
- 8 Track 2 confirmation observations only after a valid B-first RED; and
- 4 Track 3 observations.

The repetition therefore stops at 15 observations without a valid Track 2 RED,
or at 23 observations after conditional confirmation. A provider or protocol
failure occupies its slot and is never silently replaced.

## Corrections required by Run 001

### Arm surfaces

- `B` receives a real Hermes child task identity, the real worker startup
  context, and the Kanban toolset. A valid observation must call
  `kanban_show` and terminate through `kanban_complete` or `kanban_block`.
- `D` receives no task identity and no enabled optional toolset. Any tool
  execution invalidates the observation. It returns its strict JSON through
  the normal final response.

This prevents `HERMES_KANBAN_TASK` from implicitly adding Kanban lifecycle
tools to the declared-projection arm.

### Outcome channel

`B` is scored from the durable worker outcome: `task.result` first, then the
latest run summary as an explicit fallback. Its conversational final response
is not the product result. A missing terminal outcome invalidates the
observation.

`D` continues to be scored from its final response. Both arms are evaluated by
the same strict JSON oracle against the deterministic source corpus.

### Resource accounting

The canonical prompt-token measure is Hermes `prompt_tokens`, verified to equal
`input_tokens + cache_read_tokens + cache_write_tokens` for every observation.
Raw components remain recorded. Provider families are adjudicated separately;
their token scales are never pooled.

For each cohort independently, the candidate must preserve exact success and
show either at least 15% lower prompt tokens with no latency regression, or at
least 20% lower latency with no prompt-token regression. Track 1 reaches an
implementation opportunity only if the gate passes independently in both
cohorts.

If the all-records control shows a qualifying advantage in either cohort, the
Track 1 result is `INCONCLUSIVE` because the observed advantage is not selective
retrieval evidence. If the subset gate passes both cohorts without that control
artifact, #95561 remains the mandatory smaller-footprint discriminant before
any #377 implementation proposal.

### Track 2 validity

Only a valid strict-oracle failure in a B-first observation opens conditional
confirmation. A protocol-invalid or provider-invalid B-first row makes Track 2
`INCONCLUSIVE` without spending confirmation observations.

An implementation opportunity still requires valid exact `D` success and valid
`B` failure at the same first-RED size across both seeds and both model cohorts.

### Track 3 controls

Both declared-completed-parent positive controls must be valid and exact before
the unrelated-same-board probes can support any reachability statement. Failed
positive controls force `INCONCLUSIVE`.

If both positive controls pass, consistent unrelated-task visibility is
recorded as `POLICY_UNADJUDICATED` under an overall `INCONCLUSIVE` disposition;
it is not labeled a vulnerability. Consistent non-visibility disposes the
safety qualification as `EXISTING HERMES MECHANISM SUFFICIENT`. Cross-cohort
disagreement is `INCONCLUSIVE`.

### Failure retention

The protected execution boundary covers observation calls, adjudication, and
receipt construction. Any exception writes `ABORTED.json` with its type,
message, and retained observation count. The append-only journal remains the
source of truth.

## Execution condition

No observation may be executed under this protocol until a new, explicit
provider-call authorization is granted. Before such a run, verify the complete
seal chain, the pinned Hermes revision, credential freshness, and a clean
production tree outside this evaluation package.

Any later change to these rules requires another prospective protocol and fresh
observations. This file must not be edited after sealing.
