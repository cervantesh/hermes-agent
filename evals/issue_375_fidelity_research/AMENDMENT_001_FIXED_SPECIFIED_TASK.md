# Issue #375 Fidelity Research — Amendment 001

Status: `FROZEN_PROSPECTIVE_AMENDMENT_NO_OBSERVATIONS`

Amendment ID: `IP375-FIDELITY-AMENDMENT-001-SPECIFIED-TASK-2026-09-03`

Parent freeze: `IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Decision

Lane R will use each selected official AI Society record's published
`specified_task` as the fixed output of the task-specification stage. It will
not invoke a modern task-specifier model.

The published `specified_task`, assistant role, user role, and original task
must be identical between the original and ablated arms. Historical generated
messages, responses, termination reasons, and extracted solutions are not
inputs to either arm.

## Reason

Appendix T changes the AI User and AI Assistant inception prompts and says the
same selected task set is used for both solutions. Re-running task
specification with a modern, stochastic model would add an intervention not
present in the ablation and substantially increase calls and variance. The
pinned official dataset provides the task-specification output needed to hold
that stage constant.

## Operational consequence

- The paper-era task-specifier prompt remains a source-audit requirement.
- The sample manifest records stable IDs plus hashes of the original task,
  specified task, and roles.
- The execution protocol records no provider model or call for task
  specification; its identity is `PINNED_DATASET_OUTPUT`.
- This amendment does not alter the two role agents, historical priming,
  alternation, stopping rules, extraction, judging, sample size, or Lane P.

## Claim boundary

This is a prospective isolation choice for a mechanism-faithful
reconstruction. It does not recover the paper's undisclosed Appendix T sample
or original hosted model snapshots, and it does not turn Lane R into an exact
historical replication.

## Change control

This amendment is immutable after sealing. Replacing the fixed published task
with a newly generated task specification requires another prospective
amendment and fresh observations.
