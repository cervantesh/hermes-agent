# Eigent production-reference comparison

This note follows up on the "Production use of CAMEL patterns" reference in
NousResearch/hermes-agent#375. It is a source comparison, not another scored
arm of the frozen prompt experiment.

## Evidence frame

- Eigent: `main@92f17b596ce2ae27977d6db2f0ed11a81560115f`
- Eigent dependency: `camel-ai[eigent]==0.2.91a5`
- Hermes current integration branch at inspection:
  `main@d63f996a757f6255fc1454239616ab4b4435e0f5`
- Frozen Hermes experiment baseline:
  `58523f284ca52a162a213a7efd335b203e783706`
- Frozen prompt candidate: `c19e547f211805a579f890a75b9d55f5c1f75545`

The Eigent revision is intentionally pinned. A moving repository URL is not a
reproducible statement about which production design was inspected.

## What the Eigent reference establishes

Eigent describes itself as built on CAMEL and its backend directly subclasses
CAMEL's `Workforce`. At the pinned revision, the product path uses more than a
worker prompt:

| Mechanism | Pinned Eigent evidence | What it establishes |
|---|---|---|
| Coordinator, task planner, and specialized workers | `backend/app/service/chat_service.py:2670-2885` | The product uses explicit orchestration and role-specific agents. |
| CAMEL task decomposition | `backend/app/utils/workforce.py:381-394` | Task planning is a runtime operation, not only prompt prose added to a worker. |
| Retry and replan | `backend/app/utils/workforce.py:196-209`, `924-934` | Failed work has an explicit recovery policy. |
| Structured task analysis | `backend/app/utils/workforce.py:221-285` | Completion quality is analyzed through a structured CAMEL result with bounded retries. |
| Durable task-state publication | `backend/app/utils/workforce.py:78-135`, `658-681`, `697-745`, `843-894` | Queued, running, and completed steps are persisted around dispatch and publication. |
| Progress-sensitive liveness | `backend/app/utils/workforce.py:1000-1109` | A sliding stall watchdog distinguishes long-running progress from no progress. |
| Tests for ordering and watchdog behavior | `backend/tests/app/utils/test_workforce.py:54-126`, `152-268` | The repository tests persistence-before-dispatch and progress/stall relationships. |

This is valid production-architecture evidence: a real CAMEL-derived product
surrounds its agents with task state, recovery, liveness, and structured
analysis.

It is **not** evidence that the exact Phase 1 prompt proposed in #375 caused
Eigent's behavior or reliability. A search of the pinned backend found no
direct use of the classic `CAMEL_TASK_DONE`, `RolePlaying`, `role_playing`, or
`inception` symbols. Eigent's own worker system messages are short, generic
role descriptions; most of the observable control is in the Workforce layer.
No production outcome metric, controlled prompt ablation, or causal attribution
to those prompt lines was identified in the inspected sources.

There is also an important limit in the quality path. If structured analysis
fails repeatedly for an otherwise completed task, Eigent currently falls back
to accepting the result with `quality_score=80`
(`backend/app/utils/workforce.py:262-285`). This is not a universal hard
acceptance gate and should not be described as one.

## Comparison with current Hermes

Hermes `main` has advanced materially beyond the experiment's frozen baseline.
The comparison must therefore distinguish current behavior from what the A/B
actually tested.

| Concern exposed by Eigent | Current Hermes evidence | Disposition for #375 |
|---|---|---|
| Worker role and completion instructions | `_build_child_system_prompt()` in `tools/delegate_tool.py:1173-1276`; prompt proposal #17561; completion-contract PR #79508 | Prompt work has an existing owner. The frozen A/B did not demonstrate a stable gain from #17561's variants. |
| Multi-agent decomposition and coordination | `delegate_task` supports task batches, orchestrator children, depth limits, live list/steer/stop, and nested delegation; orchestration issue #344 is closed | Already represented in Hermes. Do not reopen Phase 2 from the Eigent reference alone. |
| Machine-readable child output | `tools/delegation_output_schema.py`; `delegate_task` can attach an optional per-task JSON Schema, validate the final response, and perform one bounded correction turn | Existing mechanism. It validates response shape, not the truth of external side effects. |
| Truncation and lifecycle status | `tools/delegate_tool.py:3081-3168` records `exit_reason` and `truncated`; any non-empty non-sentinel summary still receives `status=completed` | The distinction is visible to the parent, but summary truth is not thereby proven. |
| No-progress handling | `_run_single_child()` tracks child iteration, tool, and activity progress and stops refreshing the parent heartbeat when the child is stale | Similar liveness machinery exists. A new watchdog proposal needs a current-main failure witness. |
| Artifact or side-effect truth | #16357 owns structural side-effect verification; #89182 owns a broader opt-in verification gate over existing evidence | Existing owners. This is beyond the strict prompt-only closure of #375. |

