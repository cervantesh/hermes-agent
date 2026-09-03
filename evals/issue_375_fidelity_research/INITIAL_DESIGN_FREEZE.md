# Issue #375 Fidelity Research — Initial Design Freeze

Status: `FROZEN_DESIGN_NO_OBSERVATIONS`

Freeze ID: `IP375-FIDELITY-INITIAL-2026-09-03`

Frozen on: 2026-09-03 (America/Santo_Domingo)

Hermes reference: `NousResearch/hermes-agent@4dac5f28af54001b899c9b6fc8ba81cb58da2f0e`

Issue under study: <https://github.com/NousResearch/hermes-agent/issues/375>

This artifact freezes the research question and sequencing. It is not yet an
execution protocol, does not authorize provider calls, and does not authorize
Hermes production changes.

## 1. Why a new frame is necessary

Prior work answered two different questions:

1. A prompt-only Hermes experiment closely matched issue #375 Phase 1, but it
   did not reproduce the CAMEL paper's two-agent RolePlaying system.
2. A fuller CAMEL-derived product experiment implemented more of the paper's
   mechanism, but it was not historically exact and no longer isolated the
   prompt-only change proposed by #375.

Those results remain valid within their published scopes. They must not be
pooled with or retroactively relabeled as observations under this freeze.

The new work keeps two contracts independent:

- **Lane R — source-fidelity reconstruction:** determine whether the published
  Appendix T original-versus-ablated inception-prompt result recurs under a
  prospectively specified modern reconstruction.
- **Lane P — Hermes product validation:** determine whether the exact Phase 1
  proposal in #375 improves a real current-Hermes delegation failure.

A result in Lane R cannot establish product necessity. A result in Lane P
cannot be called a reproduction of the paper.

## 2. Frozen source identities

| Source | Identity | Role |
| --- | --- | --- |
| Hermes integration branch | `4dac5f28af54001b899c9b6fc8ba81cb58da2f0e` | Current product baseline at freeze time |
| Issue #375 body | updated `2026-08-31T21:31:27Z`, normalized UTF-8 SHA-256 `a64224848291d59c04a7f8946035e55bee526fc02b76bab4d249ec295e7a5613` | Product proposal |
| CAMEL paper | arXiv `2303.17760v2`, 2023-11-02 | Primary scientific source |
| Paper PDF | SHA-256 `926c73c2ae9f9abc7612ab58373e428476f4de55db78646ed59de09810db7777` | Human-readable source snapshot |
| Paper TeX source archive | SHA-256 `232dc85336d51948808effa9590087b47ccdb7e4baa364b39120743da050faf2` | Exact prompt and methodology text |
| Paper-era CAMEL repository | `camel-ai/camel@c402032a7f7cd27e196356fbcf413c521a8cb4ca` | Closest reproducible public implementation reference near publication |
| Official AI Society dataset | `camel-ai/ai_society@a493cd1636808cbe3cf2389dec79471a1db9e6bc` | Public task/role sampling frame |
| Official metadata dataset | `camel-ai/metadata@b19a8708cbe95fc3baa631e24bc888a9b89d5b91` | Public task metadata reference |
| Prior prompt-only evidence | `cervantesh/hermes-agent@7a20deaaea1a45642f38408fb560c2464d619d32` | Historical #375 product-adaptation evidence |
| Prior fuller CAMEL evidence | reviewed result `00ecca192d2ef52a4e18666dc2bdcb2d74d84544`; evidence tooling through `34931694f2f44597a862bea48114b316cb09ab71` | Historical CAMEL-derived product evidence |

The original mutable `gpt-3.5-turbo` and GPT-4 service snapshots are not
recoverable. Appendix T also contains a broken TeX reference
(`\secLabel \label{eval1}` rather than a task-list reference) and does not
publish the selected task IDs, raw paired outputs, random seed, or model
snapshot. Therefore Lane R is a **prospective mechanism-faithful
reconstruction**, not an exact historical replication.

## 3. Claim genealogy

| Claim | Owner | What the source demonstrates | Frozen status |
| --- | --- | --- | --- |
| Role flipping, repeated instructions, flake replies, and meaningless loops occurred | CAMEL paper Sections 4.1 and G | Qualitative observations in the paper's two-agent conversations | `SUPPORTED_IN_SOURCE`, not prevalence in Hermes |
| Inception Prompting consists of task specification plus AI User and AI Assistant system prompts | CAMEL paper Section 3.2 | A three-prompt, two-role, alternating protocol | `SUPPORTED_IN_SOURCE` |
| Original prompts beat the Appendix T ablation 75% to 25% under GPT-4 evaluation | CAMEL paper Appendix T, Table 9 | Published aggregate for an incompletely identified sample | `SUPPORTED_AS_PUBLISHED_AGGREGATE` |
| Adding short hardening text to one Hermes child prompt reproduces CAMEL | Issue #375 interpretation | Not tested by the paper as a standalone intervention | `NOT_PRESENT_IN_SOURCE` |
| The four source failure modes are current `delegate_task` product failures | Issue #375 | Anecdotal mapping without a current real-path corpus in the issue | `UNCONFIRMED_PRODUCT_PREMISE` |
| The evaluated prompt-only variants improve Hermes | Prior local studies | No reproducible increment under the frozen tasks/models | `NOT_DEMONSTRATED`, bounded to those variants |
| Full CAMEL cannot help Hermes | No valid owner | Prior work did not establish this universal claim | `NOT_SUPPORTED` |

