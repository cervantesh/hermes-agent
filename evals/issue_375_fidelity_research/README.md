# Issue #375 fidelity research harness

This directory implements the frozen two-lane research frame rooted at
`IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`. It is evaluation code, not
a Hermes production change.

## Safety boundary

- Provider-free commands may run without authorization.
- Provider execution requires both an ephemeral `ANTHROPIC_API_KEY` in the
  process environment and an exact `RUN_AUTHORIZATION.json` matching the
  requested stage.
- Raw task text, transcripts, extractions, and judge rationale belong outside
  the repository. Only sanitized receipts may be copied back after review.
- The pilot is never an efficacy sample. The scored run requires separate
  approval after the pilot.

## Recreate the isolated runtime

```powershell
python -m venv D:\path\outside-repo\ip375-research-venv
D:\path\outside-repo\ip375-research-venv\Scripts\python.exe -m pip install `
  -r evals\issue_375_fidelity_research\RUNTIME_REQUIREMENTS.txt `
  pytest==9.0.2
```

Keep the virtual environment outside the checkout so it cannot enter a diff.

## Tests

```powershell
$tests = Get-ChildItem tests\evals -Filter 'test_issue_375_fidelity_*.py' |
  Select-Object -ExpandProperty FullName
D:\path\outside-repo\ip375-research-venv\Scripts\python.exe -m pytest `
  --confcutdir=tests/evals $tests -q
ruff check evals/issue_375_fidelity_research tests/evals
ruff format --check evals/issue_375_fidelity_research tests/evals
```

`--confcutdir` keeps this narrow research runtime from importing unrelated
Hermes test dependencies. Full Hermes CI remains a separate repository gate.

## Provider-free sequence

1. Run `freeze_inputs.py` against the pinned dataset, CAMEL checkout, and arXiv
   TeX source. Its output must match `frozen_inputs/FROZEN_INPUTS_SEAL.json`.
2. Run `freeze_effective_prompts.py`; its output must match the effective
   prompt seal.
3. Run `offline_conformance.py` twice with an output directory outside the
   repository. The second pass must reuse four completed pairs with zero new
   fixture completions.
4. Run `preflight.py`. Before authorization it must report only the credential
   and authorization gates as absent.

Each module exposes `--help` with its required paths. Local source archives and
the dataset are intentionally not vendored.

## Authorized provider sequence

Copy `RUN_AUTHORIZATION.example.json` to `RUN_AUTHORIZATION.json` only after
the user approves the exact stage, models, and limits. Change `approved` to
`true`; do not add identity or credentials to the file. Supply the API key only
through the process environment.

Run `execute_lane_r.py --stage pilot ... --output-root <outside-repo-path>`.
After reviewing the sanitized pilot summary and receiving a second approval,
replace the authorization with the exact `scored` limits and run
`--stage scored`. The budget ledger is persisted before each attempt and must
remain in the same external output root across both stages.

Do not copy the external `private/`, `in_progress/`, or budget state into the
repository. A public evidence packet is prepared only after privacy review.
