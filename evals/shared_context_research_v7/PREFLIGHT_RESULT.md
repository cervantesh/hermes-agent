# V7 Provider-Free Preflight Result

Freeze: `SCR-V7-INITIAL-2026-09-02`

Target: clean `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`

Command:

```powershell
python -m evals.shared_context_research_v7.common.preflight_runner `
  --evidence-root evals/shared_context_research_v7/evidence `
  --label v7-preflight-20260902
```

## Observed evidence

Six observations ran with a fresh `HERMES_HOME`, board, database, and task
graph for every case.

| Case | Observation | Interpretation |
| --- | --- | --- |
| Context subset | Full payload: 8,881 bytes; declared payload: 223 bytes; both exact | A selective projection has a large structural byte advantage, but this is not yet a model-token or latency result. |
| All-records control | Full and declared payloads: 565 bytes; both exact | Selectivity provides no payload advantage when every record is required. |
| Above-cap selective read | 14,301-byte source; requested tail absent from the 4,570-byte startup context; full result exact through real `kanban_show` | Startup truncation is reachable, but this fixture is not a current-Hermes RED because the strongest allowed baseline recovers it. |
| Below-cap control | 396-byte source; requested value present at startup and exact through `kanban_show` | Positive control passed. |
| Unrelated same-board read | Canary visible through `kanban_show` | Reachability confirmed; policy intent is unadjudicated, so this is not labeled a vulnerability. |
| Declared completed parent | Canary visible through `kanban_show` | Positive relationship control passed. |

## Allowed conclusions

- Track 1 has a measurable serialized-byte hypothesis worth a sealed model
  evaluation. No token or latency claim exists yet.
- Track 2's first above-cap fixture does not establish a selective-access
  efficacy gap because current Hermes recovers the full parent result through
  a normal tool path.
- Track 3 needs an explicit product-policy decision before current cross-task
  visibility can be classified as unsafe.
- Tracks 4, 5, and 6 remain closed by the initial design's dependency gates.

## Harness correction retained

The first Windows run exposed an open SQLite descriptor in the harness because
`with kb.connect()` does not close a connection. The harness now uses
`kb.connect_closing()`. The failed test was retained in the test output during
development; it was a harness lifecycle failure, not a product observation.

