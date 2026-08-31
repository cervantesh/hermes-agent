# Delegate inception A/B evaluation

This harness measures whether a child-prompt change improves behavior through
the real synchronous `delegate_task` lifecycle. It does not treat the presence
of prompt phrases as evidence of model improvement.

The preregistered pilot contains 12 hermetic tasks, three for each failure
mode named by issue #375 and the CAMEL paper:

- role flipping: the worker must inspect sufficient local evidence instead of
  asking the parent to do or clarify the work;
- instruction echo: completion requires an exact on-disk artifact, so merely
  paraphrasing the goal cannot pass;
- flake replies: concrete values and source names are required; and
- infinite loops: a failing primary command must converge through alternate
  evidence without a third identical call.

Task goals state only the requested outcome and task-specific safety limits.
They intentionally do not repeat the candidate's anti-echo, blocker-reporting,
or change-strategy instructions; otherwise both A/B arms would receive the
behavior being evaluated.

Each task uses programmatic checks over the child result, tool trace, and
disposable workspace. No user files or real `HERMES_HOME` state are modified.

The issue also cites Eigent as a production use of CAMEL patterns. The pinned
source comparison in [`EIGENT_PRODUCTION_REFERENCE.md`](EIGENT_PRODUCTION_REFERENCE.md)
separates prompt inheritance from Eigent's orchestration, task state, recovery,
liveness, and quality-analysis mechanisms, then maps those mechanisms to
current Hermes code and existing ownership. It is design evidence, not another
scored arm or proof that the prompt candidate improves Hermes.

## Run

For the paper-aligned pilot, run both worktrees through the paired runner. It
keeps each baseline/candidate observation adjacent, randomizes which arm runs
first with a recorded seed, and is resume-safe. The only intended variable is
the child system prompt.

```bash
python evals/delegate_inception/paired_runner.py \
  --baseline-root /path/to/baseline \
  --candidate-root /path/to/candidate \
  --label haiku-pilot \
  --provider claude-code \
  --model claude-haiku-4-5 \
  --reps 3 \
  --seed 375
```

This produces 36 observations per arm. It is explicitly a pilot: CAMEL's
reported prompt ablation used the same 100-task set and blind comparative
judging. Hermes strengthens the primary endpoint with executable oracles, but
does not treat this smaller sample as a confirmatory replication.

## Long-horizon v2

The short pilot caps children at 12 iterations. The separate v2 suite keeps a
single child (Phase 1 scope) but uses Hermes's production default of 50
iterations. It contains six ten-stage workflows with dependent artifacts and
an unavailable primary source injected at a different early, middle, or late
stage. Completion requires all ten exact artifacts, ten verified transitions,
a final receipt, honest worker-role behavior, and no third identical retry at
the blocked stage.

The v1 tasks and results remain unchanged. Run v2 with a new label:

```bash
python evals/delegate_inception/paired_runner.py \
  --baseline-root /path/to/baseline \
  --candidate-root /path/to/candidate \
  --label haiku-long-v2 \
  --provider claude-code \
  --model claude-haiku-4-5 \
  --suite long \
  --reps 3 \
  --seed 375
```

This yields 18 observations per arm. It tests late drift and convergence, not
multi-agent orchestration: no parent steering, coordinator, or second child is
introduced. Repetitions do not turn six workflow shapes into 18 independent
task designs, so this remains a long-horizon pilot rather than a replication
of CAMEL's 100-task evaluation.

## Pre-registered long-horizon confirmation

`CONFIRMATION_PROTOCOL.md` freezes a separate confirmation before its first
scored observation. It uses twenty new task definitions spanning five workflow
archetypes, one observation per task and arm, rather than repeating the six v2
shapes. Its primary endpoint and stopping rule cannot be changed after results
are inspected.

```bash
python evals/delegate_inception/paired_runner.py \
  --baseline-root /path/to/baseline \
  --candidate-root /path/to/candidate \
  --label haiku-confirmation-v3 \
  --provider claude-code \
  --model claude-haiku-4-5 \
  --suite confirmation \
  --reps 1 \
  --seed 37503
```

The confirmation can establish only the measured single-child behavior. It is
not a replication of CAMEL's multi-agent experiment or evidence for every
provider and model.

## Anti-bypass holdout

After the first confirmation exposed one false-success run in each arm, a new
completion-rule intervention and an unseen holdout were frozen together in
`ANTI_BYPASS_PROTOCOL.md`. Twenty challenge tasks cover five different state
mechanics; four negative controls explicitly require repairing a documented
verifier defect so the rule cannot pass merely by refusing to touch validators.

```bash
python evals/delegate_inception/paired_runner.py \
  --baseline-root /path/to/baseline \
  --candidate-root /path/to/candidate \
  --label haiku-anti-bypass-v4 \
  --provider claude-code \
  --model claude-haiku-4-5 \
  --suite holdout \
  --reps 1 \
  --seed 37504
```

The older single-arm runner remains useful for provider smoke tests and
targeted debugging:

```bash
python evals/delegate_inception/runner.py \
  --repo-root /path/to/baseline \
  --label baseline \
  --provider gemini \
  --model gemini-3.6-flash \
  --reps 3

python evals/delegate_inception/runner.py \
  --repo-root /path/to/candidate \
  --label candidate \
  --provider gemini \
  --model gemini-3.6-flash \
  --reps 3

python evals/delegate_inception/report.py baseline candidate
```

The provider credential must already be present in the environment. Results
are resume-safe and remain ignored under `results/`.

`--provider claude-code` reuses an existing Claude Code login through Hermes's
Anthropic runtime without copying or serializing the OAuth material into the
temporary Hermes home.

For a local Codex CLI login, `--provider codex-app-server` exercises Hermes's
Codex app-server runtime without copying OAuth material into the temporary
Hermes home.

The Codex runtime normally honors the user's configured permission profile.
To run the artifact and recovery arms without changing that profile, add
`--codex-workspace-write`. The evaluator then keeps the Codex sandbox enabled,
allows writes only inside each disposable task workspace, disables network
access, and automatically removes the workspace after grading:

```bash
python evals/delegate_inception/runner.py \
  --repo-root /path/to/candidate \
  --label candidate-write \
  --provider codex-app-server \
  --model gpt-5.6-luna \
  --tasks artifact,recovery \
  --reps 3 \
  --codex-workspace-write
```

## Evidence rules

- Use identical tasks, model, provider, and repetition counts in both arms.
- Record the exact Git head and a digest when a tree is dirty.
- Three repetitions are the minimum; inspect every failed transcript before
  attributing a one-run difference to the prompt.
- Keep the task set, category definitions, repetition count, seed, model, and
  primary pass/fail oracles fixed after the first scored observation.
- Primary evidence is paired task success. Calls, duration, and individual
  failure checks are secondary diagnostics, not substitutes for success.
- Programmatic grading is arm-blind. If subjective judging is added later,
  strip arm labels and prompt-specific formatting before presenting outputs.
- A baseline failure is required before describing the candidate as a bug fix.
  Otherwise, report the change as defensive prompt hardening.
- Unit tests that inspect prompt text are regression smoke tests, not the A/B
  behavior proof.
