# Native supervisor before/after equivalence

This directory preserves the executable harness and normalized results from
[Actions run 33257891768](https://github.com/cervantesh/hermes-agent/actions/runs/33257891768).
Each isolated job checked out one exact product frame:

- before: `74a95a3ddf0e5e85d464f7cad5e8cd981e258496`;
- after: `a654f00ca05fd7f8237daf916ee3e2ceaf24d91c`.

## Real boundaries exercised

- **systemd:** a temporary `hermes-serve-*` system unit was discovered through
  Hermes' production unit iterator, restarted through real `systemctl`, and
  required to remain active with a new PID.
- **launchd:** a temporary `ai.hermes.gateway` LaunchAgent was bootstrapped in
  the runner's GUI domain, restarted through
  `_restart_launchd_gateway_after_update()`, and required to return under
  launchd supervision with a new PID and no failed label.
- **Windows SCM:** a temporary native service was registered in SCM, then
  stopped and started through Hermes' production Windows service helpers. The
  old process had to disappear and SCM had to report a new running PID.

All fixtures were removed in unconditional cleanup steps. The comparator
required each boolean contract to be non-empty, entirely true, and identical
before/after. Its verdict was `equivalent` for all three supervisors.

## Evidence map

- `equivalence-report.json` — aggregate machine verdict.
- `frames/` — normalized per-frame outcomes and native supervisor diagnostics.
- `workflow.yml` — exact runner matrix, fixture lifecycle, comparison, and
  cleanup logic.
- `harness/` — the three executable supervisor probes.

## Boundary

This proves equivalence at the real supervisor boundaries touched by the
refactor. It does not claim that a complete source update was performed from
inside each temporary service; the separate Linux real-update E2E covers the
full `hermes update` route without a native supervisor fixture.
