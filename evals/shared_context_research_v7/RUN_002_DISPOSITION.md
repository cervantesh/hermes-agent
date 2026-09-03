# V7 Run 002 disposition

Run: `v7-repetition-001-20260903`

Protocol: `SCR-V7-REPETITION-001-2026-09-03`

Target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

Overall disposition: `INCONCLUSIVE_PROTOCOL_IMPLEMENTATION`

The corrected repetition completed all 23 authorized observations and wrote a
terminal receipt. Its journal is complete, canonical token accounting holds,
and every `D` observation was tool-free. Run 001's tool contamination and
postprocessor defects did not recur.

## Track dispositions

### Track 1 — `INCONCLUSIVE`

Both arms were exact in both cohorts, and the subset projection cleared the
resource threshold. The all-records control, however, showed essentially the
same direction of advantage in both cohorts. This triggers the prospectively
frozen control-artifact veto. The observation compares a one-call, tool-free
inline projection with a multi-call Kanban worker lifecycle; it does not isolate
selective retrieval as the source of the resource difference.

Track 1 is closed as `INCONCLUSIVE` under this design. It must not be used to
claim an implementation opportunity or routed to #95561 as demonstrated value.

### Track 2 — `INCONCLUSIVE`

The B-first gate was exact at 32 and 128 records and failed at 512. Conditional
confirmation then produced four valid exact `D` successes and four valid `B`
failures across both seeds and model cohorts. The generated receipt therefore
recorded `IMPLEMENTATION OPPORTUNITY` under its immediate rules.

The completion audit found that this result does not satisfy the parent design's
strongest-current-Hermes baseline. The runner passed only the `kanban` toolset
to `B`. At 512 records, `kanban_show` spilled its complete response to a local
file, while the model surface lacked both `terminal` and `read_file`. A normal
CLI Kanban worker's configured surface includes those tools. The observed RED
therefore proves failure for a deliberately restricted worker, not failure of
all existing reachable Hermes mechanisms.

The receipt remains immutable evidence of what its runner calculated, but the
research adjudication supersedes that candidate disposition with
`INCONCLUSIVE`. No #377 implementation is authorized.

### Track 3 — `INCONCLUSIVE`

OpenAI produced valid exact outcomes for the declared-parent positive control
and the unrelated-same-board probe. Anthropic invoked the Kanban completion
tool with an explicit owner task id, which the worker-scope guard correctly rejected; both
Anthropic rows consequently lacked a durable outcome. Because both family-level
positive controls did not pass, no permissions or vulnerability conclusion is
allowed.

The next protocol may clarify that `kanban_complete` must omit `task_id` and
default to the current worker task. This changes no access hypothesis or oracle,
but requires fresh Track 3 observations.

## Reuse and next gate

Run 002 is preserved and must not be pooled with a further repetition. Track 1
needs no additional provider observations because its own control closed the
claim as inconclusive. A prospective correction should:

1. repeat Track 2 with the strongest normal Hermes worker surface, including
   `terminal` and `read_file`;
2. open confirmation only after a valid B-first RED under that surface; and
3. repeat Track 3 with an unambiguous current-task completion instruction.

That requires at most 15 new observations: 3 Track 2 B-first, conditionally 8
Track 2 confirmation, and 4 Track 3. Tracks 4–6 remain closed. No provider call
may begin without separate authorization.
