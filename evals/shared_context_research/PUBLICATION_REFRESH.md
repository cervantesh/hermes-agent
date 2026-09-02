# Publication-time upstream refresh

Refresh date: 2026-09-02  
Publication target: issue #377 evidence comment  
Access: read-only upstream Git and authenticated GitHub connector

## Revisions

- Frozen experimental target:
  `180291162ff4df0d42b5dc4fecd08005cf7cebf9`
- Upstream `main` at publication gate:
  `57d305d57f04ffb58fb8adef3657b166fa6e34a6`

The experiment is intentionally bound to the first revision. Its protocol,
source manifest, observations, and receipts remain immutable.

## Intervening code

The publication refresh found no changes between those revisions in the
specific handoff and scope-resolution owners used to define the three arms:

- `tools/delegate_tool.py`;
- `hermes_cli/kanban_db.py`;
- `tools/file_tools.py`;
- `model_tools.py`; and
- `toolsets.py`.

However, upstream did change shared runtime surfaces including
`agent/chat_completion_helpers.py`, `agent/conversation_loop.py`,
`hermes_state.py`, and gateway/session-related code. Those changes may affect
worker execution, accounting, streaming, or lifecycle behavior even though
they do not replace the handoff mechanisms themselves.

## Publication disposition

The packet is publishable as a sealed historical experiment on the recorded
SHA. It is **not** evidence about the exact behavior or resource measurements
of publication-time `main`. A current-main comparison would require a new
evidence frame, prospective seal, and new observations rather than rebasing or
pooling this packet.

This version movement does not create an implementation recommendation. The
recorded formal outcome remains `INCONCLUSIVE` on its pinned target.

## GitHub ownership at publication

The authenticated GitHub refresh found:

- issue #377 remains open and unchanged, with three comments;
- PR #82157 remains open and unmerged at
  `722fcc12d843c725e487e7d9a4dbea7a2cad4c37`;
- PR #83061 remains merged; and
- no issue or PR updated since 2026-09-01 owns the exact bounded experiment.

The closest new keyword match, issue #100383 with PR #100402, concerns a
Honcho provider's user-global recall across clients. It is persistent memory
observer configuration, not immutable dependency handoff within one workflow,
and therefore does not supersede this packet.
