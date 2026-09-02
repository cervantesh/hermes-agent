# V2 executable preflight receipt

Status: **PASS — mechanical admission only; no observation is scored**

## Evidence frame

- Upstream and target SHA: `180291162ff4df0d42b5dc4fecd08005cf7cebf9`
- Target worktree: clean at execution and rechecked after execution
- Provider/model: `claude-code` / `claude-haiku-4-5`
- Python harness: Python 3.11
- Fixtures: `preflight_detached_echo` and `preflight_shared_echo`
- Cohort membership: none; both are excluded from `TASKS`, `DEPENDENT`,
  `CONTROLS`, and every scored execution table
- Sanitized observations:
  `evidence/issue377-v2-preflight-dedicated-20260901`
- Observation count: 2 complete fixtures / 6 consumer arms
- Decision-critical source files: 22
- Source-manifest SHA-256:
  `a911c9d52492e1c7a0a3aeb3d02acf120f7514fa52e4a115c66c2d7b4a45df12`
- Sanitized observations SHA-256:
  `523015d6d5f5da45872e915bd80826b4ba402c17b8c429e620ad0248731dd0f3`
- Private raw SHA-256:
  `cce3cdb651bfbccce7883f9ad8d560fce4e3553514c2f1cd25bfa56a791834da`

## Exact commands

```powershell
python -m evals.shared_context_research.preflight_v2 `
  --repo-root C:\dev\hermes-shared-context-main `
  --python-executable C:\dev\hermes\.venv\Scripts\python.exe `
  --label issue377-v2-preflight-dedicated-20260901

python -m evals.shared_context_research.verify_public_evidence_v2 `
  --evidence-dir evals/shared_context_research/evidence/issue377-v2-preflight-dedicated-20260901
```

The independent verifier returned:

```json
{"ok": true, "count": 2, "sha256": "523015d6d5f5da45872e915bd80826b4ba402c17b8c429e620ad0248731dd0f3"}
```

## Mechanical gates proved in both fixtures

Every integrity value in the sanitized receipts is `true`:

- one admitted common producer;
- pairwise-distinct consumer homes, Kanban databases, and workspaces;
- empty consumer session stores before dispatch and expected pre-run task
  counts;
- byte-identical config, overrides, and effective tool schema across A/B/C;
- task-scoped producer-ID sentinel absent in A/C and reachable in B;
- exact seeded arm order and equal common-producer cost in every arm;
- every token and duration component present and arithmetically reconciled;
- A and detached B refer to the same persisted producer summary;
- C's actual declared-view readback digest equals the producer artifact digest;
- file and V4A patch targets confined to each arm's allow-list;
- detached producer workspace removed before consumers run;
- exact producer-written shared-file identity preserved for shared-storage B;
  and
- no forbidden consumer tool or Kanban operation in the recorded traces.

The effective consumer schema had digest
`eafc8b331bcdf8ef45a69b5f0307a3e99d29927e18025fab771854fc8b6208c5`.
It contained only the `file` surface and task-scoped `kanban_*` definitions.
Runtime trace enforcement admitted only `kanban_show`, `kanban_complete`, and
`kanban_heartbeat` among the broader Kanban definitions.

## Outcome handling demonstrated, not interpreted

All six arms passed their executable echo oracle, with zero false-success and
zero scope-expansion events. In the detached fixture, A and B did not reproduce
the canonical handoff bytes exactly even though the final oracle passed; C did.
In the shared fixture, B and C preserved exact handoff fidelity while A did
not. These are unscored preflight observations. They are not pooled, compared,
or treated as evidence for issue #377.

## Exclusions and failed attempts

Provider authentication, transport, quota, and service failures would make an
observation inadmissible; none occurred in the admitted attempt. Real SSH,
Modal, container, and multi-host boundaries remain outside this local product
experiment.

Five earlier unscored attempts are explicitly excluded. They exposed, in
order: a sentinel parser defect and scope expansion; another scope expansion;
the need for source provenance; missing lifecycle/token provenance; and the
risk of selecting on stochastic scope compliance in a complex preflight task.
Their individual dispositions and private raw receipts are preserved. None is
pooled with this preflight or the future pilot.
