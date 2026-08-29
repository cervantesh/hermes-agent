# Upstream PR CI receipt

## Initial published head

- Head: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- CI run: <https://github.com/NousResearch/hermes-agent/actions/runs/33231400792>
- Result: the full Python job found two failures in
  `tests/test_managed_runtime_resolution.py`.

Both failures described the same mechanical metadata drift. The legitimate
bare `which("uv")` and `which("npm")` calls had moved from
`hermes_cli/update_cmd.py` to `hermes_cli/update_dependencies.py`, while the
test allowlist still named the old file. The guard therefore reported both the
new path as unreviewed and the old path as stale. No runtime behavior failed.

## Correction and current head

- Correction: change the two allowlist keys to
  `hermes_cli/update_dependencies.py`; reasons and commands are unchanged.
- Head: `9f1f78ec478a4598f34057a94b273b372509af32`
- Local directed guard: `7 passed`; Ruff passed; diff-check passed.
- Upstream CI: <https://github.com/NousResearch/hermes-agent/actions/runs/33231606603>
  — success, including the full Python suite, E2E, Windows-only, macOS-only,
  Ruff, ty, security, attribution, and the required-check aggregator.
- Docker: <https://github.com/NousResearch/hermes-agent/actions/runs/33231606375>
  — success.
- Nix: <https://github.com/NousResearch/hermes-agent/actions/runs/33231606317>
  — success.

The correction changes only test metadata. The operational runtime tree
exercised by the before/after Linux and Windows-live evidence remains byte-for-
byte the reviewed `4dbdf314` runtime tree.

## Rebased ready-for-review head

- Refreshed upstream base: `ee742fe1bc828f6456659f67d27bdbeacdebbdd4`.
- Exact PR head: `cd38939500c7aac9110a0cff0d68b244414d65f4`.
- `git range-diff` reports all three original patches unchanged and authorship
  is preserved.
- Local exact-head gate: `56 passed`; Ruff passed; compileall and diff-check
  exited `0`; no changed Python file exceeds 2,000 physical lines.
- Upstream CI: <https://github.com/NousResearch/hermes-agent/actions/runs/33232923520>
  — success, including the full Python suite, E2E, Windows-only, macOS-only,
  Ruff, ty, security, attribution, and required checks.
- Docker: <https://github.com/NousResearch/hermes-agent/actions/runs/33232923216>
  — success on amd64 and arm64.
- Nix: <https://github.com/NousResearch/hermes-agent/actions/runs/33232923194>
  — success.
- Native supervisors: <https://github.com/cervantesh/hermes-agent/actions/runs/33232976850>
  — systemd, launchd, and Windows SCM before/after contracts are all true and
  equivalent on the refreshed base and exact PR head.
