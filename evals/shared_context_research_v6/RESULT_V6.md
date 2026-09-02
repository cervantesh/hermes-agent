# V6 result: current B recovered beyond the bounded preview

## Decision

The prospectively frozen B-first gate did **not** pass, so the A/B/C comparison
was not run.

Both B observations produced the exact externally verified result:

| Fixture | Source size | Tail in initial projection | Exact result |
|---|---:|---:|---:|
| `cap_below_control` | 3,613 chars | yes | yes |
| `cap_above_tail_dependency` | 5,917 chars | no | yes |

The above-cap worker called `kanban_show` on its own task, inspected the empty
attachment route, and then called `kanban_show` on the linked parent task. The
parent lookup exposes the task's complete `result` and every run's complete
`summary`; unlike `build_worker_context()`, `_handle_show()` does not apply the
4,096-character per-field projection cap. The producer workspace had already
been removed, no attachment carried the source, and the required opaque value
was absent from the child workspace and instructions.

The row's frozen `arm.ok` is false only because the earlier research scope
classified foreign-task `kanban_show` and `kanban_attachments` as violations.
That classification is useful for testing a no-foreign-read isolation model,
but it must not be confused with product failure: these tools were actually
available to the worker, and its exact output passed the external oracle.

## Interpretation

The 4,096-character startup projection is real, but it did not establish an
unrecoverable information-loss case under the current Kanban worker surface.
Current Hermes already provides an on-demand, durable parent-result lookup that
acted as shared workflow context in this fixture. Therefore this mechanism does
not justify a new C implementation on correctness grounds.

This result does not establish that the current route is optimal. The above-cap
observation used more exploratory calls and a large prompt footprint. It also
does not cover namespace policy, remote backends, a missing/disabled Kanban
surface, arbitrary payload size, concurrency, or active shared writes. Those
are separate hypotheses and require their own reachable RED witness before any
implementation proposal.

## Method notes

V5 is separately archived as inconclusive after an inherited evidence helper
selected an auxiliary SQLite file without a `sessions` table. V6 fixed only
session-store discovery and subprocess-failure retention, published a new
remote seal, and repeated every gate slot from scratch. V5 and its unscored
diagnostic were not pooled.

Private provider rows remain excluded from Git. The public receipt contains
only task identifiers, booleans, source sizes, tool counts, hashes, and the
bounded decision.
