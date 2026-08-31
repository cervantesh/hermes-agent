# Immutable source and ownership audit

## Pinned revisions

| Source | Revision | Purpose |
|---|---|---|
| Hermes | `64cc87e6681a3db4e158ed8b999ff77ba0b9d28a` | Product baseline at research start |
| CAMEL paper-era repository | `c402032a7f7cd27e196356fbcf413c521a8cb4ca` | Prompt and RolePlaying implementation nearest the paper publication window |
| CAMEL current `master` | `e88b5eebe9f8bb5597196384c818fb4e3c63b25c` | Current API and implementation comparison |
| Eigent | `92f17b596ce2ae27977d6db2f0ed11a81560115f` | Production-architecture comparison |
| Paper | arXiv `2303.17760` | Primary protocol and methodology source |

The paper-era CAMEL commit was selected by repository history at the end of
2023-04-01. It is a reproducible historical implementation reference, not a
claim that it is the exact private environment used for every paper result.
The original mutable `gpt-3.5-turbo` service snapshot is not recoverable, so
this study is a conceptual replication, not an exact replication.

## Paper-faithful CAMEL contract

The primary source defines Inception Prompting as three prompts:

1. a task-specifier prompt;
2. an AI Assistant system prompt; and
3. an AI User system prompt.

The task specifier makes the task concrete. The AI User provides one
instruction at a time. The AI Assistant supplies a specific solution and
requests the next instruction. The AI User alone emits
`<CAMEL_TASK_DONE>` when satisfied. The paper states a maximum of 40 messages
to bound cost. The historical repository example used a limit of 50 turns;
the research protocol follows the paper's 40-message cap and records this
difference rather than silently choosing the convenient value.

The paper's Appendix T ablations are not equivalent to deleting all role
instructions. They include an assistant-response-format modification and a
task-planner addition. Any study called paper-faithful must preserve that
distinction.

Historical implementation evidence:

- `camel/agent/role_playing.py` constructs task-specifier, assistant, and user
  agents and alternates their messages;
- `prompts/ai_society/task_specify_prompt.txt` bounds the specified task to 50
  words;
- `prompts/ai_society/assistant_prompt_with_task.txt` anchors the assistant
  role and requires `Solution: ... Next request.`;
- `prompts/ai_society/user_prompt_with_task.txt` anchors the user role,
  requires `Instruction`/`Input`, and owns `<CAMEL_TASK_DONE>`; and
- `examples/ai_society/role_playing.py` demonstrates the loop and termination.

No CAMEL code or prompt text is copied into Hermes production code by this
research. The source is Apache-2.0, but provenance and experimental isolation
remain explicit.

## Eigent production contract

At the pinned revision Eigent subclasses CAMEL `Workforce` and uses
`camel-ai[eigent]==0.2.91a5`. Its product path contains more than RolePlaying:

- coordinator/task planner and specialized workers;
- task decomposition and dependency updates;
- retry and replan through `FailureHandlingConfig`;
- queued/running/completed/failed state publication;
- durable subtask-step persistence before runtime publication;
- structured task analysis with bounded retries; and
- progress-sensitive stall detection.

Important negative evidence: if normal task-quality analysis fails three
times, the pinned Eigent code accepts the result with `quality_score=80`.
Eigent therefore does not establish a universal hard verification gate.

The Workforce study evaluates these operational controls with deterministic
fault injection. It does not attribute Eigent's product behavior to the
classic CAMEL prompt.

## Current Hermes mechanisms

At the pinned Hermes SHA:

- `_build_child_system_prompt()` starts at `tools/delegate_tool.py:1230`;
- orchestrator children have explicit spawning guidance and bounded depth;
- `delegate_task` supports batches, background execution, retained children,
  `list`/`steer`/`stop`, worktree isolation, provider/model selection, and
  progress-sensitive liveness;
- per-task `output_schema` validates final-response shape and permits one
  bounded correction turn;
- output schema does not verify external side effects;
- `agent/verification_evidence.py` is deliberately passive; and
- `verify_on_stop` is opt-in and defaults to false.

The evaluator must compare against these current mechanisms rather than the
much smaller delegation surface described when issue #375 was opened.

## Current ownership

| Boundary | Current public owner/status | Research disposition |
|---|---|---|
| Prompt-only hardening | #375 open; #17561 open but stale/red | Existing hypothesis; do not duplicate as a fix |
| General orchestration | #344 closed | Current Hermes behavior is the baseline |
| Acceptance criteria | #356 closed via `/goal` | Not proof of independent artifact verification |
| Debate/iterative refinement | #376 open; #20158 closed | Potential owner if RolePlaying shows value |
| Shared memory | #377 open | Out of the CAMEL fidelity MVP |
| Side-effect verification | #16357 open | Owner for structural truth, not RolePlaying |
| Verification gate/Best-of-N | #89182 open, needs decision | Owner for broader opt-in verification policy |

Research results may clarify these owners but do not silently expand or close
their contracts.

