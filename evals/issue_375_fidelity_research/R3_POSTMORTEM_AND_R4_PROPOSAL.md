# R3 terminal disposition and prospective R4 proposal

R3 is terminal as `INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE`. This document is
retrospective; it is not a preregistration, an amendment that makes R3 valid,
or authorization for another provider call.

## Observed

- Provider metadata preflight passed for all three exact model IDs.
- Nine of 30 generation/extraction fixtures reached `JUDGE_READY`.
- Task `014_005_009` received an Anthropic response with no usable text block
  and was quarantined before solution extraction completed.
- The frozen `30/30 JUDGE_READY` gate became unreachable, so execution was
  stopped before either judge received a request.
- The investigator interrupt occurred while task `050_012_004` had a provider
  request in flight. Its outcome is unknown and it was not retried.
- No score, winner, reversal result, or efficacy aggregate exists.

## Harness defects exposed

1. Anthropic usage was committed after text extraction. A completed non-text
   response therefore consumed a logical/transport attempt but did not commit
   its token usage or sanitized response receipt.
2. The fixture loop continued after a terminal fixture failure even though no
   later result could restore the required 30/30 gate. Manual interruption was
   needed to stop avoidable spend and created one unknown in-flight outcome.
3. The fixture quarantine recorded only a generic exception type, omitting the
   generation/extraction phase, arm, and sanitized transport metadata needed
   to distinguish provider content from harness transport failure.

The post-R3 implementation corrects those instrument defects provider-free:
usage and metadata are committed before content parsing, non-text responses
record content-block types without content, fixture failures record phase and
arm, and the loop stops on the first terminal fixture receipt. These changes
do not repair or reinterpret R3.

## Conditions for a clean repetition

A proposed R4 may retain the same models, prompts, two-track judge design,
30/30 fixture gate, 60/60 fidelity judgments, and 27/30 reversal threshold.
It must nevertheless be a new evidence frame because R3 observations and the
harness repair now exist. Before any R4 call it must:

1. select and seal 30 fresh task IDs excluding every R1, R2, scored-frame, and
   R3 task ID;
2. bind the repaired harness commit and its provider-free tests;
3. preserve the no-repair/no-retry-on-content contract;
4. stop automatically on the first terminal fixture or fidelity-judge failure;
5. define usage after non-text responses as committed and auditable;
6. receive a new explicit authorization with independent spend and token
   limits.

Until those conditions are prospectively frozen and approved, the correct
next action is no provider execution.
