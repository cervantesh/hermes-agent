# V4 handoff-fidelity interpretation correction

## Correction

The frozen V4 primary/resource verdict remains `NO DEMONSTRATED INCREMENT`.
The secondary `C 12/12, B 8/12, A 2/12` count must not be interpreted as a
semantic data-fidelity advantage.

The frozen `handoff_fidelity` field for detached B required the parent summary
to contain the exact canonical JSON inside `<handoff-json>` tags. In the four B
rows scored false, the producer instead returned the same canonical JSON
without those tags. `_extract_handoff_block()` therefore returned an empty
string even though the parent summary retained the complete synthetic payload.

A post-run audit bound to the already published private raw SHA-256 found:

- 12/12 dependent producer summaries parsed to the exact source value;
- 8/12 used the exact tagged wrapper counted by the frozen metric; and
- three of the four wrapper-negative B consumers passed the external oracle.

The privacy-safe audit receipt publishes the cohort/task identifiers and
hashes of the producer summary, normalized payload, and deterministic expected
source. Its test regenerates each expected-source hash from the committed task
fixtures. The private raw output remains undisclosed, but its SHA-256 is bound
to both the original result receipt and this correction receipt.

The remaining wrapper-negative B outcome was `ordered_dependency_plan`. Every
arm failed that task's external oracle in at least one cohort because the
bounded file-only worker surface did not provide a SHA-256 computation tool.
It is not evidence that B lost the handoff payload.

## Disposition

The primary V4 verdict, control results, resource thresholds, and C/B-only
counts do not change. The secondary count is retained as a format-adherence
measurement because it was prospectively defined, but it is withdrawn as a
semantic-fidelity signal or rationale for product implementation.

Any follow-up experiment must begin from an independently reachable mechanism,
such as the existing 4 KiB parent-summary cap, and must first demonstrate a B
failure under an executable oracle before running a C comparison.

Reproduction:

```text
python -m evals.shared_context_research_v4.audit_handoff_semantics_v4 \
  --raw <private-raw-v4.jsonl> \
  --output <public-semantic-audit.json>
```
