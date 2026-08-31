# Product decision and smallest-footprint roadmap

## Adjudication

| Candidate | Decision now | Evidence |
|---|---|---|
| Full CAMEL RolePlaying as default | Reject | No baseline opportunity; Haiku regressed correctness and truth; substantial overhead on both models |
| Full CAMEL as an opt-in mode | Do not implement yet | No eligible cohort showed incremental verified success |
| Pre-tool task specifier | Reject for repository tasks | It changed the requested contract before reading the workspace |
| AI User as completion authority | Reject | It emitted `task_done` for two externally incomplete/incorrect states |
| Explicit termination token | Keep only as a protocol bound | It limits turns but does not verify completion |
| Eigent Workforce wholesale | Reject | Duplicates Hermes control-plane mechanisms and imports an unsafe score-80 fallback |
| Task-level retry/replan | Unresolved hypothesis | Concrete mechanism gap, but no failed-task efficacy cohort |
| Durable step execution resume | Separate product problem | Real owner death currently yields outcome unknown; implementation would require transactional/idempotency design |
| External effect verification | Existing separate boundary | Response schema and role debate do not establish side effects |

## What should be implemented now

Nothing from CAMEL or Eigent should enter Hermes production on this evidence.
The research harness is the only completed artifact. Shipping a new role loop,
router, shared memory, task planner, or Workforce abstraction would be
speculative infrastructure.

## Conditions that would reopen CAMEL

A future study should start only from a real Hermes task family with all of:

1. a current-`main` baseline failure under an external oracle;
2. no existing owner such as `/goal`, verification-on-stop, or a specialized
   skill that already addresses it;
3. a grounded task specifier that cannot change repository facts before
   inspection, or an explicit decision to omit specification;
4. a budget-matched strong single-agent control;
5. false-success and scope-expansion guardrails; and
6. new-task, cross-family confirmation before a product PR.

Only then should ablations ask whether task specification, symmetric roles,
response format, or termination caused the gain.

## Conditions that would reopen Workforce mechanisms

Task-level retry/replan needs a reachable failure where retrying or changing
assignee is safe and the external oracle proves a better outcome. Durable step
resume needs a reported user consequence from owner death plus explicit
idempotency, unknown-outcome, lease, and side-effect reconciliation contracts.
Those are separate issues and separate PRs if evidence appears.

## Potential contribution shape

If maintainers want the methodology, the least-footprint contribution is an
evaluation package or discussion comment, not production code. It should state
the negative result, source pins, invalid Gemini preflight, executable oracles,
and limitations. It should not claim to close issue #375 or prescribe a new
architecture.

No issue or PR should be opened automatically from this research. A real
failed-baseline owner must come first.
