# V2 pilot result: formal stop without product adjudication

Status: **INCONCLUSIVE — no expansion and no implementation recommendation**

## Evidence frame

- Target: clean upstream `main@180291162ff4df0d42b5dc4fecd08005cf7cebf9`
- Provider/model: `claude-code` / `claude-haiku-4-5`
- Frozen cohort: four dependent workflows and two independent controls at
  schedule seed `377`
- Public packet:
  `evidence/issue377-v2-pilot-20260901`
- Sanitized observations SHA-256:
  `9f12e2acea6ce5ba413edb191ee277c543345d02a3cc63f48c67c048512cfbcf`
- Private raw SHA-256:
  `407f96b9251cd5d2e7ea531893078314e8d297c2287f01e620a34d0561527335`
- Decision-critical source-manifest SHA-256:
  `a911c9d52492e1c7a0a3aeb3d02acf120f7514fa52e4a115c66c2d7b4a45df12`

Exact execution command:

```powershell
python -m evals.shared_context_research.runner_v2 `
  --repo-root C:\dev\hermes-shared-context-main `
  --python-executable C:\dev\hermes\.venv\Scripts\python.exe `
  --label issue377-v2-pilot-20260901 `
  --auto-expand
```

The runner stopped after the six frozen pilot fixtures. It did not execute the
expansion or confirmation cohorts.

## Formal result

Both independent controls were valid and passed their external oracles in all
three arms. Three of the four dependent fixtures were also valid. The fourth,
`ordered_dependency_plan`, failed the frozen trace-scope integrity gate:

- arm A called `kanban_block` on its own active task after it could not produce
  the requested SHA value;
- the frozen protocol permits only `kanban_show`, `kanban_complete`, and
  `kanban_heartbeat` in scored consumer traces; and
- `all_trace_scopes` was consequently false, which invalidates the whole
  A/B/C fixture before scoring.

The frozen gate therefore returned:

```json
{
  "complete": false,
  "expand": false,
  "invalid_fixtures": ["ordered_dependency_plan"],
  "reason": "invalid_common_producer_pair_or_integrity"
}
```

Under the sealed rule, fewer than all four admitted dependent fixtures makes
the pilot `INCONCLUSIVE`. Passing controls cannot override that rule. The
invalid fixture's B/C correctness, fidelity, false-success, token, and latency
values are not eligible for a gate or product conclusion.

## Descriptive observations from valid dependent fixtures

These values are reported to make the evidence inspectable. They are not a
replacement gate and do not change the formal result. Positive resource deltas
mean C used fewer resources than B.

| fixture | verified A/B/C | B fidelity | C fidelity | C token delta vs B | C latency delta vs B |
| --- | --- | --- | --- | ---: | ---: |
| `artifact_policy_join` | pass / pass / pass | exact | exact | -1.39% | +3.02% |
| `distractor_filtered_catalog` | pass / pass / pass | altered | exact | -2.21% | +1.21% |
| `compact_release_map` | pass / pass / pass | exact | exact | -14.11% | -12.50% |

Across these three valid dependent fixtures:

- there was no C-only or B-only verified success;
- C preserved exact handoff fidelity where B did not in one fixture;
- the descriptive median C-vs-B token delta was `-2.21%`; and
- the descriptive median C-vs-B latency delta was `+1.21%`.

Those observations do not satisfy or falsify the frozen opportunity gate
because the gate requires all four dependent pilot fixtures.

## Limits

- The trace rule treated an honest, own-task `kanban_block` lifecycle outcome
  as invalid scope rather than as an adverse arm-A result. That may be too
  restrictive for a future protocol, but changing its meaning after observing
  the result would be outcome-dependent protocol drift.
- The cohort is deliberately small and ran once under one economical model.
  It does not establish statistical equivalence among the mechanisms.
- SSH, Modal, container, and multi-host access boundaries were not exercised.
  Local isolated roots and real tool restrictions are contamination controls,
  not proof of remote security or availability.
- The simulated scratchpad is an evaluation treatment, not production code and
  not evidence for a general CAMEL/Eigent architecture.

## Disposition

Stop this frozen experiment. Do not add a Hermes core tool or shared-memory
surface from these results. A future experiment would need a new, prospectively
sealed protocol that distinguishes honest lifecycle blocking from cross-scope
access; this pilot must remain immutable and must not be silently reclassified
or pooled with such a study.
