# V2 preflight attempt 3 disposition

Status: **MECHANICALLY PASSING BUT PROVENANCE-INADMISSIBLE — not scored**

This attempt passed the then-current detached/shared mechanical gates. It was
not accepted as sealing evidence because its public receipt did not bind the
exact protocol and harness source, and the path auditor did not yet extract
targets embedded in V4A patch text. A later adversarial review also found that
the source manifest initially omitted imported lifecycle code and that the
scratchpad readback receipt used expected input rather than actual view bytes.

The sanitized packet remains auditable, but it cannot authorize the V2 seal and
is not pooled with the dedicated preflight or any scored observation.
