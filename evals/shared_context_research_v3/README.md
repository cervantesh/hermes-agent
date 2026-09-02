# Issue #377 V3 repetition

This is a prospectively published repetition of the bounded shared-context
experiment. V2 remains immutable under `evals/shared_context_research/`.

The pre-run commit contains only the frame, protocol, harness, tests, and seal.
Provider-backed observations and sanitized evidence are added later in a
separate commit. No file in Hermes production is modified.

After the remote seal, `preflight_v3.py` runs the two frozen unscored topology
fixtures. The scored runner is used only if that preflight passes.

See `RESEARCH_FRAME_V3.md` and `PROTOCOL_FREEZE_V3.md` for the frozen question,
cohorts, decision rule, and limitations.
