# Inherited updater-test failure audit

## Why this receipt exists

The original candidate/base comparison reported `42 failed` on both sides.
That comparison remains useful evidence that the decomposition did not create
those node failures, but it used one direct, single-process pytest invocation.
Hermes' canonical runner isolates test files in subprocesses. The raw number
therefore must not be presented as current CI status or as 42 current defects.

The infographic now presents only the defensible conclusion — candidate and
clean base had identical inherited node outcomes — while this receipt preserves
the original counts, commands, later canonical audit, and independent owners.
No result was deleted.

## Frozen frames

### Historical equivalence frame

- Clean base: `main@ac6c8028e0`
- Candidate: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- Entry point: direct `python -m pytest` over the updater selection in one
  interpreter
- Candidate: `610 passed, 42 failed, 42 skipped`
- Clean base: `607 passed, 42 failed, 42 skipped`
- Failed-node delta: none
- Candidate-only result: three additional passing regression guards

The exact historical failed-node list is retained in
`KNOWN_BASELINE_FAILURES.txt`.

### Canonical classification frame

- Audited revision: `main@3f36c87e1ebdfbf7d14a88229dc9be222c12ea89`
- Relevant test, runner, updater, and gateway files were unchanged through
  `main@4209d371aa1bb8840ce8447555bdd863a1a96c38` on 2026-08-29.
- Environment: native Windows 11 build 26200, Python 3.11.7, pytest 9.1.1,
  psutil 7.2.2, dependencies installed from the locked project environment.
- Canonical result: 61 files, `598 passed`, `12 failed`, `42 skipped`, plus
  `test_cmd_update.py` timing out before pytest emitted its summary.

This later run classifies the inherited test infrastructure. It is not a new
candidate/base equivalence frame and must not be substituted for one.

## Reproduction

Run from a clean checkout at the audited revision with the locked development
environment installed:

```powershell
$files = @(
  (Resolve-Path 'tests/hermes_cli/test_cmd_update.py').Path
  (Resolve-Path 'tests/hermes_cli/test_lazy_command_exports.py').Path
) + (Get-ChildItem 'tests/hermes_cli/test_update*.py' |
  Sort-Object FullName |
  ForEach-Object { $_.FullName })

$selection = $files -join ';'
.\.venv\Scripts\python.exe scripts\run_tests_parallel.py `
  -j 4 --files $selection -- --tb=no -q
```

The canonical runner defaults to a 300-second per-file timeout and one retry.
On the recorded machine the full command takes roughly 15 minutes because the
passing timeout case is killed and retried.

To repeat the historical comparison rather than the canonical audit:

```powershell
$tests = @(
  'tests/hermes_cli/test_cmd_update.py'
  'tests/hermes_cli/test_lazy_command_exports.py'
) + (Get-ChildItem 'tests/hermes_cli/test_update*.py' |
  Sort-Object FullName |
  ForEach-Object { $_.FullName })

.\.venv\Scripts\python.exe -m pytest -q --tb=no $tests
```

Do not compare the two commands' raw failure counts: their process-isolation
contracts differ.

## Classification and causal controls

| Canonical outcome | Owner | Confirmed boundary | Control |
|---|---|---|---|
| 2 failures | [#98037](https://github.com/NousResearch/hermes-agent/issues/98037) | The updater purges and reimports `hermes_cli.gateway`, invalidating the fixtures' old-module process-discovery mock and exposing live developer gateways. | Preventing that unrelated module purge inside the two fixtures changes the exact run to `2 passed in 3.86s`; the live-system guard remains the production-safety backstop. |
| 3 failures | [#98038](https://github.com/NousResearch/hermes-agent/issues/98038) | A simulated launchd fixture reaches POSIX `os.getuid()` on native Windows. | Completing the simulated UID boundary changes the class to three passes. |
| 7 failures | [#98039](https://github.com/NousResearch/hermes-agent/issues/98039) | Real UNIX-socket witness cases execute where `socket.AF_UNIX` and `asyncio.start_unix_server` are unavailable. | The same source revision is green in [hosted Linux CI](https://github.com/NousResearch/hermes-agent/actions/runs/33260379678); the issue requires retaining POSIX execution while excluding only unsupported Windows cases. |
| 1 file timeout | [#98040](https://github.com/NousResearch/hermes-agent/issues/98040) | `test_cmd_update.py` passes, but its runtime narrowly exceeds the canonical 300-second file limit. | Direct pytest: `39 passed in 305.48s`; canonical runner with `--file-timeout 360 --file-retries 0`: `39 passed in 307.5s`. Default runner: two timeouts in `603.91s`. |

The 12 failed assertions are exactly `2 + 3 + 7`. The timeout is listed
separately because the runner could not parse a completed pytest summary for
that file.

## Scope and interpretation

- These are independent test-infrastructure defects, classified by the repo as
  `type/test` and `P3`.
- None of their files is changed by PR #97634.
- None changes the decomposition's behavior-preserving closure predicate.
- The historical `42` counts remain in the machine ledger and reproduction
  instructions as provenance; they were removed only from the explanatory
  infographic and PR summary because those surfaces could imply current red CI.
- Upstream exact-head CI for PR #97634 remains green. The product PR head was
  not changed by this evidence correction.

## Transfer and limitations

The commands above create no persistent service or repository fixture. Run them
in a disposable checkout if live Hermes gateways exist; the repository guard is
expected to block attempts to signal processes outside the test subtree. Remove
only that disposable checkout after collecting results.

Console streams from the original local audit were not published as raw logs.
The exact commands, revisions, summaries, causal controls, and issue receipts
are preserved here; timing may vary by machine. Reproduction succeeds when the
canonical outcomes classify into the same four boundaries, not when wall-clock
durations match exactly.
