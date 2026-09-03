# Ownership Audit

Status: current-main audit for `SCR-V7-INITIAL-2026-09-02`

## Reference state

- Audit date: 2026-09-02
- Frozen Hermes reference: `593aa74c6182ce2e5e23bc102daaaae71710c05d`
- Fetched `origin/main`: `593aa74c6182ce2e5e23bc102daaaae71710c05d`
- Drift at audit time: none
- Issue under study: #377, open, `P3`, `needs-decision`

Issue #377's original premise predates current Hermes coordination paths. Its
claim that workers only have parent relay is no longer sufficient by itself:
Kanban workers can read task state and handoffs, use comments as a durable
cross-task channel, receive live operator comments through steering, and
preserve attachments/artifacts. The V7 baseline must exercise those paths.

## Existing Hermes mechanisms

| Mechanism | Current evidence | Consequence for V7 |
| --- | --- | --- |
| Parent result relay | `tools/delegate_tool.py` gives each child a fresh conversation and returns its summary/result to the parent. | Arm A; not the strongest available baseline. |
| Full task projection | `tools/kanban_tools.py::_handle_show` returns task, parents, children, comments, runs, and result state. | Required in Arm B when a worker can identify the task. |
| Worker startup projection | `hermes_cli/kanban_db.py::build_worker_context` includes parent handoffs, prior attempts, role history, and comments with explicit caps. | Measure injected volume; do not claim context is absent. |
| Durable cross-task notes | `kanban_comment` permits cross-task comments as the deliberate handoff channel. | Test before opening an active-write mechanism. |
| Live correction | New comments on a running task are polled and injected through agent steering. `delegate_task` also has scoped live steering. | A mutable need is not RED until these routes fail the observable contract. |
| Artifacts/attachments | Kanban completion preserves declared artifacts and task tools attach files/URLs. | Use for outputs too large or structured for a prose relay. |
| Isolation | Delegate control is scoped by parent identity/session lineage; delegated children cannot mutate Kanban directly. | Preserve these boundaries in every experimental adaptation. |

## Tracker ownership map

| Owner | Overlap | Why it does not own all of #377 / V7 | Disposition |
| --- | --- | --- | --- |
| #95561 — compact/minimal `kanban_show` and worker context | Direct owner for repeated full-context token cost. | It does not define shared writes, key permissions, or cross-backend state. | Track 1 must defer to #95561 if compact/delta retrieval clears the resource gate. |
| #4529 — persistent domain-owned file bus | Shared state across independent long-lived agents and sessions. | It explicitly distinguishes persistent team state from #377's ephemeral in-workflow state. | Related, not duplicate; do not absorb persistent-team scope. |
| #86898 — cross-session A2A messaging | Active request/reply between persistent sessions. | #377 concerns workers inside a workflow, not addressing long-lived sessions. | Related, separate owner. |
| #69560 — multi-node A2A coordination/shared project memory | Remote discovery, delegation, monitoring, and broad project memory. | This is a larger multi-node architecture, not a local shared-context primitive. | Track 6 must not reinvent its transport/control plane. |
| #101015 — cross-container Kanban assignee dispatch | Real remote fleet routing failure on a shared board. | It concerns eligibility/spawn routing, not worker context semantics. | Remote-track prerequisite/constraint, not a V7 success criterion. |
| #56656 — remote file-state coordination no-op | Real cross-agent write-safety failure on remote terminal backends. | It is an existing file registry defect with a focused proposed fix. | Track 5/6 must not duplicate it; use it as a known boundary. |
| #81984 — unreadable spill paths on remote backends | Large delegated output becomes unreachable because host paths leak into backend instructions. | It is path translation, not shared memory. | Resolve or control for it before interpreting remote retrieval failures. |
| #98958 — MCP agent identity/delegation | Identity and scoped claims for remote MCP writes. | It does not define local ephemeral shared-context semantics. | Relevant only if a future permission design reaches MCP calls. |
| PR #82157 — per-child memory/toolset boundary | Adds optional child memory and child toolset restrictions. | It shares the parent's persistent memory store, has no E2E proof, and does not provide ephemeral selective state. | Overlapping experiment/control; not a substitute for Track 2 or 3. |
| PR #83061 — Kanban parent-link handoff | Merged documentation/behavior supporting parent-linked work. | It strengthens the existing baseline rather than implementing a shared pool. | Include in Arm B. |

## Track adjudication before implementation

### Track 1 — context cost and volume

Enabled for harness construction. The first comparison is the strongest
current Hermes projection versus a compact/delta projection. If that clears
the frozen product gate, #95561 owns the smallest-footprint implementation.
No shared pool is justified by volume alone.

### Track 2 — selective key access

Enabled only for a RED witness search and harness construction. A valid witness
must require a declared subset and show a changed external outcome or frozen
resource threshold versus Arm B. Convenience, cleaner prompts, or fewer bytes
without the product gate are insufficient.

### Track 3 — isolation and permissions

Enabled for negative tests. A valid witness must demonstrate reachable
cross-workflow or cross-tenant visibility through a real Hermes path. Synthetic
access to a harness dictionary is not a product bug. Existing parent/session
ownership and delegated-child restrictions are controls to preserve.

### Track 4 — active writes

Closed pending a real workflow in which parent relay, Kanban comments,
attachments, and steering cannot express the needed update while the worker is
running. Do not build production write APIs before that witness exists.

### Track 5 — concurrency

Closed until Track 4 opens the writable gate. Known remote file-state defects
belong to #56656 and cannot be reused as evidence for a new shared-state layer.

### Track 6 — remote backends

Closed until a local mechanism demonstrates value. When opened, control for
#81984 path translation, #101015 dispatch ownership, and the larger A2A scope
in #69560 before attributing a failure to shared context.

## Smallest-footprint decision rule

For every RED witness, prefer the first existing owner or extension point that
satisfies the external contract. A new shared-context layer is admissible only
when all stronger current Hermes routes have been exercised, no focused owner
already covers the gap, and the candidate clears the frozen efficacy,
resource, isolation, and false-success gates.

