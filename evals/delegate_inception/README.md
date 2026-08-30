# Delegate inception A/B evaluation

This harness measures whether a child-prompt change improves behavior through
the real synchronous `delegate_task` lifecycle. It does not treat the presence
of prompt phrases as evidence of model improvement.

The four hermetic tasks cover:

- evidence-backed work with an on-disk artifact;
- concrete diagnosis rather than a vague summary;
- honest reporting when a required artifact is missing; and
- convergence after the same executable approach fails twice.

Task goals state only the requested outcome and task-specific safety limits.
They intentionally do not repeat the candidate's anti-echo, blocker-reporting,
or change-strategy instructions; otherwise both A/B arms would receive the
behavior being evaluated.

Each task uses programmatic checks over the child result, tool trace, and
disposable workspace. No user files or real `HERMES_HOME` state are modified.

## Run

Run the same model and repetitions against two worktrees. The only intended
variable is the child system prompt.

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
- A baseline failure is required before describing the candidate as a bug fix.
  Otherwise, report the change as defensive prompt hardening.
- Unit tests that inspect prompt text are regression smoke tests, not the A/B
  behavior proof.
