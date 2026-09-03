# V7 Run 001 disposition

Run: `v7-scored-20260903`

Target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

Disposition: `INCONCLUSIVE_PROTOCOL_IMPLEMENTATION`

The authorized runner completed and durably retained all 23 expected provider
observations. It then failed while building the terminal receipt with
`KeyError: case`. No observation will be retried, replaced, or pooled with a
future repetition.

The journal is complete, but it cannot answer the product hypotheses:

1. Every D observation executed Kanban tools even though the frozen protocol
   requires D to receive no Kanban surface. Setting `HERMES_KANBAN_TASK` for
   both arms activated the worker lifecycle and gave D a route to the full
   parent graph.
2. Track 1's all-records control was not exact in both families, so its frozen
   decision rule requires an inconclusive disposition.
3. Track 3's declared-parent positive control failed in both families. The
   unrelated-task probes therefore cannot support a permissions conclusion.
4. The terminal postprocessor treated the three B-first Track 2 boundary rows
   as Track 1 rows, then indexed a missing `case` field.
5. Real Kanban workers reported through `kanban_complete`, while the runner's
   oracle inspected only `final_response`. A corrected repetition must define
   and verify the real terminal outcome channel prospectively.

The B-first boundary produced exact recovery at 32 and 128 records and a
failure at 512, which correctly triggered the eight confirmation slots. That
is retained as a descriptive witness only; the contaminated D arm and failed
controls prevent an implementation adjudication.

The machine-readable audit reconstructs slot completeness and these failures
without reading or publishing opaque corpus values. The current authorization
cap has been exhausted; no corrected provider repetition may start without a
new explicit authorization.
