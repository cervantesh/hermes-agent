# V2 preflight attempt 4 disposition

Status: **INVALID — not scored and private only**

The first provenance-bound preflight used the final pre-seal source manifest
but stopped because `cost_segments_exact` was false in both fixtures. Duration
segments reconciled exactly. The missing values were token receipts:

- the parent relay helper looked only for nested `tokens` / `token_usage`, while
  current Hermes returns the real turn counters as top-level result fields; and
- one legitimately blocked consumer omitted `worker_session_id` from its run
  metadata, although the fresh isolated consumer profile contained its sole
  persisted session and usage.

No missing usage was imputed and the gate was not relaxed. V2 now reads the
relay's actual top-level counters. When run metadata omits a consumer session
ID, it accepts a database fallback only if the consumer profile was empty
before dispatch and contains exactly one session afterward; zero or multiple
sessions remain missing usage and invalidate the fixture. The raw attempt is
retained under the ignored private-results directory and is not pooled with any
preflight or pilot evidence.
