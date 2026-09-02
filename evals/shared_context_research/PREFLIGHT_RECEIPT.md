# Real-worker preflight receipt

Date: 2026-09-01  
Target: `180291162ff4df0d42b5dc4fecd08005cf7cebf9`  
Runtime: Python 3.11.7, Windows, `claude-code` credential path,
`claude-haiku-4-5` through the Anthropic Messages adapter

## Purpose

Prove before sealing the protocol that the pinned checkout can execute the
worker lifecycle required by every arm. This is runtime preflight, not a scored
research observation.

## Procedure

1. Created an empty temporary Kanban board and a `dir` workspace.
2. Created one ready card assigned to the default profile, with model and
   provider overrides pinned to the frozen pilot runtime.
3. Called current main's `dispatch_once()` with its default spawn path.
4. Waited for the dispatcher-owned process to finish through the Kanban tools.
5. Queried the worker session ledger and external artifact.

## Observed lifecycle

The persisted tool order was:

1. `kanban_show`
2. `write_file`
3. `kanban_complete`

The card finished `done`; its run outcome was `completed`; summary was exactly
`preflight-ok`; metadata retained the probe marker and artifact reference. The
external artifact was exactly `{"ok":true}` with SHA-256
`4062edaf750fb8074e7e83e0c9028c94e32468a8b6f1614774328ef045150f93`.

## Disposition

`PASS`. The actual dispatcher -> worker -> `kanban_show` -> file tool ->
`kanban_complete` path is executable on the pinned runtime. This does not yet
prove the A/B/C harness, isolation controls, token accounting, or provider
stability for the full pilot.
