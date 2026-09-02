# Frozen V4 protocol: retain terminal fixture failures

Status: **FINAL BEFORE REMOTE SEAL**.

V4 inherits the complete V3 protocol at
`evals/shared_context_research_v3/PROTOCOL_FREEZE_V3.md`, including:

- target `c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf`;
- arms A/B/C and the fresh-process SQLite C treatment;
- four dependent fixtures and two controls;
- cohorts `haiku-s377`, `haiku-s378`, and `sonnet-s377`;
- the external workflow-success endpoint;
- resource thresholds and the bounded verdict language; and
- privacy, chronology, isolation, and public recomputation requirements.

The only amended rule is terminal-outcome retention:

1. Exit `0` records a completed fixture.
2. Exit `2` is reserved for a classified provider failure and permits one
   immediate retry. A second exit `2` is retained as invalid.
3. Exit `3` records a non-provider fixture failure immediately. It is never
   retried. The runner continues the remaining frozen slots.
4. Any worker-protocol failure that produces no parseable structured row stops
   the runner and makes the V4 package inconclusive. Before propagating the
   error, the runner atomically writes `ABORTED.json`; every later invocation
   with that label refuses to dispatch, so the missing row cannot be replaced.

Before each worker dispatch, the runner atomically writes `INFLIGHT.json`. It
removes the marker only after the structured row is flushed and `fsync`ed. A
resume may clear a stale marker only when the exact cohort/task row is already
parseable in the raw ledger; otherwise that label refuses further dispatch.

The public failure receipt is restricted to `exception_type`,
`failure_phase`, and `message_sha256`. Raw diagnostic text remains private.
Because an exception yields no complete admission receipt,
`producer_admitted=false` means “not established” on that invalid row; it does
not assert that the producer itself caused the failure.

V4 uses a new prospective source seal and remote GitHub timestamp. No V4
provider-backed preflight or observation may run before that publication.
The unscored two-fixture preflight must pass before scored dispatch; a terminal
failure in preflight stops the experiment and never creates a pass receipt.

V3 observations are historical evidence only. They are neither resumed nor
pooled with V4.
