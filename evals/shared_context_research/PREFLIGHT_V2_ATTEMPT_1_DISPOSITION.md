# V2 preflight attempt 1 disposition

Status: **INVALID — not scored and not protocol evidence**

The first two-topology preflight on target
`180291162ff4df0d42b5dc4fecd08005cf7cebf9` exercised the real dispatcher and
workers but did not satisfy the frozen integrity gates:

- the sentinel parser expected the literal phrase `task not found`, while the
  real handler returns `task <id> not found`; and
- two detached-source consumers searched their arm parent directory. The
  external result oracle passed, but the resolved-path gate correctly recorded
  scope expansion.

No observation from this attempt is pooled with the pilot. The raw record stays
under the ignored private-results directory. The sanitized receipt is retained
under `evidence/issue377-v2-preflight-20260901` solely so the failed preflight is
auditable.

Before another preflight, the harness was amended to parse the handler's
structured JSON error, make the existing workspace boundary explicit in every
consumer instruction, and fail the preflight command when any integrity gate is
false. These are pre-seal harness corrections; no V2 scored observation existed.
