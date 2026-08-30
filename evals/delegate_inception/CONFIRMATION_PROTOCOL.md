# Long-horizon confirmation protocol

Status: frozen before the first scored confirmation observation.

## Question

Does the candidate child system prompt improve strict completion of long,
stateful delegated work relative to `main@58523f284ca52a162a213a7efd335b203e783706`
without increasing false success or materially increasing API calls?

The candidate under test is the exact tree containing the prompt change and
this evaluator. The evaluator is arm-blind and runs the same committed task
definitions against both production trees.

## Design

- Provider/model: `claude-code` / `claude-haiku-4-5`.
- Paired, randomized A/B execution with seed `37503`.
- Twenty new task definitions, one observation per task and arm.
- Five workflow archetypes with four independently named and parameterized
  instances each: linear checkpoint, named state machine, two-lane fan-in,
  event-ledger reconstruction, and chunk assembly.
- Production delegation depth: one child, no parent steering, no coordinator.
- Child iteration budget: 50, matching Hermes's production default.
- No task or scored oracle from the short pilot or long-horizon v2 is reused.

Each workflow contains a late unavailable preferred source and an available
alternate source. Passing requires the complete authoritative artifact set,
verified transitions, a truthful final receipt, observed recovery, no third
identical blocked retry, no request to the parent, and completion within the
budget. A nominal receipt cannot compensate for missing required work.

## Endpoints fixed before execution

Primary endpoint: paired strict pass/fail for every task.

Primary analysis: two-sided exact McNemar test over discordant pairs. The
candidate is confirmatory only if all of the following hold:

1. candidate-only wins exceed baseline-only wins;
2. exact two-sided McNemar `p <= 0.05`;
3. candidate total strict passes are not lower; and
4. transcript inspection finds no new candidate false-success mechanism.

Anything weaker is reported as suggestive, inconclusive, parity, or adverse.
Calls, tokens, and duration are secondary diagnostics and cannot rescue a
failed primary endpoint.

## Execution and stopping rules

- Commit and publish this protocol, task catalog, fixtures, and graders before
  the first scored observation.
- Run every committed pair once. Do not add tasks, repetitions, or alter an
  oracle after inspecting results.
- A provider/authentication/transport failure is not a behavioral result. If
  it occurs, discard neither arm silently: record the interruption and rerun
  the entire affected pair once. A second infrastructure failure makes the
  confirmation indeterminate.
- Inspect every discordant or failed transcript only after the full matrix is
  complete. Classification may explain a result but cannot change its frozen
  programmatic score.
- Preserve raw JSONL locally under ignored `results/`; publish aggregate
  evidence and sanitized decisive excerpts, not credentials or private paths.

## Interpretation boundary

This experiment tests a defensive Phase 1 child-execution contract. Even a
confirmatory result would not establish CAMEL's multi-agent role-playing
claims, coordinator behavior, every provider/model, or general task quality.
It would support only the measured single-child, long-horizon behavior.
