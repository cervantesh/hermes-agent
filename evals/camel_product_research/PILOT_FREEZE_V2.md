# Pilot freeze receipt v2

This receipt supersedes `PILOT_FREEZE.md` before any valid scored cohort was
completed.

The first attempted Gemini batch produced one completed simple control and six
provider quota failures. The batch is invalid and must not be pooled with any
research result. It exposed that `worker.py` did not convert provider failures
into invalid observations. Version 2 adds that fail-closed rule and changes the
pilot runtime to the available Claude Sonnet 4.6 path.

All other task definitions, executable oracles, CAMEL source prompts,
sequential gates, thresholds, and source revisions remain unchanged. Any
result under label `pilot-gemini25flash` is preflight evidence only.

The v2 pilot label is `pilot-v2-claude-sonnet46`. A worker exits nonzero when
its summary, error, or exit reason contains a frozen provider-failure marker;
the runner therefore cannot append that attempt as a scored observation.
