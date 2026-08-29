# `update_cmd.py` decomposition — public review evidence

This directory preserves the compact, shareable evidence for the mechanical
decomposition proposed from `cervantesh:codex/update-cmd-decomposition`.
It lives on a fork-only evidence branch and is not part of the product PR.

## Frozen frame

- Upstream base: `ac6c8028e00d01ee2f299ba7fd03329c7f10382d`
- Candidate: `4dbdf314179f60999eb94e6ea5bc81367f2ea351`
- Integration refresh: upstream `main` was three unrelated commits ahead when
  publication was prepared; none changed updater or updater-test paths.
- Delivery: implementation PR remains draft.

## What the evidence establishes

- All 161 original updater functions have a destination; 155 bodies are
  AST-identical and six controlled adaptations are accounted for.
- The historical facade surface remains available: 195 of 195 top-level names.
- Static compatibility audits found no missing monkeypatch propagation across
  the extracted consumers.
- Every changed Python file is below the 2,000 physical-line cap.
- Candidate and clean-base broad runs share the same 42 failing node IDs; the
  candidate adds three passing regression guards.
- Hosted focused checks passed on Linux, macOS, and Windows.
- The controlled Linux real update path produced exit `0`, the same five
  observable invariants, and an `equivalent` comparator verdict before/after.
- The Windows live comparison produced exit `0`, the same 19 passing testcase
  IDs/statuses, and an `equivalent` comparator verdict before/after.

## Evidence map

- `ACCEPTANCE_MATRIX.md` — each claim mapped to its check, verdict, and source.
- `REVIEW_ADJUDICATION.md` — independent findings, adjudication, and TDD fixes.
- `REPRODUCE.md` — commands and limits for repeating the checks.
- `VERIFICATION_RESULTS.txt` — compact machine-oriented result ledger.
- `KNOWN_BASELINE_FAILURES.txt` — identical inherited failure set.
- `linux-e2e/` — controlled real-path workflow and machine verdict;
  [Actions run 33229985934](https://github.com/cervantesh/hermes-agent/actions/runs/33229985934).
- `windows-live/` — real Windows process/filesystem workflow and machine verdict;
  [Actions run 33230583743](https://github.com/cervantesh/hermes-agent/actions/runs/33230583743).
- `standard-runners/` — exact-candidate focused Linux/macOS/Windows receipt;
  [Actions run 33228955478](https://github.com/cervantesh/hermes-agent/actions/runs/33228955478).
- `assets/update-cmd-decomposition-verification.png` — explanatory summary.
- `SHA256SUMS.txt` — integrity manifest for this public subset.

## Honest boundary

This package supports operational equivalence in the exercised Linux updater
and Windows-live scopes. It does not prove real systemd, launchd, or Windows
SCM supervisor equivalence, and the infographic must not be treated as a
substitute for the executable evidence.
