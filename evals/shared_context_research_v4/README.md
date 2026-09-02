# Issue #377 V4 repetition

V4 is the clean repetition after V3 exposed a failure-retention defect in the
evaluation runner. It preserves V3 and its partial evidence unchanged.

The source seal must be public before preflight. Scored work starts only after
the two frozen preflight fixtures pass. Every terminal scored fixture outcome
is retained exactly once, including non-provider timeouts.

No Hermes production file is changed.
