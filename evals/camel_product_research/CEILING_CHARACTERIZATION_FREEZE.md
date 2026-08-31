# Full-CAMEL ceiling characterization freeze

Frozen after both baseline opportunity cohorts reached 7/7 and before any
scored full-CAMEL observation.

The opportunity gate rules out a positive success-rate lift on these tasks,
but a product decision still needs to know whether full CAMEL preserves known
success and what it costs. This is a non-inferiority/cost characterization,
not an efficacy comparison.

## Frozen sample

- `simple_manifest`: simple-path control
- `ambiguous_handoff`: underspecified user request requiring repository reading
- `false_success_shortcut`: seven-stage anti-bypass workflow
- model: `claude-haiku-4-5`
- one repetition per task
- result label: `ceiling-camel-haiku45`

The frozen external oracles remain authoritative. Report pass retention,
false success, API-call ratio, token ratio when available, and latency ratio
against the matching `economic-haiku45` baseline. Do not infer a success-rate
benefit from this arm. Do not open ablations unless a later failed-baseline
cohort produces a favorable full-system transition.

The earlier direct `simple_manifest` smoke is unscored. It proved runtime
conformance and exposed duplicate tool-trace accounting; v3 deduplicates tool
calls by provider call id before this scored run.
