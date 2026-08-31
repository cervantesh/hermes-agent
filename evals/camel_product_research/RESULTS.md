# Results: CAMEL and Eigent product research

## Executive result

The evaluated CAMEL-template-derived Hermes adaptation did not demonstrate an opportunity
to improve verified success over current Hermes in the frozen task catalog.
Both Sonnet and Haiku baselines reached 7/7. On three Haiku ceiling tasks, the
adaptation reached 1/3 versus the matching baseline's 3/3 and produced two
externally incorrect
`task_done` outcomes and used 3.74 times as many API calls. Its separately run
batch accumulated 8.41 times the baseline wall time; that is an observed ratio,
not a controlled latency treatment estimate.

A post-signal Sonnet robustness check passed 2/2, showing that correctness is
model-dependent. It still used 2.92 times as many calls and 2.02 times the
separately observed wall time as the already-successful baseline. These small samples do not prove
that CAMEL cannot help another distribution. They do reject a default or
general-purpose adoption claim based on the evidence collected here.

Eigent's pinned Workforce tests passed, but its useful control plane is not a
single missing Hermes feature. Hermes already has durable async dispatch,
completion replay, delivery claims, deduplication, and a stall watchdog. The
remaining task-level retry/replan and restartable execution boundaries need
independent evidence. Eigent's `quality_score=80` fallback is unsuitable as a
hard completion gate.

## Source and adapter validity

- Hermes baseline: `64cc87e6681a3db4e158ed8b999ff77ba0b9d28a`
- Each receipt records a later evaluation commit containing its freeze/harness;
  the production-code delta from the baseline remained empty outside
  `evals/camel_product_research/` and `.lider/`.
- CAMEL paper-era prompt source:
  `c402032a7f7cd27e196356fbcf413c521a8cb4ca`
- Eigent: `92f17b596ce2ae27977d6db2f0ed11a81560115f`
- All three CAMEL source templates were loaded by `git show` from the pinned source.
- The runtime used a task specifier, separate AI User and AI Assistant agents,
  strict alternation, AI-User-owned exact `<CAMEL_TASK_DONE>`, and a 40-message
  cap.
- The historical hidden assistant-priming call from `RolePlaying.init_chat()`
  was not reproduced, and Hermes composed its own guidance around each role
  prompt. Raw source-template hashes were retained; effective provider-bound
  prompt bytes were not.
- The AI Assistant used Hermes file and terminal tools. This is a
  product-oriented adaptation of the paper's role protocol, not an exact
  execution of the historical library or hosted 2023 chat-only runtime.
- Correctness came from executable workspace oracles, never from the AI User,
  AI Assistant, receipt prose, or a model judge.

The adapter and oracles passed 14 tests before valid observations. Those tests
did not cover the omitted historical priming call or effective-prompt identity.
The post-review package adds fail-closed cohort-identity and evidence-export
tests while retaining the real-process owner-death witness.

## Invalid preflight

The first Gemini 2.5 Flash attempt is invalid. One simple task completed before
six runs exhausted a free-tier quota. The original worker did not fail closed
on provider errors, so the whole batch was quarantined rather than partially
rescored. Version 2 added explicit provider-failure invalidation before the
Claude runs. No Gemini observation contributes to the conclusions.

## Current-Hermes opportunity baselines

| Model | Verified | False success | API calls | Duration |
|---|---:|---:|---:|---:|
| Claude Sonnet 4.6 | 7/7 | 0/7 | 74 | 351.93 s |
| Claude Haiku 4.5 | 7/7 | 0/7 | 104 | 377.29 s |

Because every task passed, the frozen sequential gate prohibited running CAMEL
as an efficacy candidate on these cohorts. There was no positive-success
headroom. The later CAMEL sample is explicitly a ceiling non-inferiority and
cost characterization.

## CAMEL-derived ceiling characterization on Haiku

| Task | Baseline | CAMEL-derived adaptation | False success | Call ratio | Observed wall-time ratio |
|---|---:|---:|---:|---:|---:|
| `simple_manifest` | pass | fail | yes | 2.50x | 1.49x |
| `ambiguous_handoff` | pass | pass | no | 15.17x | 33.94x |
| `false_success_shortcut` | pass | fail | yes | 1.72x | 1.28x |
| **Aggregate** | **3/3** | **1/3** | **2/3** | **3.74x** | **8.41x** |

There were two discordant pairs, both losses for CAMEL and none in its favor.
With only two discordances, a two-sided exact McNemar test is `p=0.5`; the
sample is too small for a population claim. The direction and severity are
nevertheless product-safety evidence because both failures were nominally
reported as complete.

