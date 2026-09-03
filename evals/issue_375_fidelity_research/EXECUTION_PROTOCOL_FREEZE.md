# Issue #375 Fidelity Research — Execution Protocol R1

Status: `FROZEN_EXECUTION_PROTOCOL_NO_PROVIDER_OBSERVATIONS`

Protocol ID: `IP375-FIDELITY-EXECUTION-R1-2026-09-03`

Parent design: `IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`

Prospective amendments: 001 fixed specified task, 002/003 exact historical
repeat-word termination, and 004 transport-attempt cap.

Frozen on: 2026-09-03 (America/Santo_Domingo)

No provider observation made before this freeze.

## 1. Execution identities

### Lane R

| Function | Provider | Exact requested model |
| --- | --- | --- |
| Task specification | None | `PINNED_DATASET_OUTPUT` |
| AI User | Anthropic Messages API | `claude-haiku-4-5-20251001` |
| AI Assistant | Anthropic Messages API | `claude-haiku-4-5-20251001` |
| Solution extraction | Anthropic Messages API | `claude-haiku-4-5-20251001` |
| Primary pair judge | Anthropic Messages API | `claude-sonnet-4-5-20250929` |

The generation model is identical across arms and roles. Every response must
return the exact requested model ID. An alias, substituted model, or omitted
identity invalidates the affected run. The transport is the direct first-party
Messages API with `anthropic-version: 2023-06-01`; Claude Code, Codex, routers,
and subscription CLI transports are not primary Lane R transports because
they do not expose the complete provider-bound request envelope.

The model choices are modern substitutes, not the unavailable 2023 GPT-3.5
and GPT-4 snapshots. The generator/extractor uses the cheapest currently
active exact Anthropic snapshot available in the local integration; the judge
uses a different, exact, active model snapshot. This is a prospective modern
reconstruction and the model substitution remains an explicit fidelity gap.

### Lane P

The opportunity gate, if it reaches model execution, uses current Hermes
`delegate_task` with Anthropic `claude-haiku-4-5-20251001`. It does not reuse
Lane R transcripts or outcomes. No treatment model or second-family
confirmation is selected unless an eligible product RED first survives and a
separate treatment freeze is sealed.

## 2. Frozen sources and inputs

- Dataset: `camel-ai/ai_society@a493cd1636808cbe3cf2389dec79471a1db9e6bc`,
  LFS object SHA-256
  `f8cfd147969ced5a61ba6df3507d6e14348ec5b300e94c1a05ec67d0266c0c12`.
- Paper-era code/prompts:
  `camel-ai/camel@c402032a7f7cd27e196356fbcf413c521a8cb4ca`.
- Paper source: arXiv `2303.17760v2`, source archive SHA-256
  `232dc85336d51948808effa9590087b47ccdb7e4baa364b39120743da050faf2`.
- Sample: the 100 IDs in `frozen_inputs/SAMPLE_MANIFEST.json`.
- Pilot: the first four IDs in `frozen_inputs/FROZEN_INPUTS_SEAL.json`; pilot
  outputs are discarded and those IDs are generated again in the scored run.
- Generation/judge order and the 20-task order-reversal subset:
  `frozen_inputs/SCHEDULE.json`.
- Static source prompt hashes: `frozen_inputs/SOURCE_PROMPT_RECEIPT.json`.
- Per-task effective role-system and initial-relay hashes:
  `frozen_inputs/EFFECTIVE_SYSTEM_PROMPT_MANIFEST.json`.

Only `original_task`, `specified_task`, and the two role names are resolved
from the dataset. Prior instructions, responses, outputs, termination labels,
and message IDs are never passed to a model. The published `specified_task`
is held byte-identical across arms.

## 3. Role-generation contract

The harness reproduces the pinned `RolePlaying` state transition:

1. Each role has its own system prompt and private alternating history.
2. The assistant receives its own rendered system prompt as the first user
   message. Its response is retained in assistant history but discarded from
   the inter-agent transcript.
