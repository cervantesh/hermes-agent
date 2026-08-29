# Independent review record and adjudication

This document is a faithful structured record of the conclusions retained in
the working session. It is **not** presented as a verbatim transcript: raw
reviewer transcripts were not persisted as standalone artifacts.

## Review frame supplied to the reviewers

The reviewers were asked to assess a complete decomposition of
`hermes_cli/update_cmd.py`, with these non-negotiable premises:

1. preserve runtime behavior and the historical import/monkeypatch surface;
2. distinguish mechanical movement from intentional adaptations;
3. keep mutable historical state authoritative on the compatibility facade;
4. prevent a live pre-update process from mixing old executing frames with new
   modules after it mutates its own checkout;
5. test operational effects, not merely imports or formatting; and
6. treat any unproved adjacent guarantee as residual risk, not as silently
   completed work.

## Fable review

Verdict before correction: **REQUEST CHANGES**.

Confirmed:

- all original top-level functions had destinations;
- the extraction was overwhelmingly mechanical;
- the facade preserved the historical callable surface;
- mutable state and updater-generation protection were intentionally handled;
- the extracted gateway-restart data flow was plausible and exercised by the
  existing regression suite.

Blocking finding:

- `update_backup.py` called `logging.getLogger(...)` without importing or
  injecting `logging`. Invalid configuration and snapshot-failure paths could
  therefore raise `NameError`, violating the promise that backup problems do
  not abort an update.

Minor observations:

- the facade did not implement patch propagation for `__delattr__`;
- `_update_compat.py` contained a dead logger declaration.

## Opus review

Verdict before correction: **REQUEST CHANGES**.

Opus independently reproduced the same blocker on two reachable paths:

- an unknown pre-update backup mode; and
- a quick-snapshot failure.

Both raised `NameError` in the candidate while the original implementation did
not. An attempted broader baseline check used an archive without `.git`; Opus
correctly withdrew conclusions from that invalid control instead of treating
the resulting cold-start behavior as a refactor regression.

## Grok review

Verdict before adjudication: **ACCEPT WITH MINOR FOLLOW-UP**.

Grok confirmed the general decomposition, facade compatibility, generation
freeze, and gateway-restart extraction. It did not catch that `logging` was
undefined, so its acceptance was a false negative relative to the independently
reproduced blocker.

One minor finding was valid:

- the modified-skill notice test flattened several source files into one line
  stream, allowing a hint in the next file to satisfy a notice in the previous
  file.

One observation remained speculative rather than a current defect:

- patch propagation for a future internal caller of
  `_write_fleet_restart_pending_marker`. No such reachable internal caller was
  demonstrated in the reviewed tree.

## Adjudication

Final pre-fix verdict: **REQUEST CHANGES**.

Accepted findings:

1. Fix the reachable backup-path `NameError` while preserving the historical
   logger identity.
2. Make the modified-notice invariant respect source-file boundaries.
3. Remove the dead logger declaration from `_update_compat.py`.

Rejected as current requirements:

1. `__delattr__` propagation — theoretical and unsupported by a reachable
   compatibility consumer.
2. Propagation for a hypothetical defining-module caller — no current product
   path depended on it.

## Corrections and TDD evidence

The backup blocker was fixed by routing all four moved logging sites through
`_u().logger`. This both removes the undefined dependency and retains the
historical logger name `hermes_cli.update_cmd`.

RED evidence:

- `test_unknown_config_mode_falls_back_without_aborting` failed with
  `NameError: name 'logging' is not defined`.
- `test_quick_snapshot_failure_never_blocks_update` failed with the same
  `NameError`.

GREEN evidence:

- the two new backup tests plus the two notice tests: `4 passed`;
- the broader related compatibility/restart set: `31 passed`;
- the final focused gate after cleanup: `16 passed`;
- Ruff: `All checks passed!`;
- `compileall`: exit `0`;
- `git diff --check`: exit `0`.

## Post-update verification

`main` advanced by three Desktop-only commits from `3340bbbdad` to
`ac6c8028e0`. No updater or updater-test path in this decomposition was changed
by those commits. The branch was advanced to the new `main` without conflicts.

The same broad test selection was then executed on the candidate and a clean,
detached `main@ac6c8028e0` worktree:

| Tree | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Candidate | 610 | 42 | 42 |
| Clean main | 607 | 42 | 42 |

The 42 failing test node IDs were identical. The candidate's three additional
passes are newly added regression guards. Therefore the broad local comparison
found no candidate-only regression.

