# Reproduce the evidence

Run from `C:\dev\hermes-wt-update-refactor` with the candidate file set whose
hashes match `SHA256SUMS.txt`.

## 1. Pin the frame

```powershell
git fetch origin main --prune
git rev-parse HEAD
git status --short --branch
git diff --check
```

Expected head: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`.
Its parent/base is `ac6c8028e00d01ee2f299ba7fd03329c7f10382d`.
The candidate worktree should be clean.

## 2. Focused regression gate

```powershell
python -m pytest -q `
  tests/hermes_cli/test_backup.py::TestRunPreUpdateBackup `
  tests/hermes_cli/test_lazy_command_exports.py `
  tests/hermes_cli/test_update_modified_notice.py `
  tests/hermes_cli/test_update_stale_module_purge.py `
  tests/hermes_cli/test_update_fleet_check_fail_closed.py `
  tests/hermes_cli/test_update_fleet_probe_resume_token.py `
  tests/hermes_cli/test_update_gateway_restart_aborted.py `
  tests/hermes_cli/test_update_launchd_restart_verification.py
```

Expected: `56 passed`.

## 3. Static quality gates

```powershell
python -m ruff check `
  hermes_cli/update_cmd.py `
  hermes_cli/_update_compat.py `
  hermes_cli/update_backup.py `
  hermes_cli/update_dependencies.py `
  hermes_cli/update_desktop.py `
  hermes_cli/update_fleet_restart.py `
  hermes_cli/update_gateway_posix.py `
  hermes_cli/update_gateway_windows.py `
  hermes_cli/update_notices.py `
  hermes_cli/update_orchestrator.py `
  hermes_cli/update_process_guard.py `
  hermes_cli/update_reconciliation.py `
  hermes_cli/update_runtime_refresh.py `
  hermes_cli/update_source.py `
  hermes_cli/update_zip.py `
  tests/hermes_cli/test_backup.py `
  tests/hermes_cli/test_lazy_command_exports.py `
  tests/hermes_cli/test_update_modified_notice.py `
  tests/hermes_cli/test_update_stale_module_purge.py

python -m compileall -q hermes_cli
git diff --check
```

Expected: Ruff reports `All checks passed!`; the other commands exit `0`.

## 4. Structural cap and fleet split

Count every changed Python file and fail if any exceeds 2,000 physical lines.
Then compare the seven top-level functions moved from the parent candidate's
`update_orchestrator.py` against the combined current orchestrator and fleet
modules using attribute-free AST dumps. Expected results:

- `FILES_OVER_CAP 0`;
- `update_orchestrator.py 1846`;
- `update_fleet_restart.py 1178`;
- `MOVED_FUNCTIONS 7`; `MISSING []`; `CHANGED []`.

## 5. Broad updater matrix

```powershell
$tests = @(
  'tests/hermes_cli/test_cmd_update.py',
  'tests/hermes_cli/test_lazy_command_exports.py'
) + (Get-ChildItem tests/hermes_cli/test_update*.py | ForEach-Object {
  $_.FullName
})

python -m pytest -q --tb=no $tests
```

Expected in the reviewed Windows environment:

- candidate: `610 passed, 42 failed, 42 skipped`;
- clean `main@ac6c8028e0`: `607 passed, 42 failed, 42 skipped`;
- the 42 failure node IDs are identical.

Do not infer equivalence from the counts alone. Capture and compare the failed
node IDs. Environment-sensitive failures included absent `psutil`, POSIX/macOS
controls executed on Windows, and existing test-isolation behavior.

## 6. Recompute file identity

```powershell
$package = 'C:\dev\hermes-update-cmd-review-evidence-ac6c8028e0'
$files = Get-Content (Join-Path $package 'reviewed-files.txt')
foreach ($file in $files) {
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLower()
  "$hash  $file"
}
```

Compare the output to `SHA256SUMS.txt`. Any difference requires a fresh review.

## 7. Native-supervisor gate

The real native-supervisor comparison is preserved in `native-supervisors/`
and visible in
[run 33257891768](https://github.com/cervantesh/hermes-agent/actions/runs/33257891768).
It checked out refreshed base `74a95a3ddf` and exact rebased head `a654f00ca0`
independently and exercised ephemeral real systemd, launchd, and Windows SCM
services. Expected aggregate verdict: `equivalent`, with every contract value
true in both frames.

The exact workflow is `native-supervisors/workflow.yml`; executable probes are
under `native-supervisors/harness/`. This is real supervisor-boundary coverage,
not a claim that a complete source update ran from inside each fixture.

Hosted standard-runner evidence is available in
[fresh manual rerun 33228955478](https://github.com/cervantesh/hermes-agent/actions/runs/33228955478),
which checked out candidate `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
directly on all three runners. The previous green run is retained as
[run 33228764944](https://github.com/cervantesh/hermes-agent/actions/runs/33228764944),
with the broad baseline comparison retained in
[diagnostic run 33226997709](https://github.com/cervantesh/hermes-agent/actions/runs/33226997709),
and the focused Windows reconciliation gate in
[run 33227674944](https://github.com/cervantesh/hermes-agent/actions/runs/33227674944).
Those earlier runs are OS-hosted unit/integration evidence; the separate native
run above supplies the real systemd, launchd, and Windows SCM boundary evidence.

## 8. Real-path updater E2E equivalence

The controlled before/after E2E and its complete evidence are archived under
`ci/run-33229985934/` and are visible in
[run 33229985934](https://github.com/cervantesh/hermes-agent/actions/runs/33229985934).
The exact executable workflow is preserved as
`ci/run-33229985934/raw/workflow.yml`.

It checks out `main@ac6c8028e0` and candidate `4dbdf31417` independently,
installs each updater in a real Python environment, applies one equivalent
descendant commit through `hermes update`, and compares five observable
postconditions. The controls and the excluded Node-only phase are documented
in `ci/run-33229985934/README.md`; do not cite this run as native-supervisor or
browser-tool coverage.

## 9. Windows live before/after equivalence

The exact workflow, complete logs, JUnit reports, normalized outcomes, and
machine comparison are archived under `ci/run-33230583743/` and visible in
[run 33230583743](https://github.com/cervantesh/hermes-agent/actions/runs/33230583743).

It independently checks out base `ac6c8028e0` and candidate `4dbdf31417` on
GitHub-hosted Windows and executes all five `*_windows_live.py` updater/restart
files. The comparator fails unless both frames exit `0`, expose the same
non-empty testcase set, and mark every case passed. Expected result: 19 cases
in each frame, no ID/status delta, verdict `equivalent`.

This comparison uses real Windows processes, handles, locked files, process
inventory, migration, and reconciliation. Windows SCM itself is covered
separately by the native-supervisor gate in section 7.
