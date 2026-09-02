# Issue #377 shared-context product experiment

This directory is a **research and evidence package**, not a Hermes production
change or an implementation PR.

## Question

For dependent multi-agent workflows, does workflow-scoped shared context
improve externally verified correctness, handoff fidelity, parent/total token
usage, or latency over mechanisms Hermes already provides?

The comparison is:

- **A — parent relay:** a parent model receives and retransmits the producer
  result;
- **B — existing Hermes handoff:** the real Kanban parent-link projection for
  detached workspaces, or the exact producer-written artifact when storage is
  shared; and
- **C — simulated scratchpad:** a workflow-scoped, declared-read, write-once
  store implemented only in this evaluation package.

The experiment targets clean upstream
`main@180291162ff4df0d42b5dc4fecd08005cf7cebf9`, recorded on 2026-09-01.
Ownership was refreshed on 2026-09-01 in
[`OWNERSHIP_REFRESH_V2.md`](OWNERSHIP_REFRESH_V2.md). At publication time on
2026-09-02, upstream had advanced to
`57d305d57f04ffb58fb8adef3657b166fa6e34a6`; this packet was not rerun on that
revision. See [`PUBLICATION_REFRESH.md`](PUBLICATION_REFRESH.md) for the exact
scope of the intervening changes.

## Result

Formal outcome: **`INCONCLUSIVE`**.

The frozen pilot ran four dependent workflows and two independent controls.
Both controls passed in every arm. One dependent fixture,
`ordered_dependency_plan`, was invalidated because arm A invoked
`kanban_block`; the prospectively sealed trace contract allowed only
`kanban_show`, `kanban_complete`, and `kanban_heartbeat`. The frozen gate
therefore stopped without expansion.

The three valid dependent fixtures showed no C-only verified success. C
preserved exact handoff fidelity where B did not in one fixture; descriptively,
C used a median `2.21%` more tokens than B and reduced latency by `1.21%`.
Those values are not a substitute gate and do not justify any conclusive
product label.

See:

- [`PILOT_V2_RESULT.md`](PILOT_V2_RESULT.md) for observations and uncertainty;
- [`PRODUCT_ADJUDICATION_V2.md`](PRODUCT_ADJUDICATION_V2.md) for the bounded
  product disposition;
- [`ADVERSARIAL_RESULT_REVIEW_V2.md`](ADVERSARIAL_RESULT_REVIEW_V2.md) for the
  post-result falsification; and
- [`COMPLETION_AUDIT_V2.md`](COMPLETION_AUDIT_V2.md) for requirement-by-
  requirement closure.

## Package boundaries

- No Hermes production file is changed by this package.
- `results-private/` contains raw local provider evidence and is ignored by
  Git. It is intentionally absent from the public package.
- `evidence/` contains sanitized receipts only. Failed preflight and V1
  packets are retained solely to explain exclusions; they are not pooled with
  the scored pilot.
- The C scratchpad is an experimental treatment, not a proposed class or tool.
- Actual SSH, Modal, container, and multi-host boundaries remain unverified.

## Recorded environment

- Host topology: native Windows, local isolated temporary roots
- Python: 3.11.7
- Provider/model: `claude-code` / `claude-haiku-4-5`
- Target: clean detached checkout of the SHA above
- Harness base: `34931694f2f44597a862bea48114b316cb09ab71`

Deterministic verification takes only a few seconds on the recorded host and
does not call a model. A live pilot invokes the configured provider repeatedly;
allow approximately 15–45 minutes and expect provider usage charges. Runtime
and cost depend on provider availability and are not guaranteed by this
estimate.

## Prerequisites

1. A clone containing this package.
2. A separate clean checkout of `NousResearch/hermes-agent` at the exact target
   SHA.
3. Python 3.11 with the target repository's development dependencies,
   including `pytest` and `ruff`, for the deterministic suite.
4. Only for a live rerun: a working `claude-code` provider login and a Hermes
   Python environment capable of starting real Kanban workers.

No elevated privileges, persistent service, or user production
`HERMES_HOME` is required. The harness creates isolated temporary homes,
boards, databases, and workspaces.

## Deterministic verification

From the repository root, substitute your own absolute target path:

