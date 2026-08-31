# Product decision and smallest-footprint roadmap

## Adjudication

| Candidate | Decision now | Evidence |
|---|---|---|
| Evaluated CAMEL-derived adaptation as default | Do not implement | No baseline opportunity; the Haiku sample lost verified correctness and produced false success |
| Evaluated adaptation as an opt-in mode | Do not implement yet | No eligible cohort showed incremental verified success |
| Evaluated ungrounded pre-inspection task specifier | Reject as a default | It changed one Haiku task contract; repository-wide value or harm remains unresolved |
| AI User as completion authority | Reject | It emitted `task_done` for two externally incomplete/incorrect states |
| Explicit termination token | Keep only as a protocol bound | It limits turns but does not verify completion |
| Eigent Workforce wholesale | Reject | Overlaps existing Hermes control-plane boundaries and imports an unsafe score-80 fallback |
| Task-level retry/replan | Unresolved hypothesis | Concrete mechanism gap, but no failed-task efficacy cohort |
| Durable step execution resume | Separate product problem | Real owner death currently yields outcome unknown; implementation would require transactional/idempotency design |
| External effect verification | Existing separate boundary | Response schema and role debate do not establish side effects |

## What should be implemented now

No CAMEL or Eigent mechanism should enter Hermes production on this evidence.
The research harness is the only completed artifact. Shipping a new role loop,
router, shared memory, task planner, or Workforce abstraction would be
speculative infrastructure.

## Conditions that would reopen CAMEL or a revised adaptation

A future study should start only from a real Hermes task family with all of:

1. a current-`main` baseline failure under an external oracle;
2. no existing owner such as `/goal`, verification-on-stop, or a specialized
   skill that already addresses it;
3. a grounded task specifier that cannot change repository facts before
   inspection, or an explicit decision to omit specification;
4. a budget-matched strong single-agent control on the same production tree;
5. false-success and scope-expansion guardrails; and
6. new-task, cross-family confirmation before a product PR.

If historical CAMEL fidelity is claimed, the evaluator must also reproduce the
historical initialization state sequence and record hashes of the effective
provider-bound prompts. Only then should ablations ask whether task specification, symmetric roles,
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
that this adaptation showed no incremental benefit in the evaluated sample,
include source pins, the invalid Gemini preflight, executable oracles, sanitized
receipts, and the protocol/causality limitations. It should not claim to close
issue #375 or prescribe a new architecture.

No issue or PR should be opened automatically from this research. A real
failed-baseline owner must come first.
