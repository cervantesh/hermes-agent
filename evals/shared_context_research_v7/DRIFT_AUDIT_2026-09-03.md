# Supplemental drift audit — 2026-09-03

Parent design: `SCR-V7-INITIAL-2026-09-02`

Frozen Hermes target: `593aa74c6182ce2e5e23bc102daaaae71710c05d`

Observed `origin/main`: `48c0c3a873bc5adaf20c632b5b7630a4fac000b4`

The original sealed audit remains historical evidence and was not edited.
This supplemental audit was performed before sealing the corrected repetition.

## Relevant code drift

Direct comparison of the frozen target with observed `origin/main` found no
byte changes in:

- `tools/delegate_tool.py`;
- `hermes_cli/kanban_db.py`; or
- `tools/kanban_tools.py`.

The observed main revision changed `agent/relay_llm.py`,
`agent/relay_runtime.py`, and `agent/relay_tools.py` as part of the Relay 0.8.3
upgrade. Those changes do not alter the Kanban startup projection,
`kanban_show`, terminal task result, declared-projection arm, fixtures, or
external oracles used by Tracks 1–3.

The corrected repetition therefore remains pinned to the frozen Hermes target
for comparability. The main advance does not silently replace that target and
does not require a hypothesis, fixture, threshold, or adjudication change.

## Tracker state

At this audit:

- #377 remains open with `P3` and `needs-decision`;
- #95561 remains open and is still the focused owner for optional
  full/compact/minimal `kanban_show` and worker-context retrieval.

Accordingly, #95561 remains the mandatory smallest-footprint discriminant if
Track 1 later demonstrates a repeated selective retrieval advantage.
