# Eigent Workforce and current Hermes evidence

This is a source-pinned product-gap analysis, not an argument to import Eigent
wholesale.

## Executed source suites

At Eigent `92f17b596ce2ae27977d6db2f0ed11a81560115f`:

```text
uv run --project backend --frozen pytest backend/tests/app/utils/test_workforce.py -q
38 passed, 3 warnings in 3.79s
```

The warnings were unawaited-coroutine warnings in mocked tests. They do not
change the assertions, but they are retained as test-quality caveats.

At Hermes `64cc87e6681a3db4e158ed8b999ff77ba0b9d28a`:

```text
python -m pytest tests/tools/test_async_delegation.py tests/gateway/test_completion_delivery.py -q
52 passed, 1 skipped in 16.97s
```

The selected suites execute process-restart completion recovery, delivery
claims/deduplication, progressing/stalled runner behavior, and gateway
reinjection. They are characterization evidence, not production fault
injection across two live machines.

## What is already overlapping

Hermes already persists an async dispatch before submitting the daemon runner
(`tools/async_delegation.py:861-897`), classifies an abandoned owner as
`outcome unknown` (`:351-398`), restores undelivered terminal events (`:400`),
atomically claims delivery (`:467`), and interrupts/finalizes stalled children
(`:1258-1416`). Therefore “add durability, deduplication, and a watchdog from
Eigent” is not a valid product proposal.

Eigent independently persists Workforce subtask steps before UI/runtime
publication (`backend/app/utils/workforce.py:78`, invoked before assignment at
`:658`), enables CAMEL retry and replan (`:206-208`), and uses a
progress-sensitive stall timeout (`:188-194`, `:1015`). These are concrete
mechanisms, but several overlap Hermes at a different boundary.

## The remaining boundaries

1. **Execution restart is not completion replay.** Hermes preserves the task
   specification and terminal delivery, but an owner death while running is
   classified as outcome unknown. It does not recreate the child at a durable
   step frontier. A restartable execution protocol would be a separate,
   high-risk product feature.
2. **Task-level retry/replan is not current generic behavior.** Hermes retries
   provider calls and permits one response-schema correction, but a failed
   delegated task is not generically re-decomposed or reassigned. Whether that
   improves verified outcomes needs a real failed-task cohort before design.
3. **Neither system proves side effects by default.** Hermes's output schema
   verifies response shape, and `agent.verify_on_stop` defaults off. Eigent's
   analyzer is model-produced quality evidence rather than an external oracle.
4. **Eigent's fallback cannot be adopted as a truth gate.** After three failed
   quality-analysis attempts, a non-failure analysis returns
   `quality_score=80` (`workforce.py:221-285`). Its own test pins that behavior.
   This preserves flow but can turn verifier unavailability into apparent
   acceptance.

## Product disposition

- Do not add a second durability, completion-delivery, claim, or stall stack.
- Do not treat the pinned Eigent quality score as verified completion.
- Evaluate task-level replan/reassignment only on a cohort where current
  Hermes reaches a terminal externally incorrect result or a recoverable
  delegated failure.
- Treat restartable step execution as an independently closable transaction
  problem, not as a prerequisite for role prompting.
- Reuse current Hermes async state and delivery ownership if either mechanism
  is later implemented.

The smallest current conclusion is negative architecture evidence: most of
the generic Workforce control plane already exists in Hermes, while the two
remaining mechanisms require their own opportunity and safety proof.
