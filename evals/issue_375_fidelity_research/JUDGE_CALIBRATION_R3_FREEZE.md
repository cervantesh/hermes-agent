# Issue #375 Fidelity Research — Judge Calibration R3

Status: `FROZEN_DESIGN_NO_IMPLEMENTATION_OR_PROVIDER_OBSERVATIONS`

Protocol ID: `IP375-JUDGE-CALIBRATION-R3-2026-09-03`

Parent execution protocol:
`IP375-FIDELITY-EXECUTION-R2-2026-09-03 @ bc5dadff484c`

Parent disposition receipt:
`PILOT_R2_CONFORMANCE_RECEIPT.json @ ecfdc1ce7a72`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## 1. Decision this protocol can support

R3 asks whether a paper-family judge can execute CAMEL Appendix H's unchanged
pairwise evaluation contract reliably enough to support the already frozen
100-task comparison. It calibrates the measurement instrument; it does not
measure whether the original or ablated inception prompt is better.

R3 may unlock a separately authorized scored run only if its fidelity track
passes every frozen gate below. It cannot authorize provider calls by itself.

## 2. Evidence entering the freeze

- Appendix H requests exactly two first-line scores on a scale of 1 to 10.
- R2 attempted 12 of 20 fresh task pairs: nine completed and three produced
  `JudgeScoreRangeError` under `claude-sonnet-4-5-20250929`.
- R2 recorded no transport retry or model-identity failure.
- The third range violation triggered the prospectively frozen stop rule; the
  remaining eight tasks were not run.
- R2 preserved only the error category. The invalid raw judge line and parsed
  numeric values were discarded before persistence, so whether the violations
  were zeroes or values above ten is not recoverable.
- After R2 was closed, one completed public receipt was accidentally displayed
  during schema inspection. That single exposed outcome is excluded from all
  R3 choices and R2 remains ineligible for efficacy analysis or pooling.

## 3. Fidelity boundary and judge tracks

The paper identifies its evaluator only as GPT-4 and does not provide an API
snapshot. The closest still-documented pinned historical snapshot is
`gpt-4-0613`; current OpenAI documentation marks it deprecated. R3 therefore
defines:

- **Track F — fidelity gate:** `gpt-4-0613`, exact model identity required;
- **Track C — cross-family control:** `claude-sonnet-4-5-20250929`, retained to
  measure whether R2's compliance problem repeats on a fresh cohort.

Both tracks receive the exact frozen Appendix H system message, evaluation
template, instruction, temperature zero, and the same answer order. No JSON
schema, tool call, response-format constraint, corrective suffix, repair,
clamping, score normalization, or content retry is permitted.

Track C cannot unlock a paper-fidelity scored run. If Track F is unavailable,
substituted, or fails, the R3 disposition is inconclusive even if Track C
passes. A later product-oriented evaluation may use another model only under a
separate protocol and a narrower attribution claim.

## 4. Fresh calibration cohort

Select 30 distinct AI Society task IDs from the pinned dataset after excluding:

1. all 100 IDs in the frozen scored manifest;
2. all four R1 pilot IDs; and
3. all 20 R2 pilot IDs.

Rank remaining IDs by SHA-256 of
`IP375-JUDGE-CALIBRATION-R3|<stable-record-id>` and take the first 30. Generate
the order schedule with seed `IP375-JUDGE-CALIBRATION-R3-SCHEDULE`. Seal the
manifest, exclusions, schedule, source digests, and effective prompts before
any provider call.

Each task runs the existing original and ablated generation arms once with
`claude-haiku-4-5-20251001`, followed by the unchanged solution extraction.
Every answer pair is then evaluated by each judge twice: once in the sealed
order and once in the reversed order. Generation artifacts are shared across
judge tracks; they are never regenerated selectively for a judge failure.

These 30 tasks are calibration-only. They are not replacements for missing R2
tasks, are never added to the 100-task scored sample, and contribute no efficacy
estimate.

## 5. Required harness properties

R3 implementation must be proved provider-free before authorization:

1. atomically checkpoint both generated transcripts and extracted solutions
   before the first judge request;
2. atomically persist the raw judge response privately before parsing it;
3. record publicly only response hash, length, returned model, usage, latency,
   parse category, and whether the reversal outcome agrees;
4. on numeric range failure, preserve the parsed numeric pair privately without
   mapping or displaying it against arm identity;
5. distinguish format, range, transport, identity, budget, and persistence
   failures with typed causes;
6. resume without regenerating a completed phase or repeating a completed judge
   request;
7. keep credentials, raw prompts, answers, scores, task text, and account
   identity outside the repository; and
8. prevent summaries and progress output from exposing arm scores, winners, or
   aggregate efficacy.

Executable negative tests must mutate the sealed cohort, order, prompt digest,
model identity, phase checkpoint, and authorization. Each mutation must block
provider execution or quarantine the affected observation as specified.

## 6. Calibration gates

R3 reaches `FIDELITY_JUDGE_CONFORMANCE_PASS` only when all are true:

- all 30 generation/extraction pairs reach their durable judge-ready checkpoint;
- Track F returns the exact requested model on every call;
- all 60 Track F judgments have exactly two first-line numeric scores, both in
  `[1,10]`;
- Track F's winner classification agrees after order reversal on at least 27
  of 30 pairs;
- no Track F transport, budget, persistence, source, seal, or resume failure
  occurs; and
- no score, winner, arm aggregate, or efficacy comparison is inspected.

The 27/30 reversal threshold is frozen as a 90% minimum agreement target for a
measurement instrument. Track C reports the same compliance metrics but does
not participate in the pass decision. No candidate is selected according to
which arm it favors.

Any invalid Track F judgment fails R3; it is preserved, not repaired. Any
missing task, selective regeneration, post-observation prompt change, or model
substitution also fails R3.

## 7. Resource ceilings and preflight

An eventual R3 authorization may permit at most:

- 30 generated answer pairs;
- 120 judge requests, including reversals;
- 2,700 logical completions and 8,100 transport attempts;
- 6,000,000 input tokens and 3,000,000 output tokens;
- four wall-clock hours; and
- USD 20.00 additional first-party API spend.

The USD 20 ceiling is a kill limit, not a forecast. It accounts for the high
published token price of the deprecated GPT-4 snapshot plus fresh generation.
Before authorization, preflight must verify access to both exact model IDs with
metadata-only or zero-generation checks that incur no billable completion when
the provider supports them. Lack of access stops R3 before generation.

The authorization must name both providers, both exact model IDs, the protocol
digest, the 30-task cohort digest, and every ceiling. R2 authorization is not
valid for R3. The previously exposed Anthropic credential must be rotated; no
credential may be pasted into a repository artifact.

## 8. Dispositions

R3 has only these terminal dispositions:

- `FIDELITY_JUDGE_CONFORMANCE_PASS`;
- `INCONCLUSIVE_FIDELITY_JUDGE_UNAVAILABLE`;
- `INCONCLUSIVE_JUDGE_PROTOCOL_NONCONFORMANCE`; or
- `INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE`.

Only the first permits asking for a new authorization for the scored study.
None is evidence that either inception prompt is superior.

This document is immutable after sealing. Implementation defects require a
separate prospective amendment before any provider observation. Changes to
models, cohort, prompts, gates, or analysis require a new protocol version.
