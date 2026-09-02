# V4 research frame: terminal-outcome retention

Status: **pre-observation**.

V4 repeats the exact V3 product question, target, arms, fixtures, cohorts,
models, seeds, thresholds, and external outcome oracle. It changes one harness
contract exposed by the archived V3 run:

> Every terminal fixture outcome must become exactly one retained row.

A classified provider failure may receive the single frozen retry. Any other
exception, including a consumer deadline, becomes a structured invalid row on
the first attempt. It is not retried or replaced, and the runner continues the
remaining frozen slots. The raw row may retain a private diagnostic; public
evidence contains only exception type, failure phase, and a message digest.

The V3 partial result remains `INCONCLUSIVE` and is not pooled into V4. V4 runs
all 18 slots from scratch against the same clean target SHA.

This is a methodological repair, not a production implementation and not a
change to Hermes behavior.
