# Archived fork CI evidence — run 33228955478

This directory preserves the raw GitHub Actions evidence for the fresh
standard-runner verification of candidate
`4dbdf314179f60999eb94e6ea5bc81367f2ea351`.

- Run: <https://github.com/cervantesh/hermes-agent/actions/runs/33228955478>
- Trigger: `workflow_dispatch`
- Status: `completed`
- Conclusion: `success`
- CI harness head: `05003dff0f05e74984dbdc0a47e39ebdf08c19c7`
- Candidate checked out by every job: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- Created: `2026-08-29T02:26:28Z`
- Completed: `2026-08-29T02:27:13Z`

## Preserved material

- `run.json`: raw run metadata from the GitHub Actions API.
- `jobs.json`: raw metadata for all three jobs.
- `logs.zip`: unmodified log archive downloaded from the GitHub Actions API.
- `logs/`: extracted copy of `logs.zip` for convenient inspection.
- `workflow.yml`: workflow definition used by the CI harness branch.
- `SHA256SUMS.txt`: hashes for the four authoritative downloaded/configuration
  files.

## Raw outcome lines

- Linux: `17 passed in 1.58s`; `All checks passed!`
- macOS: `17 passed in 1.15s`
- Windows: `17 passed in 3.42s`
- Windows restart reconciliation: `4 passed in 2.19s`

The Actions run is attached to the CI harness commit because the workflow
lives on that branch. The checkout records in all three logs independently
show that the tests ran against the candidate SHA above.
