# Issue #375 Fidelity Research — Amendment 005

Status: `FROZEN_PROSPECTIVE_AMENDMENT_NO_OBSERVATIONS`

Amendment ID: `IP375-FIDELITY-AMENDMENT-005-RUNTIME-IDENTITY-2026-09-03`

Parent protocol: `IP375-FIDELITY-EXECUTION-R1-2026-09-03 @ 78294319621e`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Decision

The execution environment must record and validate versions from the imported
runtime modules, not only from Python distribution metadata. The required
runtime identities are:

- `anthropic.__version__ == 0.87.0`;
- `tiktoken.__version__ == 0.12.0`; and
- `scipy.__version__ == 1.17.1`.

The preflight also records the installed distribution metadata version. A
metadata/runtime mismatch is an environment warning and must be resolved or
explicitly accepted before provider execution; it may not be represented as
the runtime version.

## Reason

The provider-free preflight found stale parallel `anthropic` dist-info
directories: package metadata reported `0.120.0`, while Python imported the
`0.87.0` module. Provider behavior is determined by imported code.

## Scope and change control

No model, prompt, sample, endpoint, or analysis rule changes. This amendment
is immutable after sealing; a different runtime version requires an evidence
refresh before observations.
