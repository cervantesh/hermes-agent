# Frozen V3 protocol: durable shared-context repetition

Status: **FINAL BEFORE REMOTE SEAL**. No provider-backed preflight or scored
observation may run until this file and the complete decision-critical source
manifest are committed and pushed to the public fork.

Target: `NousResearch/hermes-agent@c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf`.

## Arms

- **A — parent relay:** one parent model receives the producer's persisted
  completion summary and relays it once to the consumer.
- **B — current Hermes handoff:** the real Kanban parent-link projection for
  detached workspaces or the exact producer-written artifact for shared
  storage.
- **C — durable experimental handoff:** validated producer data is committed
  to a workflow-keyed SQLite store. The writer closes; a fresh Python process
  opens the database read-only and returns only declared keys. That projection
  is placed in the consumer body. C remains evaluation code, not a proposed
  product surface.

All consumers use the same bounded tool schema and isolated homes, databases,
sessions, boards, and workspaces. The existing V2 real-worker kernel remains
the execution engine and is hash-bound into the V3 source manifest.

## Cohorts and repetitions

Every cohort executes the same four dependent fixtures and two independent
controls. No adaptive fixture selection is allowed.

| cohort | model | schedule seed |
| --- | --- | ---: |
| `haiku-s377` | `claude-haiku-4-5` | 377 |
| `haiku-s378` | `claude-haiku-4-5` | 378 |
| `sonnet-s377` | `claude-sonnet-4-6` | 377 |

Provider: `claude-code`. One retry is permitted only for a classified provider
failure. A second provider failure is retained as an invalid observation; it
is never replaced or pooled as success.

After the remote seal and before scored observations, one unscored provider
and topology preflight runs `preflight_detached_echo` and
`preflight_shared_echo` with `haiku-s377`. It must admit the producer, execute
all three arms, and satisfy every integrity gate. A failed preflight stops the
experiment and is retained as evidence; it cannot be replaced by an easier
fixture or counted as a scored observation.
The scored runner refuses to dispatch without the passed receipt and verifies
its target, cohort, fixtures, remote source commit, source-manifest digest, and
sanitized-observation digest.

## Primary endpoint and admission

The primary endpoint is executable `verified_workflow_success`. Model prose,
completion status, or a completion token cannot override the external oracle.

A fixture is valid only when its producer is admitted, all three arms exist,
every integrity value is true, and no provider failure is present. All 18
fixture/cohort pairs and every control must be valid for a conclusive label.

## Lifecycle and scope

Allowed Kanban operations are `kanban_show`, `kanban_complete`,
`kanban_heartbeat`, and `kanban_block`.

- Any explicit Kanban target different from the active consumer card is a
  foreign-task integrity violation.
- `kanban_block` on the active card is not scope expansion. The external oracle,
  final status, and receipt determine the adverse arm outcome.
- Every public `kanban_block` receipt contains the operation, `own_active_task`
  or `foreign_task`, and SHA-256 identities for actor and target. Raw IDs,
  paths, prompts, logs, and summaries remain private.

All V2 file-path, tool-surface, producer, identity, isolation, atomicity, and
cost-accounting checks remain active.

## Decision rule

If any expected fixture is missing or invalid, or any independent control
fails, the verdict is `INCONCLUSIVE`.

With a complete experiment:

- `IMPLEMENTATION OPPORTUNITY` requires one of:
  - the same externally verified fixture succeeding only in C — both A and B
    fail — in all three cohorts;
  - median C-vs-B total-token improvement of at least 15% in every cohort,
    with no cohort showing latency regression; or
  - median C-vs-B constructed-latency improvement of at least 20% in every
    cohort, with no cohort showing token regression.
- An unreplicated C-only success yields `INCONCLUSIVE`.
- Otherwise the bounded label is `NO DEMONSTRATED INCREMENT`. This is not an
  equivalence claim and does not prove that shared context has no value.

Fidelity remains a reported secondary endpoint. Fidelity without an external
outcome or repeated resource trigger cannot independently authorize a product
implementation.

## Evidence and chronology

The seal records hashes for V3 files and reused V2 execution files. The remote
pre-run commit SHA and GitHub timestamp are part of the final receipt. Results
must be committed later, never amended into the pre-run commit.

Public verification must:

1. validate observation bytes and count;
2. recompute the decision from sanitized observations;
3. compare that decision byte-for-structure with `receipt.json`; and
4. fail on any mutated verdict or metric.

## Limitations frozen in advance

- The fixtures remain synthetic and structured.
- SQLite plus a fresh local process tests durability beyond process memory, not
  multi-host availability or a production scratchpad service.
- Constructed latency is not sequential harness wall time, and token totals are
  not provider-price-weighted cost.
- Two Anthropic model tiers are not cross-provider confirmation.

These limitations narrow interpretation; they do not permit post-result
threshold changes.
