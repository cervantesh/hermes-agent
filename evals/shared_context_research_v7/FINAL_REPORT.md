# Shared Context Research V7 — Final Report

Freeze: `SCR-V7-INITIAL-2026-09-02 @ 7de472e9de934cac0a5041defb3ea455d4129118969c3b830b8a77d93c201787`

Hermes: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

CAMEL: `camel-ai/camel@5cd0d0f4bda29893bdbf90c707c4ee59e36c829c`

Issue: <https://github.com/NousResearch/hermes-agent/issues/377>

Final product disposition: `NO_IMPLEMENTATION_JUSTIFIED_BY_FROZEN_EVIDENCE`

## Executive conclusion

The evaluated Hermes adaptations did not produce evidence sufficient to add a
new shared-context mechanism to the product. This conclusion is deliberately
bounded: under the frozen models, opaque fixtures, horizons, existing Hermes
capabilities, controls, and external oracles, no incremental product need was
demonstrated.

The study does **not** conclude that CAMEL is ineffective, that every possible
shared-context design lacks value, or that future real workflows cannot expose
a different gap. It concludes that issue #377 should not advance to a product
implementation from this evidence package.

## Source fidelity

The original CAMEL paper's relevant mechanisms are task specification, two
role agents, alternating multi-turn cooperation, inception prompts, and
explicit termination. Current CAMEL Workforce additionally supports selected
lifecycle synchronization of complete conversation/tool memory. Declared-key
reads, namespaces, active shared writes, concurrency semantics, and remote
durability are Hermes adaptations, not paper findings.

Accordingly, V7 is product-oriented exploratory/adaptation research informed
by CAMEL. It is not presented as a direct scientific replication of the paper.

## Evidence history

| Frame | Observations | Valid use | Disposition |
| --- | ---: | --- | --- |
| Run 001, `v7-scored-20260903` | 23 | Harness diagnosis only; do not pool | `INCONCLUSIVE_PROTOCOL_IMPLEMENTATION` |
| Run 002, `v7-repetition-001-20260903` | 23 | Track 1 control; exposed restricted Track 2 surface and ambiguous Track 3 completion | `INCONCLUSIVE_PROTOCOL_IMPLEMENTATION` |
| Run 003, `v7-repetition-002-20260903` | 7 | Clean Track 2 strongest-baseline gate and Track 3 controls/probes | `NO_IMPLEMENTATION_JUSTIFIED_BY_FROZEN_EVIDENCE` |

Invalid or superseded rows were preserved rather than rewritten or pooled.
Run 003 stopped at seven observations because no Track 2 RED opened the
conditional eight-observation confirmation block.

## Track results

### 1. Context cost and volume — `INCONCLUSIVE`

Run 002 produced exact outputs and an apparent projection advantage, but the
all-records control showed essentially the same advantage. The comparison
therefore measured the overhead difference between a one-call inline prompt
and a multi-call worker lifecycle rather than isolating selective retrieval.
The prospectively frozen control veto applies. No resource-value claim is made.

### 2. Selective key access — `EXISTING HERMES MECHANISM SUFFICIENT`

Run 003 allowed the B arm to use the normal Hermes CLI worker surface. It was
valid and exact at 32, 128, and 512 opaque records. At 512, the worker followed
the real spill path with `read_file` and `terminal` and still returned the exact
requested value. The D confirmation arm was not run because the required
current-Hermes product RED did not occur.

### 3. Isolation and permissions — `INCONCLUSIVE`, `POLICY_UNADJUDICATED`

Both Anthropic Sonnet 4.6 and OpenAI Codex GPT-5.4 passed the declared-parent
positive control and could read an unrelated same-board task. This confirms
reachability. The repository's current behavior does not define the frozen
candidate denial rule as product policy, so the observation is not classified
as a vulnerability and does not justify a permissions layer.

### 4. Active writes — gate closed

No real workflow demonstrated that completed results, Kanban comments,
attachments, or live steering fail the required external outcome. No treatment
was built or scored.

### 5. Concurrency — gate closed

This track depended on a valid active-write need. Because Track 4 did not open,
no shared-write concurrency mechanism was tested or proposed.

### 6. Remote backends — gate closed

The frozen design required a locally valuable treatment before remote
portability testing. No such treatment survived the earlier gates.

## Product decision

No production code should be proposed from V7. In particular, the evidence
does not support adding a shared key/value store, declared-key API, namespace
policy, active-write protocol, concurrency controller, or remote shared-state
backend to Hermes.

An implementation specification is intentionally omitted because the frozen
adoption gates did not pass. Producing one would turn an unproven treatment
into apparent product direction.

## Reopening condition

Reopen only for a new, independently frozen product question with a real
Hermes-native workflow that fails an external oracle after every ordinary
authorized existing route has been allowed. A cost-only claim needs a clean
comparator that removes lifecycle overhead and a prospectively defined
resource threshold. A permission claim needs maintainer-owned policy before
reachability can be called a violation. Tracks involving writes, concurrency,
or remote backends retain their original dependency gates.

Any future frame must cite this freeze, state which conclusion new evidence can
change, define its kill condition, and preserve these runs without pooling
invalid observations.

## Current-main drift

After Run 003, `origin/main` was refreshed to
`a2a16dfdacc3616c473ef56a905913ce99cb81e0`. A path-limited comparison found no
changes since the frozen Hermes revision in the delegation, Kanban,
tool-resolution, or worker-ownership paths that define this study's baseline.
The drift classification is `NO_IMPACT`; the detailed command scope is recorded
in `DRIFT_AUDIT_2026-09-03_FINAL.md`.
