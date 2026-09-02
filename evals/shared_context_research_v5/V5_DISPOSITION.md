# V5 disposition: inconclusive harness compatibility failure

V5 dispatched the first sealed B-gate slot
(`haiku-s377/cap_below_control`) after the remote seal. The fixture subprocess
exited nonzero before emitting a structured row. The sealed runner used
`subprocess.run(check=True)` and did not persist captured stderr before raising,
so the slot cannot be resumed or replaced.

A separate, explicitly unscored diagnostic run with seed 379 reproduced the
same failure and exposed its cause:

```text
sqlite3.OperationalError: no such table: sessions
```

On the current target, the inherited evaluation helper encountered an
auxiliary `state.db` without the `sessions` table before the worker profile's
actual session store. This is a harness compatibility defect, not a B outcome,
provider failure, or product result.

Disposition: **INCONCLUSIVE — HARNESS COMPATIBILITY FAILURE**. V5 contributes
no scored observation and must not be pooled with a corrected repetition. A
new version must select session databases by schema and retain subprocess
failure evidence before it can repeat the complete frozen schedule from
scratch.
