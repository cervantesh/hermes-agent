# Windows live before/after equivalence — run 33230583743

- Workflow run: <https://github.com/cervantesh/hermes-agent/actions/runs/33230583743>
- Base frame: `ac6c8028e00d01ee2f299ba7fd03329c7f10382d`
- Candidate frame: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- Runner: GitHub-hosted Windows
- Result: both frames exited `0`; the same 19 testcase IDs passed in each;
  comparator verdict `equivalent`.

## Observable scope

The workflow executes every repository test file whose name identifies it as
a Windows live updater/restart test:

- `test_venv_holder_windows_live.py`
- `test_desktop_lifecycle_windows_live.py`
- `test_fleet_config_migration_windows_live.py`
- `test_plan_reconciliation_windows_live.py`
- `test_shim_fail_closed_windows_live.py`

These tests exercise real Windows processes, process handles, locked files,
process discovery/classification, migration, and restart-plan reconciliation.
The comparator requires identical non-empty testcase sets, successful statuses,
and exit code `0` in both frames.

This is Windows live-path evidence, but it is not a Windows Service Control
Manager E2E. It also says nothing about systemd or launchd. Native-supervisor
equivalence remains a separate unproven boundary.

## Preserved material

- `artifacts/`: before/after JUnit and normalized outcomes plus the comparator
  report.
- `raw/run.json` and `raw/jobs.json`: GitHub API metadata.
- `raw/logs.zip` and `raw/logs/`: complete downloadable job logs.
- `raw/workflow.yml`: exact workflow definition executed from the CI harness
  commit `ed905cb5ae9e0e62a8638d7597d76dce32c7a71f`.
- `SHA256SUMS.txt`: integrity manifest for the authoritative evidence files.

