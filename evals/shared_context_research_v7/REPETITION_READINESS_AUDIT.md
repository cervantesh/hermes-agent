# Corrected repetition readiness audit

Audit date: 2026-09-03

Parent design: `SCR-V7-INITIAL-2026-09-02`

Corrected protocol: `SCR-V7-REPETITION-001-2026-09-03`

Status: `READY_FOR_A_SEPARATELY_AUTHORIZED_REPETITION`

## Run 001 disposition

Run 001 consumed all 23 authorized provider observations. Its append-only
journal is complete, but its only permitted disposition is
`INCONCLUSIVE_PROTOCOL_IMPLEMENTATION`. It is preserved and must not be pooled
with a corrected repetition.

No product conclusion about CAMEL-derived shared context, selective retrieval,
or Hermes #377 is supported by Run 001.

## Defect closure matrix

| Run 001 defect | Corrected evidence | Status |
| --- | --- | --- |
| `D` inherited Kanban lifecycle tools through `HERMES_KANBAN_TASK` | `_task_scope(None)` clears the identity; `D` receives no optional toolset; any tool execution invalidates the row; executable test asserts the environment and surface | Closed |
| `B` was scored from conversational `final_response` instead of the worker outcome | `read_worker_outcome()` reads `task.result`, then an explicit latest-run fallback; missing durable output invalidates the row; real isolated-DB test scores `task.result` | Closed |
| Resource accounting omitted cache writes and mixed provider scales | Runtime requires canonical `prompt_tokens == input + cache_read + cache_write`; decisions are made independently for each cohort | Closed |
| The all-records control could not veto a selective-retrieval claim | Any qualifying control advantage in either cohort forces `INCONCLUSIVE`; test covers the veto | Closed |
| Invalid B-first observations could trigger confirmation | Only a valid strict-oracle RED sets `confirmation_allowed`; test proves invalid rows stop without expansion | Closed |
| Track 3 emitted a policy conclusion despite failed positive controls | Both family-level positive controls must be valid and exact; otherwise disposition is `INCONCLUSIVE`; test covers the failure | Closed |
| Receipt construction failed outside the protected evidence boundary | Observation, adjudication, and receipt construction share one protected boundary; postprocessing failures write `ABORTED.json` with the retained count | Closed |
| Maximum observation path was implicit | Tests prove the normal stop at 15 and the conditional maximum at 23 | Closed |

## Integrity and verification

- The original design SHA-256 remains
  `7de472e9de934cac0a5041defb3ea455d4129118969c3b830b8a77d93c201787`.
- The worktree remains pinned to Hermes
  `593aa74c6182ce2e5e23bc102daaaae71710c05d`.
- The original protocol, both execution amendments, Run 001 audit, and corrected
  repetition protocol seals all verify against current bytes.
- The full evaluation package passes 57 tests, Ruff lint, and Ruff formatting.
- The corrected repetition subset passes 12 focused tests.
- No production Hermes file is modified.
- No corrected-repetition provider observation exists.
- A zero-call credential preflight at `2026-09-03T03:55:33.5774446+00:00`
  found an Anthropic credential and a Codex access token with at least the
  required 30-minute lifetime. This is point-in-time evidence and must be
  repeated immediately before execution.

## Remaining work

The next evidence-producing action is a fresh corrected repetition. It requires
a new explicit authorization because the prior limit of 23 provider
observations was exhausted by Run 001. Under the corrected protocol it will use
15 observations unless a valid Track 2 B-first RED opens the eight confirmation
observations, for a maximum of 23.

Only valid corrected observations can adjudicate Tracks 1–3. Tracks 4–6 remain
closed unless the frozen gates are opened by those results. A final research
report or implementation-ready specification would be premature before that
repetition.