3. The user receives the rendered user-system prompt plus the historical
   introduction suffix.
4. The user's response is relayed as a user message to the assistant; the
   assistant response is relayed as a user message to the user on the next
   turn.
5. Inter-agent messages never enter the other agent's history as assistant
   messages. Each provider history remains `user, assistant, ...`.

Both arms use temperature `0.2`, `top_p=1.0`, one completion, no streaming,
and no tools. Anthropic does not accept OpenAI presence/frequency penalties or
`n`; those historical zero/default settings are recorded but not transmitted.
Prompt caching and extended thinking are disabled.

Before each role call, the harness applies the pinned GPT-3.5 ChatML counting
algorithm using `cl100k_base` and a 4,096-token limit. The request's
`max_tokens` is the remaining historical budget, at most 4,096. The local
tokenizer implementation is pinned to `tiktoken==0.12.0`; this emulates the
published code path but cannot recover the exact 2023 tokenizer service.

Termination order and semantics follow the pinned generator, including:

- provider/token termination;
- three consecutive user responses without `Instruction:`;
- any assistant response containing `Instruction:`;
- the exact ordered repeat-word nested-loop behavior in Amendment 003;
- saving the user message, then checking `<CAMEL_TASK_DONE>`;
- saving the assistant message; and
- a maximum of 40 saved role messages.

## 4. Extraction and judging

Each transcript is serialized in generation order as alternating
`AI User:`/`AI Assistant:` labeled text. The exact Appendix H solution
extraction text is the extractor system prompt; the serialized transcript is
the sole user message. Extraction uses temperature `0`, no tools or thinking,
and `max_tokens=4096`.

The judge question is the fixed `specified_task`. The Appendix H prompt
template receives the two extracted solutions and the exact published judge
instruction in its `{prompt}` field. The exact Appendix H judge system prompt
is provider `system`. Judging uses temperature `0`, no tools or thinking, and
`max_tokens=2048`.

Assistant order is blinded as `Assistant 1`/`Assistant 2` and follows the
sealed schedule. The first output line must contain exactly two numeric scores
in `[1, 10]`. Higher score wins; equal scores draw. A malformed result is not
content-retried and quarantines that judgment. The sealed 20-task subset is
judged a second time in reversed answer order; the mapped categorical outcome
is compared with the primary outcome.

## 5. Pilot and scored run

The four-record provider pilot exercises both generation arms, extraction,
judging, receipt creation, resume, and quarantine. It is conformance-only,
never inspected for aggregate efficacy, never pooled, and is stored under a
separate pilot namespace. Harness defects require an amendment or R2 protocol;
the invalid pilot remains preserved and a fresh pilot is run.

Only a valid pilot unlocks the 100-task scored run. The scored run has no
efficacy-driven stop and uses no replacement tasks. It may stop only for a
hard resource limit, revoked authorization, credential failure, or protocol
validity failure; that disposition is
`INCONCLUSIVE_PROTOCOL_OR_INFRASTRUCTURE`.

## 6. Retry, quarantine, and validity

Each logical call permits the initial transport attempt plus two retries for
timeouts, connection errors, HTTP 429, and provider 5xx responses, with frozen
2-second and 4-second waits. Authentication, authorization, invalid request,
model mismatch, safety/content response, malformed content, and protocol
violations are not transport-retried.

An unresolved failure in either arm quarantines the entire task pair. No arm
may be regenerated selectively after its content is observed. Primary results
require at least 90 valid task pairs, no arm-specific unresolved-failure count
difference greater than five, no prompt/model identity breach, no manifest or
schedule drift, and no more than four mapped categorical disagreements among
the 20 reversed judgments. Otherwise the scientific disposition is
`INCONCLUSIVE_PROTOCOL_OR_INFRASTRUCTURE` regardless of the win count.