## 4. Lane R — source-fidelity reconstruction

### 4.1 Primary scientific question

On a prospectively selected public AI Society task sample, using the same
modern model and configuration in both arms, does the original paper-era
Inception Prompting protocol receive more blinded pairwise wins than the
Appendix T ablated protocol?

### 4.2 Frozen mechanism

Both arms must preserve:

- task specification from the paper-era prompt;
- one AI User and one AI Assistant;
- the exact paper-era role names and task text for each selected record;
- separate, symmetric role histories;
- the historical `RolePlaying.init_chat()` assistant-priming state transition;
- strict AI User/AI Assistant alternation;
- the paper's termination checks: three non-instructing user rounds,
  assistant instruction/role reversal, task-done token, token exhaustion, and
  40 total role messages;
- paper-era sampling configuration where supported: temperature `0.2`,
  `top_p=1.0`, one completion, no streaming, and no penalties; and
- no Hermes terminal, file, browser, or model tools.

The sole arm difference is the role-system prompt pair:

- `R-original`: exact original AI Society assistant/user prompt templates from
  the pinned paper-era repository and arXiv source.
- `R-ablated`: exact Appendix T assistant/user prompts from the pinned TeX
  source.

The task-specifier, runtime, task, model, generation parameters, budgets,
solution extractor, and evaluator must otherwise be identical.

### 4.3 Prospective sampling frame

- Use only task IDs and role/task fields from the pinned official AI Society
  dataset; never expose its previously generated conversations to either arm.
- Normalize records and produce a manifest with stable IDs and content hashes.
- Rank eligible records by SHA-256 of
  `IP375-FIDELITY-R1|<stable-record-id>` and select the first 100 distinct task
  records. This matches the 100-task scale described for the paper's AI
  Society agent evaluation without pretending to recover its undisclosed
  Appendix T sample.
- Seal the full manifest before the first provider call.
- A small conformance pilot may use the first four records solely to validate
  wiring. Pilot outputs are never efficacy observations and are not pooled.

### 4.4 Extraction, evaluation, and order controls

- Extract a final solution from each transcript using the exact solution
  extraction prompt published in Appendix H.
- Evaluate paired extracted solutions with the exact Appendix H evaluation
  prompt, using a separately pinned evaluator model.
- Blind arm labels and randomize Assistant 1/2 order deterministically per task.
- Run an order-reversal control on a prospectively selected 20-task subset.
- Record both numeric scores and categorical `original`, `ablated`, or `draw`.
- Report solution length and role-message count so verbosity or conversation
  length cannot be mistaken for correctness without inspection.
- Retain a second, non-primary evaluator or human audit subset only as a
  robustness analysis. It must not replace or tune the frozen primary result.

### 4.5 Endpoint and dispositions

Primary endpoint: the paired original-versus-ablated win distribution from the
frozen primary evaluator.

Report:

- original wins, ablated wins, and draws;
- exact binomial confidence interval for original wins among non-draw pairs;
- two-sided exact sign/binomial test against `0.5`;
- order-reversal disagreement; and
- provider failures, protocol violations, terminations, calls, tokens, and
  latency as separate evidence.

Allowed scientific dispositions:

- `DIRECTIONALLY_COMPATIBLE`: original wins significantly more often than the
  ablated arm under the frozen modern reconstruction.
- `NON_CONFIRMATORY`: the frozen sample does not distinguish the arms.
- `CONTRARY`: the ablated arm wins significantly more often.
- `INCONCLUSIVE_PROTOCOL_OR_INFRASTRUCTURE`: validity requirements fail.

No disposition may be described as reproducing the exact `75%/25%` historical
result or as proving a Hermes product benefit.

## 5. Lane P — issue #375 product validation

### 5.1 Product question

Does the exact Phase 1 prompt-only treatment proposed in #375 improve an
externally verified outcome for a real `delegate_task` workflow that fails on
current `main`, without increasing false success, cost beyond the accepted
threshold, or prompt-cache instability?

### 5.2 Mandatory opportunity gate

Before building or running a candidate:

1. Refresh `origin/main` and audit drift in the real delegation lifecycle.
2. Find a reproducible current-main case for at least one claimed failure mode.
   A synthetic instruction designed to make a model echo, flip roles, or loop
   is insufficient by itself.
3. Run the case through the real `delegate_task` entry point with its ordinary
   tools, iteration budget, `/goal` or verification behavior, relevant skill,
   and other authorized production routes.
4. Verify failure through an external oracle. Model prose and stylistic labels
   are not the primary outcome.
5. Check current owners including #17561, #79508, #16357, #89182, and any newer
   issue/PR sharing the demonstrated cause.

