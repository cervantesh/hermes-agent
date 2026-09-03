# Issue #375 fidelity research harness

This directory implements the frozen two-lane research frame rooted at
`IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`. The active provider
protocol is `IP375-FIDELITY-EXECUTION-R2-2026-09-03 @ bc5dadff484c`. It is
evaluation code, not a Hermes production change.

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
4. Run `preflight.py` as a module. Before R2 authorization it must report
   `anthropic_api_key_present` and `authorization_matches_active_protocol` as
   false; a stale authorization file may still make
   `explicit_run_authorization_present` true, but cannot unlock execution.

The independent current-main Lane P opportunity gate is recorded in
`LANE_P_CURRENT_MAIN_OPPORTUNITY_AUDIT.md` and bound by
`LANE_P_OPPORTUNITY_RECEIPT.json`. Its `NO_CURRENT_PRODUCT_OPPORTUNITY`
disposition makes no provider call and does not alter Lane R. The separate
`LANE_R_MAIN_DRIFT_RECEIPT.json` records why later integration-branch changes
do not change Lane R's pinned source frame.

Each module exposes `--help` with its required paths when invoked with
`python -m evals.issue_375_fidelity_research.<module>`. Local source archives
and the dataset are intentionally not vendored.

## R2 pilot gate

R1 remains immutable evidence of three unsuccessful conformance attempts. R2
does not overwrite or pool those observations. It uses the separately sealed
`frozen_inputs/PILOT_R2_MANIFEST.json` and
`frozen_inputs/PILOT_R2_SCHEDULE.json`: 20 fresh task pairs disjoint from the
100-task scored sample.

The unchanged judge contract still requires exactly two scores in `[1,10]`.
R2 classifies malformed judge output as either `JudgeOutputFormatError` or
`JudgeScoreRangeError`; it never repairs, retries, clamps, or scores that
content. The pilot may continue past at most two such quarantines and passes
only with at least 18 complete pairs, all 20 tasks accounted for, and no other
failure. No pilot efficacy aggregate may be inspected or reported.

## Authorized provider sequence

Copy `RUN_AUTHORIZATION.example.json` to `RUN_AUTHORIZATION.json` only after
the user approves the exact R2 digest, stage, models, 20-task cohort, and
limits. Change `approved` to `true`; do not add identity or credentials to the
file. Supply a current API key only through the process environment.

Run the R2 pilot with the sealed pilot inputs:

```powershell
python -m evals.issue_375_fidelity_research.execute_lane_r `
  --stage pilot `
  --repo <repo> `
  --dataset <dataset> `
  --manifest evals/issue_375_fidelity_research/frozen_inputs/PILOT_R2_MANIFEST.json `
  --schedule evals/issue_375_fidelity_research/frozen_inputs/PILOT_R2_SCHEDULE.json `
  --camel-repo <camel-repo> `
  --supplement-tex <supplement-tex> `
  --paper-pdf <paper-pdf> `
  --paper-source <paper-source> `
  --output-root <new-outside-repo-path>
```

After reviewing the sanitized pilot summary and receiving a second approval,
replace the authorization with the exact `scored` limits and run
`--stage scored`. The budget ledger is persisted before each attempt and must
remain in the same external output root across both stages.

Do not copy the external `private/`, `in_progress/`, or budget state into the
repository. A public evidence packet is prepared only after privacy review.
