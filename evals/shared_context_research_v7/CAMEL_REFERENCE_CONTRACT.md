# CAMEL Reference Contract

Status: evidence contract for `SCR-V7-INITIAL-2026-09-02`

## Pinned references

- Hermes: `NousResearch/hermes-agent@593aa74c6182ce2e5e23bc102daaaae71710c05d`
- CAMEL: `camel-ai/camel@5cd0d0f4bda29893bdbf90c707c4ee59e36c829c`
- Paper: Li et al., *CAMEL: Communicative Agents for “Mind” Exploration of Large Model Society*, arXiv:2303.17760v2 (2023)

The references above are the evidence frame. Later source changes are drift to
audit, not silent updates to this contract.

## Three distinct systems

### 1. Original CAMEL paper

The paper evaluates a communication protocol, not a shared key/value store.
Its relevant mechanisms are:

1. a preliminary idea plus two human-selected roles;
2. a task-specifier agent that produces a concrete task;
3. an AI User that plans and issues instructions;
4. an AI Assistant that executes those instructions;
5. a multi-turn transcript visible to both role agents;
6. role-specific, mostly symmetric inception prompts; and
7. termination when the AI User emits `<CAMEL_TASK_DONE>`.

The paper names role flipping, repeated instructions, flake replies, and
infinite dialogue as observed failure modes. A harness claiming paper fidelity
must expose and score those failures. A shared scratchpad, declared keys,
namespaces, permissions, concurrent writes, and durable recovery are not paper
mechanisms and must not be attributed to it.

### 2. Current CAMEL Workforce

At the pinned commit, `Workforce` is a task orchestration implementation with
dependency tracking and worker pools. Its optional `share_memory=True` path:

- retrieves memory records from the coordinator, task agent, and every
  `SingleAgentWorker`;
- reconstructs those records and deduplicates them by UUID; and
- writes every new record to every other supported agent's memory.

Synchronization occurs at selected Workforce lifecycle boundaries. The code
explicitly excludes `RolePlayingWorker` and nested Workforce instances from
collection. This is complete-record conversation/tool-memory replication, not
selective-key retrieval, a transaction protocol, or a permission boundary.

Workflow memory is a separate feature: it persists summarized workflow files
and later loads selected prior workflows into agents. It must not be conflated
with the live `share_memory` switch.

### 3. Hermes adaptations under test

The V7 tracks study product adaptations that may be inspired by coordination
needs but are not claims about the paper or Workforce:

- compact or delta reads;
- selective declared-key access;
- workflow/tenant isolation and permissions;
- active shared writes;
- concurrent update semantics; and
- remote-backend coherence.

These mechanisms become candidates only after a current Hermes-native RED
witness shows that the strongest existing route cannot satisfy the same
observable contract.

## Experimental-arm contract

| Arm | Meaning | Required behavior |
| --- | --- | --- |
| R | Pinned CAMEL reference | Run the relevant pinned CAMEL mechanism without relabeling later Workforce features as paper behavior. |
| A | Hermes parent relay | Workers receive only their assigned input; the parent relays completed results. |
| B | Strongest current Hermes mechanism | Use all reachable native paths needed by the task: parent projection, `kanban_show`, comments, attachments/artifacts, and live steering. |
| C | Harness-only CAMEL simulation | Preserve task specification, AI User/Assistant roles, alternating multi-turn dialogue, and explicit termination. No production integration. |
| D | Minimal adaptation | Add only the smallest experimental mechanism required by a witnessed gap, such as declared-key reads. |

Arm B is not a deliberately weak baseline. If it recovers omitted context with
`kanban_show` or another normal Hermes route, that is a successful baseline,
not a bypass.

## Measurement contract

Every scored trial must record:

- pinned source and protocol identifiers;
- task and seed identifiers;
- model/provider identity when a provider is used;
- arm, order, and retry metadata;
- externally verified task outcome;
- input/output tokens and elapsed time where observable;
- tool actions and retrieved context volume;
- protocol violations, false-success signals, and termination reason; and
- sanitized artifact hashes sufficient for independent verification.

The common resource gate is frozen as:

- equal external success;
- at least 15% lower median tokens **or** at least 20% lower median latency;
- no regression in the other resource; and
- repetition across two model cohorts.

Model prose, self-reported completion, and a green unit mock are not external
success evidence.

## Attribution rules

- Say “paper mechanism” only for task specification, the two roles, their
  alternating conversation, inception prompts, or termination contract.
- Say “current Workforce behavior” only for code observed at the pinned CAMEL
  commit.
- Say “Hermes adaptation” for keys, namespaces, permissions, active writes,
  concurrency, durability, or remote-backend semantics.
- Report a negative result as bounded by the tested tasks, models, horizons,
  and mechanisms. It does not establish universal non-benefit.