If no valid, unowned product RED survives, Lane P stops as
`NO_CURRENT_PRODUCT_OPPORTUNITY`. Lane R may still proceed as research, but no
Hermes treatment freeze or production PR is permitted.

### 5.3 Treatment gate after a product RED

Only after the opportunity gate passes may a separate sealed treatment
protocol be created. It must:

- compare current Hermes with the exact smallest prompt delta claimed by
  #375, not silently substitute the full CAMEL role loop;
- identify every candidate sentence and whether it is exact CAMEL text, a
  #375 adaptation, or a new local hypothesis;
- use matched task, tools, budget, model, order, and externally executable
  oracle;
- include unseen confirmatory tasks and a second compatible model family;
- measure verified success, false success, calls, tokens, latency, and prompt
  bytes; and
- preserve Hermes's per-conversation prompt stability and strict role
  alternation.

If Lane R suggests a different mechanism, such as two-role interaction or task
specification, that mechanism requires its own external-method-adaptation
freeze. It cannot replace the #375 prompt-only candidate after results are
known.

### 5.4 Product dispositions

- `IMPLEMENTATION_OPPORTUNITY`: repeated current-main RED becomes GREEN under
  the frozen prompt-only treatment, clears product thresholds, survives
  controls, and has no existing owner.
- `EXISTING_MECHANISM_OR_OWNER_SUFFICIENT`: a current authorized path or active
  owner closes the demonstrated need.
- `NO_DEMONSTRATED_INCREMENT`: a valid comparison does not show the required
  improvement.
- `NO_CURRENT_PRODUCT_OPPORTUNITY`: no eligible baseline failure exists.
- `INCONCLUSIVE`: provider, protocol, sample, or oracle validity is inadequate.

Only `IMPLEMENTATION_OPPORTUNITY` can support a draft production PR, and only
for the smallest demonstrated product delta.

## 6. Model, provider, and cost gate

This initial design intentionally does not select mutable hosted model
snapshots. Before any model observation, an execution-protocol freeze must pin:

- exact provider and returned model identity for task specification, both role
  agents, extraction, and judging;
- provider API mode and effective request parameters;
- byte hashes of every effective provider-bound system and user prompt;
- credentials preflight result without credential material;
- maximum observations, calls, tokens, wall time, and monetary exposure; and
- retry, rate-limit, transport-failure, and quarantine rules.

The generation model must be identical across original and ablated Lane R
arms. The primary evaluator must be independent of arm order and fixed before
outputs are inspected. A provider alias that silently changes model identity
invalidates comparability unless the provider returns a stable resolved model
identifier recorded in every receipt.

Prior authorization for observations under another freeze does not authorize
spend under this one.

## 7. Evidence and privacy contract

Every observation must record source IDs, freeze IDs, task hash, arm, order,
effective prompt hashes, model identities, parameters, termination reason,
protocol violations, usage, latency, output hashes, evaluation, and validity.

Provider/credential/rate-limit/transport failures are retained but quarantined
from scientific and product outcomes. Raw transcripts remain private unless
separately reviewed and authorized for publication. Public receipts must remove
credentials, endpoints, usernames, machine paths, and provider-private content
while preserving independently checkable hashes and aggregates.

## 8. Sequential execution plan

1. Implement deterministic source extraction, task-manifest construction, and
   conformance tests without provider calls.
2. Seal the execution protocol, exact model identities, prompt hashes, sample
   manifest, evaluator, budget, and analysis code.
3. Run the four-record Lane R conformance pilot; repair only harness defects in
   a new protocol version and never pool invalid pilot output.
4. Run the frozen 100-task Lane R sample without efficacy-driven early stop.
5. Analyze and publish only the allowed bounded scientific disposition.
6. Independently run Lane P's current-main opportunity gate.
7. Stop Lane P if no real product RED survives. Otherwise create a separate
   treatment freeze before implementing or observing a candidate.
8. Compare Lane R and Lane P only at the interpretation layer; never pool their
   outcomes.

## 9. Non-goals

- claiming access to the original 2023 hosted model snapshots or undisclosed
  Appendix T task sample;
- treating modern-model agreement as an exact historical replication;
- using a scientific reconstruction to justify a Hermes production change;
- weakening the Hermes baseline to create headroom;
- evaluating shared memory, Eigent Workforce, retry/replan, durable resume,
  debate mode, or general multi-agent architecture under this freeze;
- adding a new core tool, telemetry, or user-facing configuration; or
- publishing provider transcripts or credentials.

## 10. Change control

This document is immutable after sealing. Any semantic change to sources,
sampling, prompts, lifecycle, models, evaluator, endpoint, thresholds,
exclusions, or stopping rules requires an amendment or a new freeze before the
affected observations.

Integration drift is classified as `NO_IMPACT`, `EVIDENCE_REFRESH`, or
`CONTRACT_CHANGE`. Lane R source drift does not silently update the pinned
paper frame. Lane P must refresh current `main` immediately before its product
opportunity run.

Future artifacts must cite this freeze as
`IP375-FIDELITY-INITIAL-2026-09-03 @ <digest-prefix>` and preserve all earlier
#375 evidence under its original claims.
