# `update_cmd.py` decomposition — public review evidence

This directory preserves the compact, shareable evidence for the mechanical
decomposition proposed from `cervantesh:codex/update-cmd-decomposition`.
It lives on a fork-only evidence branch and is not part of the product PR.

## Frozen frame

- Upstream base: `b954547e726eb8df7479178d3db489852904705b`
- Operational candidate: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- Published PR head: `99daedd99928c26ba0259c54d292fb790228b71a`
  (the three original commits rebased without patch drift)
- Integration refresh: the branch was rebased onto the exact upstream base
  above; `git range-diff` reports all three patches unchanged and preserves
  their authorship.
- Delivery: implementation PR is ready for review.

## What the evidence establishes

- All 161 original updater functions have a destination; 155 bodies are
  AST-identical and six controlled adaptations are accounted for.
- The historical facade surface remains available: 195 of 195 top-level names.
- Static compatibility audits found no missing monkeypatch propagation across
  the extracted consumers.
- Every changed Python file is below the 2,000 physical-line cap.
- A historical single-process diagnostic produced the same 42 failing node IDs
  on candidate and clean base, while the candidate added three passing guards.
  That command is not the canonical per-file runner and is not current-CI
  status. A later canonical clean-main audit assigned the independently
  closable test defects to #98037, #98038, #98039, and #98040; none is caused
  by this refactor.
- Hosted focused checks passed on Linux, macOS, and Windows.
- The controlled Linux real update path produced exit `0`, the same five
  observable invariants, and an `equivalent` comparator verdict before/after.
- The Windows live comparison produced exit `0`, the same 19 passing testcase
  IDs/statuses, and an `equivalent` comparator verdict before/after.
- Real systemd, launchd, and Windows SCM boundaries produced identical,
  entirely successful before/after contracts on the exact published PR head.

## Evidence map

- `ACCEPTANCE_MATRIX.md` — each claim mapped to its check, verdict, and source.
- `REVIEW_ADJUDICATION.md` — independent findings, adjudication, and TDD fixes.
- `REPRODUCE.md` — commands and limits for repeating the checks.
- `VERIFICATION_RESULTS.txt` — compact machine-oriented result ledger.
- `KNOWN_BASELINE_FAILURES.txt` — node IDs from the historical noncanonical
  single-process diagnostic; retained as comparison provenance, not current CI.
- `INHERITED_FAILURE_AUDIT.md` — exact historical and canonical commands,
  environment, results, causal controls, and ownership for #98037–#98040.
- `UPSTREAM_CI.md` — initial red classification, two-line metadata correction,
  and exact-current-head upstream CI receipt.
- `linux-e2e/` — controlled real-path workflow and machine verdict;
  [Actions run 33229985934](https://github.com/cervantesh/hermes-agent/actions/runs/33229985934).
- `windows-live/` — real Windows process/filesystem workflow and machine verdict;
  [Actions run 33230583743](https://github.com/cervantesh/hermes-agent/actions/runs/33230583743).
- `native-supervisors/` — real systemd, launchd, and Windows SCM fixtures,
  executable probes, native diagnostics, and aggregate comparator;
  [Actions run 33260176395](https://github.com/cervantesh/hermes-agent/actions/runs/33260176395).
- `standard-runners/` — exact-candidate focused Linux/macOS/Windows receipt;
  [Actions run 33228955478](https://github.com/cervantesh/hermes-agent/actions/runs/33228955478).
- `assets/update-cmd-decomposition-verification.png` — explanatory summary.
- `SHA256SUMS.txt` — integrity manifest for this public subset.

## Honest boundary

This package supports operational equivalence in the exercised Linux updater,
Windows-live, and real native-supervisor boundaries. The supervisor run tests
the restart/verification boundary directly; it does not execute a complete
source update from inside each fixture. The infographic must not be treated as
a substitute for the executable evidence.
