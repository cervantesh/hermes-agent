# Amendment 001 — Windows asynchronous-log lifecycle

Parent protocol seal SHA-256:
`fb01efd5b59bd3d36070b8b3702ba0ebc66420f8a465bafc5e0aa5ea56fffdb3`

Status at discovery: no scored observation had started. One Anthropic
credential preflight completed its provider call, then failed while destroying
its temporary home. It is infrastructure evidence only and is excluded from
the scored ledger.

## Observed failure

On Windows, `AIAgent.close()` did not tear down Hermes's process-wide queued
logging handlers. `TemporaryDirectory.__exit__()` then attempted to remove
`logs/.__agent.lock` while `concurrent-log-handler` still held it open. The
provider response itself had completed successfully (`api_calls=1` with
measured usage), but cleanup raised `PermissionError`, followed by
`NotADirectoryError` during the retry path.

## Authorized correction

`windows_execution_adapter.py` wraps the already sealed isolation context and
calls Hermes's existing test-isolation teardown helper before the underlying
temporary directory exits. It then resets the logging initialization latch so
the next isolated observation creates handlers scoped to its own home.

The adapter is installed only at the two scored isolation bindings used by
Tracks 1–3.

## Impact assessment

This amendment changes only post-call logging cleanup on Windows. It does not
change:

- a prompt or toolset;
- a corpus, seed, requested key, or relationship;
- a cohort, provider, model, or API mode;
- an oracle, metric, threshold, arm order, stopping rule, or disposition; or
- the original design, original protocol seal, or any production Hermes file.

All scored observations must be produced after this amendment is sealed. No
pre-amendment provider call may be pooled into the scored result.
