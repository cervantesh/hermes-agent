# Frozen V6 protocol: clean repetition after session-evidence repair

Status: **FINAL BEFORE REMOTE SEAL AND PROVIDER OBSERVATION**.

V6 repeats V5's target, fixtures, models, seeds, B-first gate, comparison
schedule, oracles, and decision threshold exactly. V5 is not resumed or pooled.

Two methodological repairs are allowed:

1. session evidence lookup ignores SQLite candidates that lack a `sessions`
   table and selects the store containing the exact worker session id; and
2. every subprocess nonzero or malformed output becomes a retained,
   privacy-safe failure row before the label is permanently aborted.

The unscored V5 seed-379 diagnostic is excluded. V6 starts every provider slot
from scratch after a new source seal is published remotely. No retry or row
replacement is permitted.
