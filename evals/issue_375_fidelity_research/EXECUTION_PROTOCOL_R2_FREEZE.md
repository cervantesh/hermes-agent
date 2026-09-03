# Issue #375 Fidelity Research — Lane R Execution Protocol R2

Status: `FROZEN_PROSPECTIVE_NO_R2_OBSERVATIONS`

Protocol ID: `IP375-FIDELITY-EXECUTION-R2-2026-09-03`

Parent protocol: `IP375-FIDELITY-EXECUTION-R1-2026-09-03 @ 78294319621e`

Parent amendments: 001–007 as listed by `ACTIVE_FREEZE.json` at commit
`3a637ae4d6536f1cf69cd4e813198f23df1ad26f`.

Frozen on: 2026-09-03 (America/Santo_Domingo)

## 1. Question this version can change

Can the direct-provider harness demonstrate end-to-end conformance when the
unchanged CAMEL Appendix H judge occasionally violates its requested numeric
output contract, without repairing, retrying, scoring, or selectively
regenerating that content?

R2 does not change or answer the scientific efficacy question. It changes only
the unscored provider-pilot gate and the classification needed to distinguish
an expected judge-output quarantine from a harness or infrastructure failure.

## 2. Preserved contracts

R2 preserves the R1 source revisions, dataset, 100-task scored manifest and
schedule, arms, historical priming, 40-message horizon, termination rules,
token accounting, prompt wording and hashes after Amendment 007, models,
temperatures, extraction, blinded judge ordering, `[1,10]` score range,
no-content-retry rule, scored-run validity gate, analysis, privacy rules, and
scientific attribution limits.

The exact models remain:

- generation and extraction: `claude-haiku-4-5-20251001`;
- judge: `claude-sonnet-4-5-20250929`.

## 3. Fresh pilot cohort

The R2 pilot contains 20 distinct task IDs selected from the pinned AI Society
dataset after excluding every ID in the frozen 100-task scored manifest. Rank
the remaining IDs by SHA-256 of
`IP375-FIDELITY-R2-PILOT|<stable-record-id>` and select the first 20. Generate
the paired order with seed `IP375-FIDELITY-R2-PILOT-SCHEDULE`; no reversal
judgment runs in the pilot. Seal manifest, schedule, dataset digest, exclusions,
and artifact hashes before provider execution.

These 20 tasks are conformance-only, never efficacy observations, never pooled
with R1 or the scored sample, and never used to choose a treatment.

## 4. Typed judge-output quarantine

The deterministic parser distinguishes:

- `JudgeOutputFormatError`: the first line is not exactly two numeric values;
- `JudgeScoreRangeError`: two values parse, but either is outside `[1,10]`.

Both are provider-content protocol violations. They are not transport-retried,
repaired, clamped, rescored, or selectively regenerated. Their task pair is
quarantined and execution continues to the next fresh pilot task.

Every other unresolved exception is a disallowed pilot failure and stops the
pilot. This includes source/seal drift, authorization or identity failure,
budget exhaustion, generation or extraction failure, malformed persistence,
and transport failure after the frozen retries.

## 5. Conformance predicate

The R2 pilot passes only when all of the following hold:

1. all 20 selected task IDs reach either `COMPLETE` or a typed judge-output
   quarantine;
2. at least 18 task pairs are `COMPLETE`;
3. at most two task pairs have a typed judge-output quarantine;
4. no disallowed quarantine, model-identity breach, missing task, source drift,
   or harness/infrastructure failure occurs;
5. both generation arms, extraction, judging, persistence, resume, sanitized
   receipt, and quarantine paths remain covered by executable tests and the
   provider run; and
6. no aggregate wins, scores, arm outcomes, or efficacy comparison from the
   pilot is inspected or reported.

The 18/20 threshold is frozen before selecting or observing the R2 pilot and
matches the scored protocol's minimum 90/100 valid-pair fraction. Passing it
only unlocks consideration of a separately authorized scored run.

## 6. Resource ceilings and authorization

The R2 pilot permits at most 20 paired observations, 1,700 logical
completions, 5,100 transport attempts, 3,000,000 input tokens, 1,500,000 output
tokens, three wall-clock hours, and USD 5.00 of additional first-party API
spend. The prior R1 pilot cost of USD 1.062046 remains reported separately and
is not reset or hidden.

No R2 provider call is authorized by this freeze. Before execution, the user
must approve the exact R2 protocol digest, models, 20-observation limit, and
these ceilings in a new local authorization artifact. The scored run retains
its R1 maximum ceilings but requires a later authorization based on the R2
pilot receipt and projected exposure.

## 7. Kill conditions and allowed disposition

Stop R2 without a scored run if the pilot fails its conformance predicate, a
new harness defect appears, the exact models are unavailable or substituted,
the source/seal frame drifts, or an authorized resource limit is reached. A
harness defect requires another prospective protocol version and a fresh
cohort; a content quarantine within the frozen allowance does not.

The only R2 pilot dispositions are `CONFORMANCE_PASS` and
`INCONCLUSIVE_PROTOCOL_OR_INFRASTRUCTURE`. Neither is an efficacy result or a
product-adoption recommendation.

This document is immutable after sealing.
