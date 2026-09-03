# Issue #375 Fidelity Research — Amendment 004

Status: `FROZEN_PROSPECTIVE_AMENDMENT_NO_OBSERVATIONS`

Amendment ID: `IP375-FIDELITY-AMENDMENT-004-TRANSPORT-CAP-2026-09-03`

Parent input freeze: `IP375-FIDELITY-EXECUTION-R1-2026-09-03`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Clarification

`frozen_inputs/CALL_CAP.json` counts 8,860 logical model completions. It does
not count retry attempts. The execution protocol permits at most three
transport attempts per logical completion: the initial attempt and two
retries for eligible transport, rate-limit, or provider 5xx failures.

Therefore the hard transport-attempt ceiling is 26,580. Invalid model output,
parse failures, protocol violations, and content-policy outcomes are not
retryable transport failures.

This amendment adds a missing resource distinction; it does not change the
sample, prompts, schedule, logical call cap, or scientific endpoint.

## Change control

This artifact is immutable after sealing. More attempts require a new
prospective protocol and fresh observations.
