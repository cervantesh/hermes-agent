# Amendment 002 — Ephemeral Codex credential bridge

Parent amendment: `AMENDMENT_001_SEAL.json`.

Status at discovery: no scored observation had started. The initial Codex
credential preflight validated the external Codex CLI token structurally but
did not reach the provider because Hermes intentionally does not consume OAuth
credentials from an API-key environment variable.

## Authorized correction

For `openai-codex` observations only, the execution adapter reads the valid
Codex CLI access token and writes a temporary Hermes auth record inside the
already isolated per-observation `HERMES_HOME`.

The real external refresh token is never copied. The temporary record uses a
non-refreshable sentinel. The run aborts before persistence when the access
token has less than 30 minutes remaining. Consequently, the research process
cannot rotate or invalidate the Codex CLI refresh token.

The temporary auth record is destroyed with the observation home after queued
logging handles are closed by Amendment 001.

## Impact assessment

This amendment supplies credential authority only. It does not change:

- a prompt or toolset;
- a corpus, seed, requested key, or relationship;
- a cohort, provider, model, or API mode;
- an oracle, metric, threshold, arm order, stopping rule, or disposition; or
- the original design, protocol seal, Amendment 001, or production Hermes.

All scored observations must be produced after this amendment is sealed. The
failed preflight is infrastructure evidence only and cannot enter the scored
ledger.
