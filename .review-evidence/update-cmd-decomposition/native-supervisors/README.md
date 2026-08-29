# Native supervisor before/after equivalence

This directory preserves the executable harness and normalized results from
[Actions run 33232976850](https://github.com/cervantesh/hermes-agent/actions/runs/33232976850).
Each isolated job checked out one exact product frame:

- before: `ee742fe1bc828f6456659f67d27bdbeacdebbdd4`;
- after: `cd38939500c7aac9110a0cff0d68b244414d65f4`.

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
