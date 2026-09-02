# V3 scored-run disposition

The prospectively sealed V3 run is **INCONCLUSIVE** and must not be resumed or
presented as a complete experiment.

- Frozen source commit: `d8f4423eb4fa62ac3fe3e192c1aeaaccb9d19262`
- Target: `NousResearch/hermes-agent@c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf`
- Retained scored observations: 15 of 18
- Sanitized observation SHA-256:
  `44b4f6dbc83ec607bb999321e027011aba3e5b3d20c528d43708907257ffa5b7`
- Private raw SHA-256:
  `c935e17fb1196e1ae85e464c59c20700f1fbd1d05e060674c76fd47040efa305`

The first 15 fixture/cohort pairs completed without a provider retry. During
`sonnet-s377/ordered_dependency_plan`, a consumer exceeded the frozen worker
deadline. `fixture_worker_v3` exited without a structured observation and
`runner_v3` raised `RuntimeError` instead of retaining the non-provider failure
as an invalid row. The remaining two fixtures did not run.

Re-running that slot under V3 would silently replace an adverse attempt and
violate the no-adaptive-replacement rule. Therefore the partial packet reports
the three missing slots and the frozen adjudicator returns `INCONCLUSIVE`.

Any repetition must use a newly sealed protocol that records every terminal
fixture failure as a structured invalid observation, continues the remaining
frozen slots, and never converts that failure into a provider retry.
