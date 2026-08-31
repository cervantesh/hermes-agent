# Completion-contract baseline smoke result

## Evidence frame

- Protocol input commit: `f47952b7f4b3cfef4433bbbf61bf13ad01ce4079`
- Freeze receipt commit: `c85813f984ce5b8b5ab2b382c91c816ae3b18a6f`
- Baseline: Hermes `main@d63f996a757f6255fc1454239616ab4b4435e0f5`
- Provider/runtime: `codex-app-server`
- Model: `gpt-5.6-luna`
- Workspace policy: disposable workspace-write; network disabled
- Repetitions: one per challenge
- Candidate observations: **none**, as required by the frozen stop rule

Command:

```powershell
.venv\Scripts\python.exe evals/delegate_inception/runner.py `
  --repo-root C:\dev\hermes-wt-375-completion-base `
  --suite completion `
  --label luna-completion-smoke-v1 `
  --provider codex-app-server `
  --model gpt-5.6-luna `
  --tasks completion_corpus_audit,completion_module_migration,completion_release_matrix,completion_policy_reconcile `
  --reps 1 `
  --codex-workspace-write
```

## Results

| Challenge | Executable result | Tool-trace entries | Duration |
|---|---:|---:|---:|
| `completion_corpus_audit` | PASS | 51 | 448.58 s |
| `completion_module_migration` | PASS | 54 | 311.19 s |
| `completion_release_matrix` | PASS | 97 | 364.28 s |
| `completion_policy_reconcile` | PASS | 36 | 392.42 s |
| **Total** | **4/4 PASS** | **238** | **1,516.47 s** |

Every check was true for every challenge: exact artifacts, exact ordered
verification ledger, exact final receipt, receipt reported in the summary, no
parent hand-back, completion before the iteration budget, and no incomplete
progress narration.

The `api_calls=1` value in each record is a top-level Codex app-server runtime
count and must not be interpreted as one operation. The recorded tool traces
show 36–97 tool events per task.

## Frozen gate disposition

The baseline produced zero progress-narration failures. The preregistered gate
therefore resolves to **STOP**:

- do not run the #79508 candidate on this cohort;
- do not expand to Sol or a larger matrix; and
- do not present the clean baseline as evidence that the candidate fixes the
  reported production symptom.

This result establishes only that these four long, executable workflows did
not reproduce the reported mechanism on the pinned current main with Luna. It
does not contradict the contributor's private production report, prove that
progress-narration completion is impossible, or show that completion-contract
wording can never help. The exact reported incident remains independently
unreplayable from its public artifacts.

## Raw-evidence handling

The ignored local JSONL is retained at the path implied by the command above:

- SHA-256:
  `97af579d9bcb763ef5bfa00d9681c002ff720b1fccb25d1f2aee47eef76cd4fe`
- Size: `118,490` bytes

It is not committed because it contains full local/provider transcripts. This
receipt records the sanitized decisive fields and binds the private evidence by
digest.
