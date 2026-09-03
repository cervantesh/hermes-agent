# Issue #375 Fidelity Research — Amendment 002

Status: `FROZEN_PROSPECTIVE_AMENDMENT_NO_OBSERVATIONS`

Amendment ID: `IP375-FIDELITY-AMENDMENT-002-REPEAT-WORD-2026-09-03`

Parent freeze: `IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Decision

Lane R will preserve the additional repeat-word termination implemented by
the pinned paper-era AI Society generator. A single counter advances when a
role message contains one of these case-insensitive substrings:

`goodbye`, `good bye`, `thank`, `bye`, `welcome`, `language model`

The historical loop resets the counter on a non-matching check and terminates
at four matches. The harness will reproduce the effective behavior of the
pinned loop and label the outcome `repeat_word_threshold`.

## Reason

The initial freeze's list of historical termination checks omitted this
condition. The source of truth is
`examples/ai_society/role_playing_multiprocess.py` at
`camel-ai/camel@c402032a7f7cd27e196356fbcf413c521a8cb4ca`. Omitting it could
extend some conversations beyond the behavior that produced the official AI
Society data.

## Scope

No other termination condition changes. This prospective correction applies
before any provider observation and does not modify earlier evidence.

## Change control

This amendment is immutable after sealing. Any different word list, threshold,
or counter semantics requires another prospective amendment and fresh
observations.
