# Real-path updater E2E equivalence — run 33229985934

This directory preserves the successful before/after E2E comparison for the
`update_cmd.py` decomposition.

- Run: <https://github.com/cervantesh/hermes-agent/actions/runs/33229985934>
- Before updater: `ac6c8028e00d01ee2f299ba7fd03329c7f10382d`
- After updater: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- CI harness head: `9f9f731303c5c8747908140331b37b80ab9377b2`
- Result: `success`
- Comparator verdict: `equivalent`
- Created: `2026-08-29T02:51:48Z`
- Completed: `2026-08-29T03:00:35Z`

## Contract exercised

Each frame installed its own updater into a real Python 3.11 virtual
environment and applied `hermes update` to an equivalent one-commit descendant.
The comparison required both frames to satisfy the same five observable
invariants:

1. the real Hermes installation completed;
2. the installed launcher worked before the update;
3. `hermes update` landed on the exact target commit;
4. the launcher worked after the update; and
5. the repository's install/update E2E contract completed successfully.

Both frames returned exit code `0`, every invariant was `true`, and the
machine-readable comparator emitted `"verdict": "equivalent"`.

## Controlled scope

The repository's unmodified E2E currently fails before reaching the updater
because its fake-network proxy produces TLS EOF errors during the unrelated
`npm install` phase. The first two diagnostic attempts are retained as runs
`33229539145` and `33229741884`.

The successful comparison made the same two harness-only adjustments on both
frames:

- skipped Node dependencies during installation; and
- replaced the pipefail-sensitive installer flag probe with an equivalent
  here-string probe.

The workflow verifies that the pre-update harness commit differs from each
original source only in `scripts/install.sh`, and that the update target adds
only `tests/install/install-update-e2e.sh`. No updater implementation file is
changed by those controls. Python installation, virtualenv creation, git
update, target verification, and launcher execution remain real.

This proves parity for the real Linux updater path under that controlled
scope. It does not replace native-supervisor coverage for systemd, launchd, or
Windows SCM.

## Preserved evidence

- `artifacts/`: before and after transcripts, installer logs, outcome JSON,
  and the final comparison report downloaded from GitHub Actions.
- `raw/run.json` and `raw/jobs.json`: GitHub API metadata.
- `raw/logs.zip`: unmodified complete GitHub Actions log archive.
- `raw/logs/`: extracted logs for inspection.
- `raw/workflow.yml`: exact workflow definition used by the run.
- `SHA256SUMS.txt`: integrity hashes for the authoritative evidence files.
