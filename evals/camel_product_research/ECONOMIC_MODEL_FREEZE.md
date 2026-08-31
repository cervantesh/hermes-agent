# Economic-model opportunity freeze

Frozen after the Sonnet baseline reached 7/7, and before observing this cohort.

## Question

Does full CAMEL create externally verified successes for an available economic
model on any task where current Hermes fails, without increasing false
success enough to erase the benefit?

## Runtime and protocol

- model: `claude-haiku-4-5`
- provider path: Claude Code credential through Hermes's Anthropic transport
- tasks, fixtures, external oracles, prompt hashes, source revisions, and
  40-message CAMEL cap: unchanged from `PILOT_FREEZE_V2.md`
- repetitions: one opportunity pilot
- ordering: randomized with seed 375

Run the baseline on all seven tasks. Full CAMEL is authorized only for failed
baseline tasks. Ceiling tasks stop. A favorable transition is exploratory and
requires new-task confirmation; an unfavorable observation does not prove
that CAMEL cannot help other models or task distributions.
