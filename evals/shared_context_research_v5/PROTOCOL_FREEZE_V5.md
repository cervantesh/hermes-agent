# Frozen V5 protocol: 4,096-character parent-summary gate

Status: **FINAL BEFORE REMOTE SEAL AND PROVIDER OBSERVATION**.

Target: clean `NousResearch/hermes-agent@c7429f60cadb21482c1e3e34ccf4f1014d887de8`.

## Fixtures

- `cap_below_control`: an ASCII canonical JSON source below 4,096 characters;
  the required final record must remain visible in current B.
- `cap_above_tail_dependency`: the same shape above 4,096 characters; the
  required opaque final record is outside current B's projection.

The selected id is supplied independently in `consumer_input.json`. The
external oracle requires the complete exact selected record. The opaque value
is deterministic but absent from the consumer instructions and workspace.

## Stages and stopping rule

1. A deterministic real-code structural probe must show the below-cap tail is
   visible and the above-cap tail is absent with a truncation marker.
2. Run only B for both fixtures using `claude-haiku-4-5`, seed 377.
3. Stop without running A or C unless the below-cap B result is exact and the
   above-cap B result is not exact, with both producers and schemas valid.
4. If that gate passes, run fresh A/B/C comparisons for both fixtures in
   `haiku-s377`, `haiku-s378`, and `sonnet-s377`. No observation is replaced.

The implementation-opportunity threshold is replicated C-only exact success on
the above-cap fixture in both Haiku seeds and Sonnet, with the below-cap control
green in B and C. Anything less is descriptive or inconclusive. Token and
latency deltas are secondary and cannot override outcome correctness.

The target cap is measured as characters because `_cap()` currently calls
`len(str)` despite the constant's `_BYTES` name. ASCII fixtures make the
character/byte distinction numerically inert here.

All code remains fork-only evaluation scaffolding. No production integration
is authorized by this protocol alone.