## Bounded hypotheses and ownership

The production comparison yields four testable directions, but none authorizes
an unowned implementation by itself:

1. **Progress-narration completion.** #79508 reports a reachable production
   case and owns a small prompt-side completion contract. Evaluate that exact
   incident and candidate rather than creating another Phase 1 wording variant.
2. **False success despite a plausible summary.** The frozen Hermes holdout
   reproduced this behavior. Output-schema validation can constrain shape but
   cannot prove that files, commands, uploads, or state transitions occurred.
   #16357 and #89182 own the structural verification directions.
3. **Worker stalls without progress.** Eigent's sliding watchdog is a useful
   control reference, but Hermes already has progress-aware stale detection.
   Compare observable failure behavior only if a current-main real-path case
   survives that mechanism.
4. **Retry/replan after a failed approach.** Eigent shows that this can be a
   runtime policy rather than a prompt sentence. Before proposing it for
   Hermes, require a reproducible repeated-failure case, verify that the current
   parent/orchestrator cannot already recover, and identify an independently
   closable owner.

## Initial follow-up status

The first ownership check inspected #79508 at
`1dede33ad12ae184ca293fc15160b24c7a18f534`. Its public description contains
two verbatim progress-narration endings and reports an internal same-model
re-dispatch that completed after adding a do-not-stop instruction. It does not
publish the original task, the referenced 1,000-pair corpus, the commands,
sanitized traces, or a replayable fixture. There are no public review comments
or additional commits supplying that material at the inspected revision.

Consequently, the exact production incident cannot currently be replayed
independently from public evidence. This does not contradict the report; it
limits what an external evaluator can claim. The next evaluation must be a
prospective cohort of new progress-narration tasks, frozen before scoring and
reported separately from both #79508's private incident and the completed #375
prompt ablation. It should compare a current-main base with the smallest
current-main composition of #79508's completion-contract block, rather than
running its stale historical branch as though unrelated main changes did not
exist.

## Current adjudication

- **Strict #375 Phase 1:** the Eigent reference does not change the frozen A/B
  result and does not supply RED-to-GREEN evidence for the proposed prompt.
- **Validation value:** high. It corrects the research frame by showing which
  CAMEL-derived controls a production repository actually implements.
- **Implementation value:** conditional. Reuse the invariants as test ideas
  only after a current Hermes witness and ownership check.
- **Next executable work:** preregister a new progress-narration cohort for a
  current-main composition of #79508, because its exact reported incident is
  not publicly replayable; separately, use the frozen false-success cases to
  characterize current `main`'s existing structured-output and verification
  boundaries. Keep both cohorts separate from the completed prompt ablation.

## Reproduction commands for this source audit

The following commands identify the immutable sources used above without
copying Eigent code into Hermes:

```bash
gh api repos/eigent-ai/eigent/commits/main --jq .sha
gh api 'repos/eigent-ai/eigent/contents/backend/app/utils/workforce.py?ref=92f17b596ce2ae27977d6db2f0ed11a81560115f'
gh api 'repos/eigent-ai/eigent/contents/backend/app/service/chat_service.py?ref=92f17b596ce2ae27977d6db2f0ed11a81560115f'
gh api 'repos/eigent-ai/eigent/contents/backend/tests/app/utils/test_workforce.py?ref=92f17b596ce2ae27977d6db2f0ed11a81560115f'
git show d63f996a757f6255fc1454239616ab4b4435e0f5:tools/delegate_tool.py
git show d63f996a757f6255fc1454239616ab4b4435e0f5:tools/delegation_output_schema.py
```
