# V2 protocol adversarial review and adjudication

Artifact reviewed: `PROTOCOL_FREEZE_V2.md` before V2 sealing, against
`main@180291162ff4df0d42b5dc4fecd08005cf7cebf9`.

Configuration: James (`gpt-5.6-sol`, inherited reasoning configuration) acted
as a read-only adversary with the V2/V1 documents and exact repository tree.
No external provider was invoked. The review was not model-calibrated for a
general repository verdict; every decision-relevant claim below was verified
by the adjudicator against the cited main tree.

## Candidate disposition

| candidate | evidence and disposition | amendment |
| --- | --- | --- |
| shared-storage B was both artifact-based and required to reference the producer summary | **CONFIRMED closure-falsifier.** The two written gates could not both hold. | Gate 2 is topology-specific: detached B references the persisted summary; shared B proves the artifact digest and absence of a parent link. |
| C could read the producer card by explicit ID on a shared board | **CONFIRMED closure-falsifier.** `tools/kanban_tools.py::_handle_show` accepts an explicit task ID and has no read-ownership check. | A/C now use independent homes and Kanban DBs; a real-path producer-ID sentinel must fail there and succeed in B. |
| distinct profile names could introduce configuration differences | **CONFIRMED closure-falsifier.** dispatcher workers resolve profile-scoped config before launch. | Every consumer is named `consumer` in an isolated home containing byte-identical config; semantic config and override receipts must match. |
| producer-free controls could not detect cross-board contamination | **CONFIRMED closure-falsifier under the original shared DB.** | DB isolation plus the explicit producer-ID sentinel exercises the previously reachable cross-card read. Consumer traces also reject non-own task IDs and cross-root reads. |
| cost/latency boundaries were underspecified | **CONFIRMED ambiguity; blocking before seal.** | Included/excluded timing segments and parent-token zero/missing semantics are frozen in a table. |
| unbalanced random order could correlate an arm with warm-up or degradation | **CONFIRMED proportional risk material to the resource gate.** | A blocked schedule uses all six permutations across the confirmation fixtures and near-balanced positions in the four-fixture pilot; exact orders are frozen. |
| empty or truncated common summary had no treatment rule | **CONFIRMED ambiguity.** | It is admitted when the artifact is valid, then scored as A/detached-B fidelity; shared B remains artifact-based. |
| negative outcome labels overlapped | **CONFIRMED wording ambiguity, not a metric defect.** | `NO OPPORTUNITY` is pilot-stop only; `EXISTING HANDOFF SUFFICIENT` requires an opened gate followed by negative confirmation. |

## Scope adjudication

All accepted amendments protect causal validity of the experiment. None adds
a Hermes product requirement or changes issue #377's scope. OS-level
filesystem denial, remote backends, persistent scratchpad recovery, and a
production authorization model remain broader architecture and unverified.

## Rebuttal pass

The adversary confirmed that the first-pass blockers were disposed of, then
identified two new closure-falsifiers:

1. shared-storage B allowed a post-producer harness copy, which would not be
   the existing shared-file baseline and could add treatment-only cost; and
2. lexical trace inspection could miss terminal enumeration, variables, or
   relative traversal into another temporary root.

Both are **CONFIRMED**. V2 now requires the producer to create the exact object
that B reads, with no later copy. All consumer profiles disable terminal,
process, code-execution, delegation, memory, and session-search surfaces; a
preflight proves their absence from the effective schema. Remaining file-tool
paths are resolved using main's own path semantics and checked against a
per-arm allow-list, so relative traversal and absolute/tilde paths are judged
by effective target rather than string matching. This does not claim OS-level
security outside the worker tool contract.

## Executable preflight and final closure passes

The first two unscored preflight attempts were rejected rather than pooled.
They exposed an ID-qualified `not found` parser mismatch and real
scope-expansion events. The parser was corrected; scope expansion was retained
as an adverse outcome rather than added to the allow-list. A third attempt
proved the two real lifecycle topologies and all then-current mechanical gates,
but it was not accepted as sealing evidence after the adversary identified two
additional provenance/trace closure-falsifiers:

1. V4A patch targets live inside patch text and could bypass a check of only
   `arguments.path`; and
2. the public receipt did not bind the exact protocol and harness source.

Both were confirmed. The auditor now extracts and resolves every V4A file
header and rejects an unparseable target set. A canonical source manifest binds
the decision-critical files before, during, and after execution, and the public
verifier recomputes it.

The next rebuttal found that the manifest omitted imported `runtime.py`, and
that C's stated readback digest was calculated from expected fixture input
rather than actual view bytes. Both were confirmed and fixed. `runtime.py` is
now in the manifest; C hashes only values returned by `view.read`, with a
corruption regression proving that altered readback produces a mismatch.

The final narrow adversarial recheck returned **READY**. It confirmed closure
of the V4A, provenance, and actual-readback falsifiers and found no direct
regression from those fixes. The adjudicator's local suite passed 34 tests; the
adversary could not locate this worktree's virtual environment and did not
claim an independent test run.

The first provenance-bound attempt then rejected every fixture on exact token
accounting. Durations reconciled, but the relay helper looked for a nested usage
object while current Hermes returns top-level counters, and a blocked consumer
omitted run metadata despite leaving exactly one session in its fresh isolated
profile. Missing usage was neither zero-filled nor accepted. The candidate now
reads the real relay counters and permits a consumer DB fallback only for one
unambiguous post-run session after a proven empty pre-run profile.

The fourth narrow recheck returned **READY**. Pinned main's finalizer confirms
that the relay fields are real turn counters. The consumer fallback is causally
bounded by the zero-session precondition, separate parent environment, and
exactly-one-row rule; zero or multiple sessions remain unresolved. Exact cost
validation still requires every numeric component and both the token and
duration sums.

Disposition: **READY for one final provenance-bound, unscored preflight.** A
successful packet plus creation of `PROTOCOL_SEAL_V2.json` authorizes the
frozen pilot. This review alone does not authorize scoring and makes no product
claim about issue #377.

That next attempt reconciled token and duration costs but rejected a
scope-expansion event in the complex detached fixture. Repeating until a model
randomly complied would select on outcome. The candidate therefore separates
mechanical admission from scored task difficulty: two dedicated trivial echo
fixtures exercise the same lifecycle and both topologies but are excluded by
construction from every scored cohort. Product fixtures and their scope rules
are unchanged.

The fifth narrow recheck returned **READY**. It confirmed that `preflight` only
labels the record, both echo fixtures traverse the identical runtime, their
orders are complete permutations, and cohort/table assertions make them
unreachable from product inference.

Final disposition: **READY for the provenance-bound dedicated preflight.** A
successful packet plus creation of `PROTOCOL_SEAL_V2.json` authorizes the
frozen pilot.
