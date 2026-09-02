# Ownership and current-capability audit

Audit date: 2026-09-01  
Pinned upstream: `180291162ff4df0d42b5dc4fecd08005cf7cebf9`

## Issue #377 premise

Issue #377 proposes workflow-scoped shared memory because dependent children
otherwise route context through a parent, potentially adding tokens, latency,
and information loss. Its implementation sketch depends on the older #344
workflow-DAG roadmap.

The premise is now only partially current. Since the issue was written, Hermes
has gained durable Kanban task coordination and a documented parent-link
handoff. The question is therefore not whether *any* non-parent handoff exists;
it is whether a scratchpad improves a workflow outcome that current handoffs
cannot.

## Existing mechanisms on current main

### Shared artifact/file

Dependent workers with access to one workspace can pass an authoritative
artifact directly. This is the lowest-footprint existing mechanism, but it
does not establish a cross-host guarantee.

### Kanban parent-link handoff

Current `hermes_cli/kanban_db.py` contains:

- `create_task()` at line 3169;
- `complete_task()` at line 5363;
- `build_worker_context()` at line 11015;
- a 4 KiB per-field context cap at line 481; and
- the `## Parent task results` projection at line 11163.

PR #83061 documented and live-tested the contract: a child of a completed card
can become ready immediately, and the child's worker context carries the
parent's completion summary and metadata. The docs also describe those values
as point-in-time handoffs. This is the strongest current control for arm B.

### Direct `delegate_task`

`delegate_task()` remains synchronous or background fan-out, not a workflow
scratchpad. A parent can relay child summaries, which is arm A rather than an
absence of functionality.

## Related work disposition

| Item | Status | Relationship to #377 experiment |
|---|---|---|
| #344 | closed | older umbrella roadmap; not proof that scratchpad value remains |
| #71794 | closed, unmerged | named credential profiles; not shared context |
| #82157 | open/conflicting | child memory/toolset permissions; persistent memory, not workflow-scoped immutable handoff |
| #83061 | merged | documents the real Kanban parent-link handoff used in arm B |
| #83376 | closed | records context-handoff-over-shared-state as an intentional current pattern |

Searches over open PR titles and bodies found memory-provider and session
sharing work, but no current PR that implements the bounded workflow-scoped
scratchpad proposed by #377. This is an ownership snapshot, not a permanent
claim; it must be refreshed before any future implementation proposal.

## What remains genuinely unowned

No accepted contract currently promises all of the following together:

- explicit workflow namespace;
- declared per-step reads;
- immutable upstream authority;
- atomic publication;
- cross-workspace availability; and
- measured advantage over Kanban/artifact handoff.

The first five describe a possible mechanism. The sixth is the missing product
evidence. This study addresses the evidence question only.

## Audit conclusion

Issue #377 is not ready for implementation from its original rationale alone.
It is ready for a bounded comparative experiment. Arm B must include the real
Kanban parent-link path; comparing only against parent prose would be a stale
and unfair baseline.
