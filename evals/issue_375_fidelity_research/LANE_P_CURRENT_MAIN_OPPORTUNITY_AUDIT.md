# Lane P current-main opportunity audit

Parent freeze: `IP375-FIDELITY-INITIAL-2026-09-03 @ c8de22a6da21`

Execution protocol: `IP375-FIDELITY-EXECUTION-R1-2026-09-03 @ 78294319621e`

Audit target: `NousResearch/hermes-agent@25caae02c020f6dd7ecdc3eaf353ece85aeef09b`

Disposition: `NO_CURRENT_PRODUCT_OPPORTUNITY`

This is the Lane P opportunity gate required by the frozen protocol. It is a
current-product audit, not a CAMEL observation and not an efficacy result.
No model was called, no treatment was built, and no prior observation was
pooled into this disposition.

## Strict product question

Does the exact Phase 1 prompt-only treatment proposed in #375 improve an
externally verified outcome for a real `delegate_task` workflow that fails on
current `main`, is repeatable, and is not already owned by another issue or PR?

The gate requires all of the following before any model execution:

1. a real Hermes workflow rather than a prompt designed to induce the failure;
2. a current-main reproduction;
3. an executable external oracle;
4. a repeated RED; and
5. an independently closable, unowned causal gap.

No candidate found in the issue, current repository, or refreshed overlap
search met all five requirements.

## Current-main lifecycle audit

`tools/delegate_tool.py::_build_child_system_prompt()` currently supplies the
delegated task, optional context, workspace/project instructions, tool-use
direction, and a concise final-summary shape. It does not contain the four
Phase 1 directives proposed by #375. That absence confirms that the treatment
has not landed; it does not demonstrate that the treatment is needed.

The real child path builds this prompt, constructs an isolated child agent,
and calls `child.run_conversation(user_message=goal, ...)` inside
`delegated_child_context`. The ordinary conversation loop also contains
bounded recovery for trailing continue-intent, intent acknowledgements, and
dropped structured tool calls. `verify_on_stop` is available but defaults off
unless explicitly configured. These existing routes must remain enabled as
they are in production for any future Lane P witness.

The nine commits between the frozen Hermes baseline and the audit target alter
compression, cron prompt re-append behavior, gateway compaction status, and a
contributor mapping. None changes `tools/delegate_tool.py`, the child prompt,
or the delegation lifecycle used by Lane P. Lane R therefore remains pinned to
its original source revision; the current-main refresh affects only this Lane
P audit.

## Claimed failure modes

| Claimed mode | Current eligible RED | Evidence disposition |
| --- | --- | --- |
| Role flipping | No | #375 supplies an anecdotal example, but no current real workflow, repeated trace, or external oracle. |
| Instruction echoing | No | #375 supplies an anecdotal example, but no current real workflow, repeated trace, or external oracle. |
| Flake replies | No | #375's generic example is not executable. The concrete false-side-effect problem is separately owned by #16357. |
| Infinite loops | No | Concrete loops exist, but the refreshed cases have narrower non-prompt causes and their own owners (#11171 and #94858/#94956). |

## Candidate and ownership disposition

| Reference | Classification | Why it cannot seed this Lane P treatment |
| --- | --- | --- |
| #17561 | Competing treatment, no RED | Implements the same prompt-only idea, but its tests assert prompt text and its two observations do not provide a frozen current-main RED with an external oracle. |
| #79508 | Owned active PR | Reports a real progress-narration incident and owns its completion-contract treatment. It is not an unowned #375 candidate, and its public evidence does not provide a current repeatable harness. |
| #16357 | Owned structural gap | Tracks externally false subagent side-effect claims and explicitly distinguishes structural verification from a prompt nudge. |
| #74604 | Owned, no minimal reproducer | Tracks a general agent progress-narration failure after heavy compression and explicitly lacks a minimal reproducer; it is not isolated to the #375 child prompt. |
| #11171 | Owned different cause | Attributes Google-model retry behavior to missing toolsets and an unrecognized provider finish reason, with a different causal boundary and proposed fix. |
| #72901 | Fixed different cause | The concrete child tool-narration failure was closed on main by #100937/e71352a because the cause was streaming tool-call parsing, not missing inception text. |
| #94858/#94956 | Owned parent loop | The reproduced loop is a parent retrying control actions against a completed child; #94956 owns a structured non-retryable/circuit-breaker fix. |
| #100223 | Closed duplicate treatment | A later #375 prompt implementation was closed as a duplicate of #17561 and also bundled unrelated changes. |

The broader search also found prompt/verification and completion proposals,
including #30093 and #67713. They do not provide an eligible #375 baseline:
they either own a different contract or add treatment/visibility rather than a
current reproducible product RED.

## Gate result

Lane P stops before creating a task/oracle manifest because there is no
eligible case to place in it. Creating synthetic failure prompts or reusing old
successful/failed cohorts would violate the freeze. Re-running an already
owned incident solely to manufacture headroom would also fail the ownership
gate.

Accordingly:

- provider calls: `0`;
- efficacy observations: `0`;
- treatment freeze: not created;
- product treatment: not built;
- production code: unchanged; and
- upstream publication: none.

This disposition does not claim that the four behaviors never occur, that the
#375 treatment cannot help any model, or that the open overlapping PRs should
close. It means only that the prospectively required current, repeatable,
externally judged, unowned product RED was not available at this audit point.
A future real incident can reopen Lane P under a new current-main evidence
frame; it must not retroactively alter this receipt.

