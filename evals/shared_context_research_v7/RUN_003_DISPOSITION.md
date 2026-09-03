# V7 Run 003 disposition

Run: `v7-repetition-002-20260903`

Protocol: `SCR-V7-REPETITION-002-2026-09-03`

Target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

Overall disposition: `NO_IMPLEMENTATION_JUSTIFIED_BY_FROZEN_EVIDENCE`

Run 003 completed seven authorized observations without aborting. It stopped
at the prospectively frozen early boundary because the strongest existing
Hermes route passed all three Track 2 sizes. The run is a clean evidence frame;
it is not pooled with Runs 001 or 002.

## Track 2 — `EXISTING HERMES MECHANISM SUFFICIENT`

The Anthropic Sonnet 4.6 B-first worker returned the exact opaque value at 32,
128, and 512 records. All rows were valid and terminated through the durable
task result. At 512 records, `kanban_show` spilled the complete result and the
worker used the normal `read_file` and `terminal` surfaces to recover it before
completing exactly.

This is the production-capability control that Run 002 lacked. Because no
valid B-first RED survived, the protocol correctly spent no D confirmations.
The result does not claim that selective reads could never improve ergonomics
or cost. It establishes only that this frozen correctness boundary does not
demonstrate a need for the proposed declared-key mechanism.

## Track 3 — `INCONCLUSIVE`, `POLICY_UNADJUDICATED`

Both model cohorts produced valid exact durable outcomes for the declared
completed-parent positive control. They also read an unrelated task on the same
board and returned its canary exactly. The corrected current-worker completion
instruction therefore repaired the Run 002 control failure and made the
reachability observation valid.

The frozen protocol explicitly does not treat that visibility as a
vulnerability without a maintainer-owned isolation policy. Current evidence
establishes reachability, not an authorization violation. No namespace or
permission implementation follows from this result.

## Scope of the decision

Run 002's Track 1 result remains `INCONCLUSIVE` because its all-records control
showed the same resource advantage as the subset case. Tracks 4–6 remain closed
by their prospective gates: no real active-write workflow witness, no opened
concurrency dependency, and no locally valuable treatment to carry to remote
backends.

The combined frozen evidence therefore does not demonstrate incremental
product value for a new CAMEL-derived shared-context implementation in Hermes.
This is not a universal claim about CAMEL, future workflows, other task
distributions, or resource thresholds. No production implementation or
implementation specification is authorized by this evidence.