### Observed failure traces

1. **The recorded task specification changed the contract.** On
   `simple_manifest`, the original task required the exact path
   `output/result.json`. The task specifier invented a project-root
   `manifest.json`, schema fields, and checksum work before either role read
   the repository. The pair produced the right JSON at the wrong path and
   terminated successfully.
2. **Role satisfaction was not external verification.** On the seven-stage
   anti-bypass task, every stage artifact was correct and verified, but the
   assistant stopped one required `advance.py` call early. The AI User treated
   `verified 7/7` as the final receipt, emitted `<CAMEL_TASK_DONE>`, and the
   actual final receipt never existed.
3. **Open-ended specification expanded the requested scope.** The handoff task
   required one five-field JSON receipt, while the recorded specified task
   requested a repository audit, CI validation, documentation, cleanup, a
   commit, and potentially a tag. The candidate eventually passed the external
   oracle after 91 calls and 1,155 seconds, versus 6 calls and 34 seconds for
   baseline. The sanitized evidence proves the specified-task expansion and
   oracle result, not every extra artifact claimed in the discarded transcript.

The exact termination token bounded the conversation but did not make
termination truthful. The AI User judged assistant prose, not external state.

## Post-signal Sonnet robustness check

| Task | Baseline | CAMEL-derived adaptation | Call ratio | Observed wall-time ratio |
|---|---:|---:|---:|---:|
| `simple_manifest` | pass | pass | 3.00x | 1.75x |
| `false_success_shortcut` | pass | pass | 2.90x | 2.10x |
| **Aggregate** | **2/2** | **2/2** | **2.92x** | **2.02x** |

Sonnet's task specifications stayed grounded and both external oracles passed.
This means the Haiku failures are not deterministic properties of the prompt
text alone. It does not produce a benefit: the matching baseline already
passed with materially fewer API calls and lower separately observed wall time.

## Eigent and Hermes operational results

- Eigent pinned Workforce suite: 38 passed, 3 test warnings.
- Hermes async-delegation and completion-delivery suites: 52 passed, 1 skipped.
- Added real-process witness: after the owner process dies while a child is
  running, Hermes recovers the record as `outcome unknown`; it does not resume
  execution from a durable step frontier.

The source inspection and native suites locate the boundary as follows; they do
not compare both products on one shared end-to-end fault:

- Hermes durability protects dispatch metadata and terminal delivery.
- Eigent adds task-level retry/replan and persisted task-step representation.
- Neither evaluated default is an external side-effect truth gate.
- Eigent's exhausted quality analyzer accepts with score 80; that behavior
  must not become Hermes's completion authority.

## Current-main drift

Before adjudication, upstream `main` was refreshed to
`cd2bd160579d5240e52d01e2f735da55ff4242ef`; the adversarial review later
checked `26f178e5fa78c691cadf847058ef1d55a707bfb0`. The frozen baseline is an
ancestor of both. Two intervening commits changed provider-failure classification in
`tools/delegate_tool.py`: failures now report `failed/error` rather than being
misclassified as completed or max-iterations. They do not change the
successful Claude task path, CAMEL prompts, fixtures, or external oracles.
They reinforce, rather than invalidate, the quarantine of the Gemini batch.

## Limitations

- Seven synthetic, hermetic tasks and one repetition per primary opportunity
  baseline are not a broad benchmark.
- Only three Haiku ceiling tasks and two post hoc Sonnet tasks ran the adaptation.
- The treatment and baseline used different execution paths and available
  budgets, so the observations describe full paths rather than isolate a CAMEL
  component effect.
- Candidate and baseline batches were sequential rather than interleaved;
  wall-time ratios are uncontrolled observations.
- The adapter omitted historical assistant priming and did not retain hashes of
  Hermes's effective composed system prompts.
- Both valid models are from one provider family. Gemini could not sustain the
  protocol; Codex app-server cannot inject the historical role text as a native
  system prompt, so it was not mislabeled as cross-family confirmation.
- CAMEL token totals were unavailable through this evaluator path. Calls and
  wall time are exact; token-cost comparison remains unverified.
- The tool-using assistant is appropriate for Hermes product evaluation but
  differs from the paper's original chat-only architecture and model snapshot.
- The task catalog found no baseline failure opportunity. It therefore cannot
  estimate a positive treatment effect where CAMEL might genuinely help.

The defensible conclusion is bounded: this evaluation found no evidence to
justify implementing the evaluated adaptation in Hermes now, and it found
concrete default-adoption risks. It is not an evaluation of historically exact
CAMEL, a component-level causal estimate, or evidence that every CAMEL
mechanism lacks value in every future cohort.
