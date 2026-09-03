# R4 terminal postmortem

R4 terminated prospectively as `INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE`.
It is not resumable, poolable, or evidence about prompt efficacy.

## What happened

Twenty fixtures reached `JUDGE_READY`. During generation of the ablated arm
for task `027_006_007`, the Anthropic client raised `APIConnectionError`.
The fail-fast gate quarantined that fixture, wrote the public summary, and
made no request to either judge.

The recorded lower-bound usage before termination was 547 logical calls, 547
transport attempts, 1,151,493 input tokens, 273,557 output tokens, and USD
2.519278. The failed dispatch has no response receipt, so its provider-side
outcome and any associated usage are unknown.

## Evidence defect

The original public summary reported `usage_is_lower_bound: false`. That value
is incorrect. Its classifier treated six earlier successful response receipts
from the same generation arm as evidence that the terminal dispatch itself had
a receipt. The terminal call has no seventh response receipt.

`R4_EXECUTION_DISPOSITION_RECEIPT.json` preserves the original summary hash and
records the conservative adjudication without rewriting external evidence.

## Disposition

R4 remains terminal. The frozen protocol does not allow retrying the failed
call, resuming the remaining cohort, or presenting a new run as R4. A future
repetition would require a new prospective protocol, fresh identity, explicit
authorization, and a concrete reason strong enough to reopen this calibration
line. The harness defect can be repaired and tested provider-free without
authorizing such a repetition.

## Provider-free harness repair

The postmortem repair recognizes provider SDK connection and timeout failures
as retryable transport errors, emits sanitized receipts for attempts whose
provider-side outcome is unknown, and keeps that uncertainty sticky after a
successful retry. Final summaries derive `usage_is_lower_bound` from both live
backend receipts and durable public fixture/judgment checkpoints, so a legal
process restart cannot erase the signal.

This repair applies only to future protocols. It does not resume R4 or change
R4's frozen inputs, observed output, terminal disposition, or eligibility for
pooling. Provider-free verification and adversarial disposition are recorded
separately in `R4_POSTMORTEM_HARNESS_REPAIR_RECEIPT.json`.
