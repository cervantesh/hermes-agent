# Issue #375 Fidelity Research — Amendment 006

Status: `FROZEN_HARNESS_REPAIR_AFTER_INVALID_PILOT`

Amendment ID: `IP375-FIDELITY-AMENDMENT-006-ANTHROPIC-SAMPLING-2026-09-03`

Parent protocol: `IP375-FIDELITY-EXECUTION-R1-2026-09-03 @ 78294319621e`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Trigger and observed evidence

The first authorized provider pilot began before this amendment. Its first
generation request received Anthropic HTTP 400 because the request specified
both `temperature` and `top_p`. The provider reports that this model accepts
only one of those controls. The harness quarantined all four pilot pairs,
recorded zero completed pairs, zero input/output tokens, and USD 0.00 cost.

The invalid pilot is preserved outside the repository. Its sanitized summary
has SHA-256
`3953d8e915c92093c81ba07c109156604a08f4be784d5284665115cc87071c6a`;
the sanitized failure receipt has SHA-256
`0933431aa8780a9cc8fae9baee0f34d198f9d9ffd136a9e759dab7eda52b8cdc`.
No transcript, extracted answer, judgment, or efficacy aggregate was observed.

## Decision

The direct Anthropic transport sends `temperature` and omits `top_p` for role
generation, extraction, and judging. The frozen logical setting remains
`top_p=1.0`, the neutral full-distribution setting; omission is its compatible
wire representation when `temperature` is supplied. Temperature, models,
prompts, sample, schedule, maximum output lengths, retry policy, judge, and
analysis remain unchanged.

## Evidence impact and rerun rule

The first pilot is invalid instrument evidence and is never pooled or used for
efficacy. A fresh pilot must run in a new output root with the same four task
IDs and sealed schedule. Only that fresh pilot can satisfy the conformance
gate. The user-authorized USD 10 ceiling remains cumulative; the invalid
attempt incurred no billed tokens or cost.

The repair is covered by a request-construction regression test that fails
when both sampling controls are emitted and passes when only `temperature` is
sent. This amendment is immutable after sealing; any further sampling-parameter
change requires another amendment and fresh observations.
