# Completion audit: issue #377 bounded product experiment

Audit date: 2026-09-01  
Audit result: **COMPLETE AS AN INCONCLUSIVE EXPERIMENT**

This audit treats completion as completion of the requested investigation, not
as proof of a product opportunity or permission to implement.

## Numbered requirements

| requirement | authoritative evidence | assessment |
| --- | --- | --- |
| 1. Start from current upstream `main` and record exact SHA. | `RESEARCH_FRAME.md`, `PROTOCOL_FREEZE_V2.md`, both public receipts, and the final `git ls-remote` all identify `180291162ff4df0d42b5dc4fecd08005cf7cebf9`. The detached target worktree is clean at that SHA. | Proved. |
| 2. Recheck #377, #82157, #83061, and newer overlap. | Pre-run `OWNERSHIP_AUDIT.md`; final GitHub-connector read in `OWNERSHIP_REFRESH_V2.md`. #82157 remains open/unmerged, #83061 remains merged, and adjacent #35688, #47035, #76221, #78418, and #81139 do not own the bounded comparison. | Proved as a dated ownership snapshot. |
| 3. Compare A parent relay, B current handoff, and C simulated scratchpad without assuming new tools. | `PROTOCOL_FREEZE_V2.md`, `runtime_v2.py`, and the six sanitized pilot observations. B uses real Kanban parent-link context for detached storage and the producer-written file for shared storage; C exists only in the harness. | Proved. |
| 4. Freeze tasks, model/provider, repetitions/order, metrics, thresholds, stopping rules, exclusions, and provider failure handling before results. | `PROTOCOL_FREEZE_V2.md` and `PROTOCOL_SEAL_V2.json`; `verify_seal_v2()` passes after the run. Source manifest: `a911c9d52492e1c7a0a3aeb3d02acf120f7514fa52e4a115c66c2d7b4a45df12`. | Proved. |
| 5. Use dependent workflows and executable external oracles. | Deterministic fixtures/oracles in `tasks.py`; producer and consumer effects are read from files rather than completion prose. The pilot ran four dependent workflows. | Proved. |
| 6. Measure verified completion, parent/total tokens, latency, handoff loss, false success, and scope expansion. | Per-arm fields in the sanitized observations; accounting and gate logic in `runtime_v2.py` and `analysis_v2.py`; summarized in `PILOT_V2_RESULT.md`. | Proved for every pilot arm, including the invalid fixture; invalid data is not promoted into the formal gate. |
| 7. Include isolation, authority, partial-write, independent-task, and no-shared-filesystem controls. | `test_concurrent_workflows_are_isolated`, `test_downstream_view_has_no_mutation_surface`, `test_uncommitted_value_is_invisible`, `test_write_once_and_idempotent_replay`, declared-read/write tests, real producer-ID sentinels, and two independent pilot controls. Detached-source topology removes the producer workspace before consumer dispatch. Actual SSH, Modal, container, and multi-host boundaries are explicitly classified unverified. | Proved within the declared local/tool-contract boundary; remote boundary honestly unverified. |
| 8. Run the smallest 6–8-workflow pilot and expand only for a real opportunity. | Six frozen pilot fixtures executed. The predeclared integrity rule stopped the run with `complete=false`, `expand=false`; expansion and confirmation did not run. | Proved. |
| 9. Apply frozen stopping decisions. | `analysis_v2.py`, public `receipt.json`, `PILOT_V2_RESULT.md`, and adversarial review all return `INCONCLUSIVE` because `ordered_dependency_plan` failed `all_trace_scopes`. | Proved. No conclusive product label is forced. |
| 10. Preserve private raw evidence and sanitized reproducible receipts with hashes, commands, SHAs, and exclusions. | Private raw is under ignored `results-private/`; pilot raw hash is `407f96b9251cd5d2e7ea531893078314e8d297c2287f01e620a34d0561527335`. Sanitized packet verifies at `9f12e2acea6ce5ba413edb191ee277c543345d02a3cc63f48c67c048512cfbcf`. `PREFLIGHT_RECEIPT_V2.md`, packet receipts, dispositions, and `RESULT_RECEIPT_V2.json` record commands and exclusions. | Proved. |
| 11. Do not modify production code, publish, open a PR, or edit #377. | Worktree status contains only the untracked `evals/shared_context_research/` package. Target worktree status is empty. GitHub was accessed read-only; no publication or PR operation was performed. | Proved. |
| 12. Keep strict issue evaluation separate from architecture redesign. | `RESEARCH_FRAME.md`, protocol scope, and `PRODUCT_ADJUDICATION_V2.md` explicitly reject general CAMEL/Eigent, memory, workflow-engine, and core-tool claims. | Proved. |

## Deliverables

| deliverable | artifact | status |
| --- | --- | --- |
| Frozen research protocol | `PROTOCOL_FREEZE_V2.md`, `PROTOCOL_SEAL_V2.json` | Complete and seal-valid. |
| Ownership and capability audit | `OWNERSHIP_AUDIT.md`, `OWNERSHIP_REFRESH_V2.md` | Complete and current at audit time. |
| Executable harness and tests outside production surfaces | `protocol_v2.py`, `runtime_v2.py`, `runner_v2.py`, scratchpad store, fixtures, analyzers, sanitizers, verifiers, and tests under this evaluation package | Complete. |
| Sanitized evidence receipts | Dedicated preflight and pilot directories under `evidence/`, plus `RESULT_RECEIPT_V2.json` | Complete and hash-verified. |
| A/B/C results and uncertainty | `PILOT_V2_RESULT.md` | Complete. |
| Adversarial falsification | `ADVERSARIAL_RESULT_REVIEW_V2.md` | Complete and independently challenged. |
| Product adjudication | `PRODUCT_ADJUDICATION_V2.md` | Complete: none of the three conclusive labels is supported; formal outcome is `INCONCLUSIVE`. |
| Closure predicate/direction if an opportunity exists | Not applicable | No opportunity was established, so defining production direction would overreach. |

## Final verification commands and results

The development test command requires the target checkout on `PYTHONPATH`
because the path-scope tests intentionally import current-main file-tool
resolution code:

```powershell
$env:PYTHONPATH='C:\dev\hermes-shared-context-main'
pytest -q evals/shared_context_research
# 36 passed

ruff check evals/shared_context_research
# All checks passed

ruff format --check evals/shared_context_research
# 45 files already formatted

python -m evals.shared_context_research.verify_public_evidence_v2 `
  --evidence-dir evals/shared_context_research/evidence/issue377-v2-pilot-20260901
# {"ok": true, "count": 6, "sha256": "9f12e2...bcf"}
```

The preflight packet also verifies with two observations at
`523015d6d5f5da45872e915bd80826b4ba402c17b8c429e620ad0248731dd0f3`.
`verify_seal_v2()` returns true, `RESULT_RECEIPT_V2.json` verifies all six
bound hashes, and `git diff --check` is clean.

## Completion decision

The requested bounded experiment has been executed, stopped by its
prospective rule, independently challenged, and fully receipted. Its scientific
result is `INCONCLUSIVE`. The work is complete because no required in-scope
action remains; repeating or loosening the protocol after observing the result
would reduce rather than increase the validity of this study.