```powershell
$TargetRepo = 'C:\path\to\clean-hermes-target'
$env:PYTHONPATH = $TargetRepo

python evals/shared_context_research/verify_publication_package.py
python -m evals.shared_context_research.verify_public_evidence_v2 `
  --evidence-dir evals/shared_context_research/evidence/issue377-v2-preflight-dedicated-20260901
python -m evals.shared_context_research.verify_public_evidence_v2 `
  --evidence-dir evals/shared_context_research/evidence/issue377-v2-pilot-20260901
python -c "from evals.shared_context_research.runner_v2 import verify_seal_v2; assert verify_seal_v2(); print('seal ok')"
pytest -q evals/shared_context_research
ruff check evals/shared_context_research
ruff format --check evals/shared_context_research
```

Expected successful outputs include:

- publication manifest verification with no missing or extra public files;
- preflight receipt: 2 observations, SHA-256
  `523015d6d5f5da45872e915bd80826b4ba402c17b8c429e620ad0248731dd0f3`;
- pilot receipt: 6 observations, SHA-256
  `9f12e2acea6ce5ba413edb191ee277c543345d02a3cc63f48c67c048512cfbcf`;
- valid protocol seal;
- 36 passing tests; and
- clean Ruff and format checks.

Every command above should exit zero. The public packet verifier checks
sanitization, source provenance, target identity, observation count, and
receipt hashes. [`RESULT_RECEIPT_V2.json`](RESULT_RECEIPT_V2.json) binds the
pilot, private-raw digest, ownership refresh, result memo, adversarial review,
and product adjudication.

## Optional live rerun

A live rerun is a **new stochastic observation**, not a reproduction of the
recorded result and not evidence that may be silently pooled with it:

```powershell
$TargetRepo = 'C:\path\to\clean-hermes-target'
$HermesPython = 'C:\path\to\hermes-python.exe'
$env:PYTHONPATH = $TargetRepo

python -m evals.shared_context_research.runner_v2 `
  --repo-root $TargetRepo `
  --python-executable $HermesPython `
  --label issue377-v2-independent-rerun `
  --auto-expand
```

The runner refuses a dirty or wrong target and verifies the sealed source
manifest. It expands only if the frozen pilot gate opens. Record a new label,
raw hash, public receipt, provider failures, and exclusions; do not overwrite
the recorded packet.

## Controls and success criteria

The deterministic suite and real preflight cover:

- concurrent workflow namespace isolation;
- declared reads and writes;
- downstream lack of a mutation surface;
- write-once authority and idempotent replay;
- invisible partial/uncommitted writes;
- A/C inability to resolve B's producer card;
- exact producer-file identity for shared-storage B;
- removal of the detached producer workspace;
- resolved file and V4A patch path boundaries;
- equal consumer schemas and clean pre-run state; and
- independent tasks receiving no artificial benefit.

The primary endpoint is the executable external oracle, never model prose or
a completion marker. A fixture is admissible only when its producer and every
integrity value pass. The complete stopping and opportunity thresholds are in
[`PROTOCOL_FREEZE_V2.md`](PROTOCOL_FREEZE_V2.md).

## Known nondeterminism and limitations

- Model outputs, latency, tokens, and provider availability are stochastic.
- The recorded schedule is fixed, but this single small pilot does not prove
  statistical equivalence.
- The own-task `kanban_block` event exposed a protocol rule that may be too
  broad. Reclassifying it after observing the outcome would be protocol drift;
  a future study would need a new seal.
- Local tool-contract isolation is not OS-level confinement and does not prove
  remote-backend availability or security.
- This study does not evaluate a general CAMEL/Eigent architecture.
- The recorded result applies to the pinned target. It must not be described as
  a current-main result after the publication refresh recorded above.

## Cleanup

Normal runs remove their temporary homes, boards, databases, and workspaces.
No daemon or service should remain. If a live run is interrupted, terminate
only worker processes created by that run, then remove only the uniquely named
temporary directory and the new label-specific directories it created under
`results-private/` and `evidence/`. Do not delete the repository, shared Hermes
home, or recorded evidence directories.

## Publication integrity

[`PUBLICATION_MANIFEST.json`](PUBLICATION_MANIFEST.json) hashes every public
file in this directory except the manifest itself. Verify it with:

```powershell
python evals/shared_context_research/verify_publication_package.py
```

The manifest intentionally rejects extra unignored files so local debris
cannot be mistaken for part of the published evidence frame.