Raw transcripts, extractions, and judge rationales remain private. Public
receipts contain hashes, lengths, usage, latency, scores, terminations, and
aggregate results only. Credentials, account identity, endpoints, usernames,
and machine paths are never written to receipts.

## 7. Frozen resources

| Resource | Pilot ceiling | Complete Lane R ceiling |
| --- | ---: | ---: |
| Paired observations | 4, unscored | 100 scored + 4 rerun pilot records |
| Logical completions | 340 | 8,860 |
| Transport attempts | 1,020 | 26,580 |
| Provider input tokens | 2,000,000 | 50,000,000 |
| Provider output tokens | 1,500,000 | 35,000,000 |
| Wall time | 2 hours | 48 hours |
| First-party API cost | USD 10 | USD 200 cumulative, including pilot |

The runner reserves the maximum possible next-call exposure before dispatch
and stops rather than cross a monetary cap. Cost accounting uses the frozen
standard global rates: Haiku 4.5 at USD 1/input MTok and USD 5/output MTok;
Sonnet 4.5 at USD 3/input MTok and USD 15/output MTok. Cache, batch, fast mode,
and regional premiums are not used. Any price change before execution requires
an evidence refresh and renewed approval, not silent substitution.

Lane P has a separate opportunity-gate ceiling of 20 current-main baseline
observations, 500 logical completions, 1,500 transport attempts, 3 hours, and
USD 15. It cannot spend from the Lane R cap or start before its task/oracle
manifest is sealed.

## 8. Primary analysis

The primary endpoint is original versus ablated categorical wins among valid
non-draw pairs. Report original wins, ablated wins, draws, exact
Clopper-Pearson 95% confidence interval for the original win proportion, and a
two-sided exact binomial test against `0.5`. The implementation is frozen to
`scipy==1.17.1`.

The allowed direction-level result is selected mechanically at alpha `0.05`:

- significant original advantage: `DIRECTIONALLY_COMPATIBLE`;
- significant ablated advantage: `CONTRARY`;
- otherwise: `NON_CONFIRMATORY`;
- any validity-gate failure: `INCONCLUSIVE_PROTOCOL_OR_INFRASTRUCTURE`.

The historical 75%/25% aggregate is a reference, not a null hypothesis or a
success threshold. Length, role-message count, termination type, usage,
latency, order disagreement, failures, and protocol violations are secondary
descriptive outcomes and do not retune the primary endpoint.

## 9. Lane P opportunity gate

Immediately before Lane P, fetch current `origin/main`, record its SHA, inspect
delegation-lifecycle drift, and refresh ownership across #17561, #79508,
#16357, #89182, and newer overlapping work. Candidate cases must arise from a
real Hermes workflow and have an executable external oracle; prompts whose
only purpose is to induce echoing, role flipping, or looping are ineligible.

All candidate cases and oracles are sealed before model execution. Run the
unmodified real `delegate_task` path with its ordinary tools, budgets, skills,
and verification behavior. If no repeated, reachable, unowned RED survives,
stop with `NO_CURRENT_PRODUCT_OPPORTUNITY`. Do not build or test a prompt
treatment. If one survives, write a new treatment freeze and request separate
authorization before any candidate observation or production edit.

## 10. Preflight and authorization

Before the first provider call, the executable preflight must prove all file
hashes, source revisions, package versions, sample/schedule invariants,
credential availability without exposing identity or secret material, and an
empty observation ledger. It writes a sanitized receipt.

This protocol freezes limits but does not authorize spend. The user must
approve the exact models and pilot ceiling after reviewing the preflight.
Completing the pilot does not automatically authorize the 100-task run; the
pilot receipt and projected remaining exposure are presented for a second
approval.

## 11. Change control

This document is immutable after sealing. Any semantic change to a model,
transport, source, prompt, wrapper, sample, ordering, lifecycle, output limit,
retry, exclusion, validity threshold, cost limit, endpoint, or analysis
requires a prospective amendment or a new protocol. Earlier observations are
never silently migrated or pooled.
