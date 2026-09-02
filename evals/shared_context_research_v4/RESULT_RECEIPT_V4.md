# Issue #377 V4 result receipt

## Bounded result

`NO DEMONSTRATED INCREMENT`

This is the prospectively declared label for this fixture/model matrix. It is
not an equivalence claim and does not show that durable shared context lacks
value outside these conditions.

## Execution completeness

- Target: `NousResearch/hermes-agent@c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf`
- Frozen source commit: `f14489bb55bbc57538e26e474e12ef445d715493`
- Observations: 18 of 18
- Provider failures: 0
- Non-provider fixture failures: 0
- Retried observations: 0
- Independent controls: all arms passed in all three cohorts
- Public observations SHA-256:
  `4a1d09f0e2b5e4e766b840f61f9571668e87ed17893ef0862a6b2e685725eb1a`
- Private raw SHA-256:
  `c0f27d0ad7ca0e5da97bdc2ed6bedc5c4d493715fb57705d37764ec12f14b447`

## Primary and resource endpoints

- Replicated C-only workflow successes: none
- B-only workflow successes: none
- Token trigger: false
- Latency trigger: false

| cohort | median C-vs-B token improvement | median C-vs-B latency improvement |
| --- | ---: | ---: |
| `haiku-s377` | -1.35% | +1.74% |
| `haiku-s378` | -8.12% | -7.29% |
| `sonnet-s377` | -1.29% | -1.00% |

Negative values mean C used more tokens or had greater constructed latency
than B. No preregistered resource threshold repeated across all cohorts.

## Secondary fidelity observation

Across the 12 dependent rows, exact handoff fidelity was observed in C for
12/12, B for 8/12, and A for 2/12. This is descriptive secondary evidence.
It did not produce a replicated C-only externally verified outcome and cannot
independently authorize product implementation under the frozen protocol.

## Relation to V3

V3 remains a separate, incomplete run with 15 retained observations and an
`INCONCLUSIVE` label. Its rows were not resumed, replaced, or pooled into V4.
V4 reran all 18 slots from scratch after prospectively sealing terminal-failure
retention and crash-safe no-replacement journals.
