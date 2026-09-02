# Adversarial falsification of the V2 pilot conclusion

Reviewed artifacts:

- `PROTOCOL_FREEZE_V2.md` and `PROTOCOL_SEAL_V2.json`;
- the private pilot trace and sanitized packet for
  `issue377-v2-pilot-20260901`;
- `analysis_v2.py`; and
- the independent public-packet verifier.

Review configuration: James (`gpt-5.6-sol`, inherited reasoning
configuration) acted as a read-only adversary. The primary adjudicator then
checked every decision-relevant claim against the frozen protocol, executable
gate, sanitized evidence, and the specific private trace event at issue.

## Leading conclusion under attack

The frozen pilot must stop as `INCONCLUSIVE`; the invalid fixture cannot be
reinterpreted as an ordinary arm-A failure merely because that interpretation
would allow the remaining B/C evidence to be scored.

## Falsification attempts

| attack | finding | disposition |
| --- | --- | --- |
| The invalidity is a sanitizer, provenance, or parser defect. | The public packet verifies against the sealed source manifest and target; no evidence-pipeline defect was found. | Rejected. |
| `kanban_block` targeted foreign state and should simply count as arm-A scope expansion. | The private trace shows that A targeted its own active card and stated that it could not produce the requested SHA. | Factually rejected; this exposed a protocol-design limitation instead. |
| Honest own-task blocking should be scored as an adverse A outcome, leaving the pair valid. | The frozen protocol explicitly allows only three Kanban operations and declares every other operation invalid before scoring. `analysis_v2.py` requires every integrity value to be true. | Semantically plausible for a future protocol, but prohibited retroactively. |
| Passing controls make the dependent failure interpretable. | Controls prove that independent tasks received no artificial benefit and that the harness paths operated. They do not override dependent-fixture admission. | Rejected. |
| The remaining three fixtures are enough to apply the resource or fidelity threshold. | The sealed pilot gate requires all four dependent fixtures and returns no metric gate when one is invalid. | Rejected. Descriptive reporting is allowed; a product verdict is not. |
| B/C's false successes in the invalid fixture prove an implementation opportunity for C or a failure of B. | B and C both failed the external oracle; C preserved handoff fidelity but still produced the wrong result and reported success. The whole fixture is inadmissible under the frozen rule. | Rejected. |

## Adversarial verdict

`INCONCLUSIVE` is the only protocol-valid result. The pilot must not expand,
and none of `NO OPPORTUNITY`, `EXISTING HANDOFF SUFFICIENT`, or
`IMPLEMENTATION OPPORTUNITY` is supported by this frozen run.

## Primary adjudication

Accepted. The own-task `kanban_block` event is evidence that the integrity rule
was broader than the contamination risk it intended to control. It is not
evidence that the event may be reclassified after the result. The correct
research response is to preserve the immutable pilot, disclose the limitation,
and decline a product recommendation.

The three valid dependent observations may be summarized descriptively to
show what was observed, but they cannot be promoted into a new stopping rule,
an equivalence claim, or a reason to implement shared context.
