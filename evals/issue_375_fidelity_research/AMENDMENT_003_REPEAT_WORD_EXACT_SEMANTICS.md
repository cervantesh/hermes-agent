# Issue #375 Fidelity Research — Amendment 003

Status: `FROZEN_PROSPECTIVE_AMENDMENT_NO_OBSERVATIONS`

Amendment ID: `IP375-FIDELITY-AMENDMENT-003-REPEAT-WORD-EXACT-2026-09-03`

Parents:

- `IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`
- `IP375-FIDELITY-AMENDMENT-002-REPEAT-WORD-2026-09-03 @ 4097be004265`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Correction

Amendment 002 correctly restored the omitted repeat-word termination but
described its counter too broadly. The pinned implementation iterates the
ordered list below for each user/assistant pair:

`goodbye`, `good bye`, `thank`, `bye`, `welcome`, `language model`

For each individual list item, it increments the shared counter if either
message contains that item; otherwise it immediately resets the counter to
zero. It terminates when the counter reaches four and breaks only the inner
word loop at that point.

The harness must reproduce that exact nested-loop behavior, including its
resets, rather than replacing it with the more intuitive rule “four messages
containing any listed word.”

## Reason

This is a source-fidelity reconstruction. Improving an awkward historical
heuristic would change the mechanism under test.

## Scope and change control

This amendment supersedes only Amendment 002's informal counter description.
Its source identity, word list, threshold, outcome label, and all other frozen
conditions remain unchanged. This artifact is immutable after sealing.
