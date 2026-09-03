# Issue #375 Fidelity Research — Judge Calibration R4

Status: `FROZEN_DESIGN_NO_PROVIDER_OBSERVATIONS`

Protocol ID: `IP375-JUDGE-CALIBRATION-R4-2026-09-03`

Predecessor: `IP375-JUDGE-CALIBRATION-R3-2026-09-03`

## 1. Decision this protocol can support

R4 is a clean repetition of the R3 measurement-instrument calibration after
R3 exposed harness defects. It asks whether the paper-family judge can execute
CAMEL Appendix H's unchanged pairwise evaluation contract reliably enough to
support the already frozen 100-task comparison.

R4 does not estimate prompt efficacy, repair R3, pool R3 observations, or
authorize the scored study. A passing fidelity track only permits requesting a
separate authorization for that study.

## 2. Evidence and contamination boundary

R3 terminated as `INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE`: nine fixtures
reached `JUDGE_READY`, one fixture returned no usable text block, one request
was interrupted in flight, and no judge request occurred. All 30 R3 task IDs
are nevertheless considered observed and are excluded from R4.

R4 must select 30 fresh AI Society task IDs after excluding every ID from the
100-task scored frame, R1, R2, and R3. Rank the remaining records by SHA-256 of
`IP375-JUDGE-CALIBRATION-R4|<stable-record-id>` and take the first 30. Generate
the schedule with seed `IP375-JUDGE-CALIBRATION-R4-SCHEDULE`. The cohort,
schedule, source receipts, effective prompts, protocol digest, and repaired
harness revision must be sealed before any provider call.

R4 inherits, without alteration, these source identities:

- AI Society dataset revision
  `a493cd1636808cbe3cf2389dec79471a1db9e6bc`;
- paper-era CAMEL revision
  `c402032a7f7cd27e196356fbcf413c521a8cb4ca`;
- arXiv v2 PDF SHA-256
  `926c73c2ae9f9abc7612ab58373e428476f4de55db78646ed59de09810db7777`;
- arXiv v2 source SHA-256
  `232dc85336d51948808effa9590087b47ccdb7e4baa364b39120743da050faf2`;
- amended source-prompt receipt SHA-256
  `d241da64de45ae148967288e4e25eafa404410403ff7b154d405cead47727590`.

The input seal must bind the dataset bytes and the effective prompt artifact.
Any source or prompt-construction difference requires a new protocol rather
than a locally valid but semantically different R4 seal.

## 3. Fixed intervention and models

R4 retains R3's intervention and exact model identities:

- generation and extraction: `claude-haiku-4-5-20251001`;
- Track F, fidelity gate: `gpt-4-0613`;
- Track C, cross-family control: `claude-sonnet-4-5-20250929`.

Both judge tracks receive CAMEL Appendix H's unchanged system message,
evaluation template, instruction, temperature zero, and sealed answer order,
then the reverse order. No structured-output constraint, corrective suffix,
repair, clamping, normalization, or retry on content is permitted. Transport
retries remain bounded exactly as in R3 and never follow a completed response.

## 4. Sequential execution and stopping

Execution is deliberately sequential:

1. Prepare and durably checkpoint all 30 generation/extraction fixtures.
2. Stop on the first fixture that is not `JUDGE_READY`.
3. Run all Track F forward and reverse judgments.
4. Stop on the first invalid, transport, identity, persistence, or budget
   outcome in Track F. Stop early if 27 reversal agreements become
   mathematically unreachable.
5. Only after Track F satisfies every gate, run Track C forward and reverse.
6. Stop Track C on its first terminal outcome and report it independently.

The executor never regenerates a completed fixture or repeats a completed
judge response. An interrupted in-flight operation has unknown outcome and is
not retried.

Before the first provider call, the executor atomically creates a durable run
identity in the external output root. Every new start or resume must verify its
protocol digest, input-seal digest, harness commit, source digests, providers,
model IDs, and limits against the current authorization. A non-empty output
root without that exact identity is rejected. Checkpoints are never accepted
by task ID alone across evidence frames.

## 5. Measurement gates and dispositions

Track F passes only if:

- all 30 fixtures are `JUDGE_READY`;
- all 60 judgments return the exact requested model;
- all 60 judgments contain exactly two first-line numeric scores in `[1,10]`;
- at least 27 of 30 winner classifications agree after reversal; and
- no transport, budget, persistence, source, seal, resume, or identity failure
  occurs.

Primary R4 dispositions are:

- `FIDELITY_JUDGE_CONFORMANCE_PASS`;
- `INCONCLUSIVE_FIDELITY_JUDGE_UNAVAILABLE`;
- `INCONCLUSIVE_JUDGE_PROTOCOL_NONCONFORMANCE`; or
- `INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE`.

Track C is `PASS` only with 30 ready fixtures, 60 complete judgments from the
exact requested model, zero invalid judgments, 30 reversal pairs, and at least
27 reversal agreements. It is `NONCONFORMANT` after any terminal Track C
outcome or a final metric below those thresholds, and `NOT_RUN` when Track F
does not pass. It cannot unlock Track F, invalidate a Track F pass, or support
an efficacy claim.

## 6. Harness and privacy contract

R4 binds the repaired harness revision only after provider-free conformance
tests pass. The harness must:

- commit usage and sanitized transport metadata before parsing response
  content, including non-text/refusal responses;
- record content-block types but never private content in public receipts;
- record fixture failure phase and arm;
- atomically persist private transcripts, solutions, raw judge responses, and
  parsed scores before downstream use;
- keep credentials, raw prompts, task text, answers, scores, winners, and
  account identity outside the repository; and
- expose only efficacy-blind conformance counts and hashes publicly.

The output root must be outside the repository. A public receipt may be copied
back only after a privacy/secret scan.

## 7. Independent authorization and ceilings

This freeze and its seal authorize zero provider calls. R1, R2, and R3
authorizations are invalid for R4. A new authorization must bind the final
protocol digest, input-seal digest, repaired harness commit, exact model IDs,
both providers, and all ceilings.

Proposed limits and stop thresholds, to be accepted or replaced before
execution:

- 30 generated answer pairs;
- 120 judge requests, including reversals;
- 2,700 logical completions;
- 8,100 transport attempts;
- 6,000,000 input tokens;
- 3,000,000 output tokens;
- a four-hour pre-dispatch deadline; and
- USD 20.00 additional first-party API spend.

Logical-call and transport-attempt limits are enforced before dispatch. Token
and actual-cost totals are response-accounted stop thresholds: one completed
response may cross them before its usage is known. Each dispatch must still
reserve a conservative configured cost, and no later request may begin after a
threshold is reached. An interrupted in-flight request makes recorded token
and cost totals explicit lower bounds. The deadline prevents a new dispatch
after four hours but cannot cancel or erase a request already in flight. These
limits are not a forecast or permission to consume them.

## 8. Immutability and kill condition

After adversarial review and sealing, this protocol is immutable. A defect in
the sealed protocol, cohort, prompt artifacts, or harness requires a separate
prospective amendment or a new protocol before further observations.

R4 ends this calibration line unless it reaches
`FIDELITY_JUDGE_CONFORMANCE_PASS`. Another inconclusive repetition does not
justify R5 by default; reopening would require a new, concrete instrument
hypothesis and independent authorization.
