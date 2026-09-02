# Adversarial review of the pre-seal protocol

Artifact reviewed: the first draft of `RESEARCH_FRAME.md`,
`OWNERSHIP_AUDIT.md`, and `PROTOCOL_FREEZE.md` against
`origin/main@180291162ff4df0d42b5dc4fecd08005cf7cebf9`.

Reviewer configuration: blind read-only Terra adversary, high reasoning, local
repository and `gh` inspection enabled. The adversary received the artifacts,
exact revision, and attack question, but not a preferred verdict.

## Adjudication

| Candidate | Evidence | Decision | Protocol change |
|---|---|---|---|
| B used a static Kanban projection but claimed the real lifecycle | delegated children strip the Kanban toolset; dispatcher workers use a different process/tool contract | confirmed closure falsifier | all arms now use actual dispatcher-owned workers, `kanban_show`, and `kanban_complete` |
| distinct fixture directories were not a proven child boundary | direct delegation has one parent workspace unless optional local Git isolation succeeds | confirmed closure falsifier | removed the unsupported isolation claim; detached-source workspaces are deleted before consumer dispatch, while remote backends remain unverified |
| global fail-closed truncation contradicted B | current `_cap()` supplies marked partial summary/metadata rather than raising | confirmed closure falsifier | fail-closed is a C gate; B truncation is a measured, scored limitation |
| B lacked a frozen canonical serialization | `complete_task()` accepts free-form summary and metadata | confirmed closure falsifier | one canonical JSON encoding and pre/post byte/digest checks are now frozen for every hop |
| resource aggregation could yield multiple verdicts | medians, seed populations, and discordance were underspecified | confirmed closure falsifier | paired unit, formula, eligible population, missing values, ties, and discordance are explicit |
| clean B context was assumed | Kanban context can include attempts, comments, history, events, and runs | proportional hardening accepted | each temporary board is clean and its context-section manifest is checked before dispatch |
| seed disagreement could be mislabeled sufficient | positive rule required both seeds but negative rule did not route opposite effects | proportional hardening accepted | material opposite-direction effects and bidirectional correctness discordance are `INCONCLUSIVE` |
| expansion median and threshold equality remained ambiguous after round one | the expansion gate had four fixtures but only the six-fixture confirmation formula was defined; `at least` conflicted with rejecting equality at threshold | confirmed closure falsifier in rebuttal | froze the four-fixture seed-377 formula, missing-value rules, and inclusive comparator for both gates |

## Rejected objections

- The GitHub ownership snapshot was not stale at review time: the cited issue
  and PR states and heads were rechecked.
- The Kanban parent-link handoff does exist on the pinned main. The defect was
  the first protocol's hybrid measurement, not the ownership claim.
- A 4 KiB cap does not invalidate arm B by itself; it is legitimate behavior to
  expose and score.
- One pilot repetition is not an automatic blocker because the protocol limits
  its claims and requires a second seed before a positive implementation
  verdict. The ambiguous aggregation rules were the actual blocker and were
  corrected.

## Disposition

`REQUEST CHANGES` on the first draft. All confirmed protocol blockers above
must be reflected and mechanically checked before the protocol is sealed. The
review does not establish that the revised experiment is executable; preflight
must still prove a real worker can run under the pinned provider/profile and
that tool-call evidence can verify `kanban_show` and `kanban_complete`.
