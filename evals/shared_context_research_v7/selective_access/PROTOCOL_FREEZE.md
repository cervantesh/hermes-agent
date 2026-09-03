# Track 2 Protocol Freeze — Selective Key Access

Parent freeze: `SCR-V7-INITIAL-2026-09-02`

Target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

## Hypothesis

At some increasing opaque payload size, the strongest current Hermes consumer
may fail to recover a consumer-selected tail record while a declared-key
projection remains exact.

## B-first gate

Run only `B` with Anthropic `claude-sonnet-4-6`, seed 377, 128-byte opaque
values, and record counts 32, 128, then 512. The required key is always the
last record and is absent from the instructions. `B` receives the real child
startup projection and can call real `kanban_show(parent_id)`.

Stop at the first strict external-oracle failure. If all three are exact,
dispose as `EXISTING HERMES MECHANISM SUFFICIENT`; do not run `D` and do not
spend the confirmation cohort.

## Conditional confirmation

Only after a B-first RED, run paired randomized `B`/`D` observations at that
same record count for seeds 377 and 378 in both frozen model cohorts. `D` is a
harness-only declared-key projection, not CAMEL Workforce behavior.

An implementation opportunity requires repeated exact `D` success and
repeated `B` failure across both seeds and both model families, with valid
provider receipts and no hidden source access. A one-off model failure is
`INCONCLUSIVE`, not product RED.

