# Post-signal regression robustness freeze

Frozen after the Haiku full-CAMEL ceiling characterization produced two
externally incorrect `task_done` outcomes. This is explicitly post hoc and is
not pooled with the preregistered sample.

## Question

Are the two observed regressions limited to the economic model, or can the
same full protocol also fail or add material cost with the stronger pilot
model?

## Frozen check

- model: `claude-sonnet-4-6`
- strategy: full CAMEL only
- tasks: `simple_manifest`, `false_success_shortcut`
- one repetition
- label: `robustness-camel-sonnet46`
- compare descriptively with the matching successful Sonnet baseline records

No ablation is authorized. A pass does not establish benefit because the
baseline already passes; a failure identifies a product-safety concern to
investigate before any adoption study.
