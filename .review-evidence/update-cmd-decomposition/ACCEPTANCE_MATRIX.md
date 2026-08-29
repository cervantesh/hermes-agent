# Acceptance matrix

| Claim | How it was checked | Verdict | Raw evidence |
|---|---|---|---|
| The published branch is rebased onto the refreshed upstream main without patch drift | exact base/head inspection plus `git range-diff` from the previously reviewed series to the rebased series | **confirmed** | base `74a95a3ddf0e5e85d464f7cad5e8cd981e258496`; head `a654f00ca05fd7f8237daf916ee3e2ceaf24d91c`; all three patches `=` |
| Every original updater function still has a destination | AST inventory of original `update_cmd.py` versus facade and extracted modules | **confirmed** | `OLD_FUNCTIONS 161`; `MISSING 0` |
| Mechanical movement dominates the change | Attribute-free AST body comparison | **confirmed** | `IDENTICAL 155`; `ADAPTED 6` |
| Every adaptation is accounted for | Source diff of the six adapted functions | **confirmed** | `_m` docstring only; four facade state/logger adaptations; `_cmd_update_impl` gateway block extraction |
| The historical module surface remains available | AST top-level-name inventory plus runtime `hasattr` against the facade | **confirmed** | `ORIGINAL_TOP_LEVEL_NAMES 195`; `PRESENT 195`; `MISSING []` |
| Historical monkeypatches reach moved consumers | Static consumer/reference audit plus executable facade tests | **confirmed** | `MODULES_CHECKED 13`; `MISSING_PROPAGATIONS 0`; focused tests pass |
| Every changed Python file respects the structural cap | Exact physical line count across the candidate diff | **confirmed** | cap `2000`; maximum `1894`; `FILES_OVER_CAP 0` |
| The fleet split is mechanical | Function-level AST comparison against parent `026b98b9eb` | **confirmed** | `7/7` moved bodies identical; none missing or changed |
| A live updater cannot purge one of its newly extracted executing modules | Exact expected-module comparison against `_STALE_PURGE_PROTECTED` plus regression test | **confirmed** | `EXPECTED 15`; `MISSING_PROTECTION []` |
| Backup failures cannot abort the update through the moved logger calls | TDD regressions for invalid mode and snapshot failure | **confirmed** | RED: two `NameError`s; GREEN: both tests pass |
| The modified-skill hint cannot be borrowed across files | Per-file invariant helper plus negative control | **confirmed** | `test_notice_hint_cannot_be_borrowed_from_the_next_file` passes |
| Focused compatibility gate is green | Focused `pytest` command in `REPRODUCE.md` | **confirmed** | `56 passed in 9.07s` |
| Broad local behavior is equivalent to clean main | Same test selection on candidate and detached clean main | **confirmed** | candidate `610/42/42`; main `607/42/42`; identical 42 failures |
| The exact candidate passes the focused decomposition gate on hosted Linux, macOS, and Windows | Fresh manually dispatched fork-only workflow with the candidate fixed by SHA | **confirmed** | checkout `4dbdf314179f60999eb94e6ea5bc81367f2ea351`; `17 passed` on each OS; [rerun 33228955478](https://github.com/cervantesh/hermes-agent/actions/runs/33228955478) |
| Hosted Windows broad behavior matches the baseline | Same broad updater selection on candidate and base | **confirmed** | candidate `635/19/40`; base `632/19/40`; identical 19 failures and three additional candidate passes |
| Windows restart reconciliation remains green after extraction | Focused hosted-Windows guard set in the fresh rerun | **confirmed** | `4 passed`; [rerun 33228955478](https://github.com/cervantesh/hermes-agent/actions/runs/33228955478) |
| The refactored updater preserves the observable real-path Linux update contract | Before/after execution of the repository install/update E2E; each frame ran its own updater against an equivalent one-commit descendant | **confirmed within controlled scope** | both exit `0`; both `5/5` invariants true; comparator `equivalent`; [run 33229985934](https://github.com/cervantesh/hermes-agent/actions/runs/33229985934) |
| The refactored updater preserves the repository's Windows live updater/restart behaviors | Run all five Windows-live files against exact base and candidate SHAs; compare non-empty testcase IDs, statuses, and exits | **confirmed within live-test scope** | both exit `0`; identical `19/19` passing cases; comparator `equivalent`; [run 33230583743](https://github.com/cervantesh/hermes-agent/actions/runs/33230583743) |
| The E2E result depends on modified updater implementation | Static name-only guards around both harness commits | **refuted** | source control touches only `scripts/install.sh`; target control adds only `tests/install/install-update-e2e.sh`; updater files remain at the reviewed SHAs |
| Hosted POSIX broad results show a deterministic candidate-only regression | Candidate/base comparison plus repeat-run inspection | **not observed** | all stable failures are inherited; only timing-sensitive `test_update_wedged_gateway` nodes varied between attempts |
| Static quality gates pass | Ruff, compileall, and diff whitespace checks | **confirmed** | `All checks passed!`; compile exit `0`; diff-check exit `0` |
| The evidence did not leave temporary reviewer artifacts in the worktree | explicit filesystem checks | **confirmed** | `BASELINE_EXISTS=no`; `SERENA_EXISTS=no` |
| The exact rebased head preserves the real native-supervisor restart boundary on Linux, macOS, and Windows | Before/after ephemeral services on systemd, launchd, and Windows SCM; require discovery, real restart, PID rotation, supervised/running post-state, cleanup, and identical contracts | **confirmed within supervisor-boundary scope** | base `74a95a3ddf0e5e85d464f7cad5e8cd981e258496`; head `a654f00ca05fd7f8237daf916ee3e2ceaf24d91c`; all three comparators `equivalent`; every contract assertion true; [run 33257891768](https://github.com/cervantesh/hermes-agent/actions/runs/33257891768) |

## Overall verdict

**Confirmed locally, through a controlled real-path Linux E2E, Windows live
before/after tests, and real three-platform supervisor-boundary probes.** The decomposition meets
the closed technical contract in the available static, unit, integration,
clean-baseline, and native-supervisor evidence. The native run covers real
systemd, launchd, and Windows SCM restart/verification boundaries, but not a
complete source update launched from inside each fixture. The E2E deliberately
excluded unrelated Node installation after two symmetric fake-network TLS
failures; that limitation is recorded in its archived evidence.
