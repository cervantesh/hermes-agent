# Pilot V1 disposition

Status: invalid for A/B/C product adjudication; retained as methodological
evidence and not pooled with any later run.

## What ran

Eighteen observations (six workflows by three arms) ran on the sealed V1
protocol against `main@180291162ff4df0d42b5dc4fecd08005cf7cebf9` using
`claude-haiku-4-5`. The two independent controls passed in every arm. No
provider failure occurred.

## Why the gate must not open

V1 ran a separate producer for every arm and required every producer to create
an exact artifact *and* repeat the entire canonical JSON byte-for-byte in its
completion summary. The artifact was exact in every dependent observation,
but at least one producer summary failed exactness in every paired fixture.

The sealed fairness rule says a failed producer validation invalidates all
three paired arms for that fixture. Therefore all four dependent pairs are
invalid. The first uncorrected aggregation mistakenly treated B's loss of
summary fidelity as an expansion trigger; enforcing the frozen paired-validity
rule correctly yields:

- `complete: false`
- `expand: false`
- `verdict: INCONCLUSIVE`

No V1 model output may be used to claim that A, B, or C is better.

## Useful non-product evidence

- Actual dispatcher workers, lifecycle tools, token receipts, context-section
  manifests, and external graders all functioned.
- Exact producer artifacts were reliable; exact long completion summaries were
  not reliable enough to serve as a cross-arm admission gate.
- Three consumers created undeclared helper scripts, and the scope oracle
  correctly rejected those otherwise plausible completions.
- A fidelity difference cannot be interpreted when the upstream values came
  from different stochastic producer runs.

## V2 correction boundary

V2 may not rewrite or pool V1. It must use one common producer observation per
fixture/seed, then expose the same producer artifact and completion summary to
all three consumer arms. Exact artifact production remains the admission gate;
summary fidelity becomes a measured property of A/B rather than a requirement
that selectively invalidates an arm.

Sanitized V1 evidence is preserved under `evidence/v1-invalid-pilot/` with raw
receipt hash `37c42f7fb6f5d0cd8a3d9ae004e92df6f44418342cb368389416edbe2eee1a41`.
