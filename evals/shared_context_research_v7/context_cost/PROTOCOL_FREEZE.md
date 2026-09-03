# Track 1 Protocol Freeze — Context Cost and Volume

Parent freeze: `SCR-V7-INITIAL-2026-09-02`

Target: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

## Hypothesis

For an opaque completed parent result, projecting only consumer-declared keys
may preserve the exact external result while materially reducing provider
input tokens or latency versus the strongest current Hermes retrieval path.

## Arms and fixtures

- `B`: a fresh Hermes consumer receives the real child startup context and may
  call real `kanban_show(parent_id)` to parse the complete `task.result`.
- `D`: a harness-only declared-key projection is placed in the consumer input;
  it is not production code and receives no Kanban tool.
- `subset`: seed 377, 80 records, 96-byte opaque values, indexes 7 and 73
  selected only after corpus generation.
- `all_records_control`: seed 378, 12 records, 32-byte opaque values, every key
  required. Its full and declared payload bytes must be equal.

The expected values and expected JSON are never placed in the model prompt.
The external oracle parses strict JSON and compares it with the deterministic
source corpus.

## Cohorts and order

- Anthropic `claude-sonnet-4-6` through `anthropic_messages`.
- OpenAI `gpt-5.4` through `openai-codex` / `codex_responses`.

Arm order is SHA-256-derived from seed and cohort. Every arm uses a fresh
`HERMES_HOME`, board, database, session, and task graph. Failed slots are
retained and never replaced.

## Decision

Use provider-reported input tokens only; do not estimate tokens from bytes.
The gate requires equal strict external success across both cohorts, at least
15% lower median input tokens or 20% lower median latency, and no regression in
the other metric. The all-records control must remain exact and cannot be used
to claim a selective payload advantage.

If the gate passes, the provisional disposition is `IMPLEMENTATION
OPPORTUNITY`, but no implementation specification may be issued until a
compact/delta `kanban_show` discriminant is tested. If that smaller projection
reproduces the benefit, disposition changes to `EXISTING OWNER` and #95561 owns
the solution. This experiment alone cannot authorize a new shared-context
layer.
