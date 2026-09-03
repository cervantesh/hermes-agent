# Issue #375 Fidelity Research — Amendment 007

Status: `FROZEN_HARNESS_REPAIR_AFTER_INVALID_PILOT`

Amendment ID: `IP375-FIDELITY-AMENDMENT-007-TEX-LINEBREAKS-2026-09-03`

Parent protocol: `IP375-FIDELITY-EXECUTION-R1-2026-09-03 @ 78294319621e`

Frozen on: 2026-09-03 (America/Santo_Domingo)

## Trigger and observed evidence

The fresh pilot governed by Amendment 006 completed three pairs and
quarantined the fourth because the Sonnet judge did not place exactly two
numeric scores on its first output line. The sanitized pilot summary has
SHA-256
`de23203e73129c1c704eb014ea680ab21ad6282581a4be0770264f7cebb356d1`;
the sanitized quarantine receipt has SHA-256
`f64916545f71250816072d6dfd6619c2dd9a2d86739481ed1aaa2e2d1bfdab3d`.
No aggregate efficacy result was computed or inspected.

A source-fidelity audit then showed that the TeX parser preserved two inline
LaTeX `\\` line-break commands as literal backslashes inside the evaluation
instruction. Trailing `\\` commands in the template were already treated as
line breaks. The supplement uses the same command for both forms; neither is
intended provider prompt content.

## Decision

`_plain_lines` converts every TeX `\\` line-break command inside the selected
prompt boxes to a newline before normalizing lines. This changes only the
evaluation-instruction hash. All source prompt hashes after the repair are
bound by
`frozen_inputs/SOURCE_PROMPT_RECEIPT_AMENDMENT_007.json`; the original source
receipt and frozen-input seal remain preserved and continue to authenticate
the pre-amendment frame.

The exact evaluation wording, models, tasks, order, temperatures, judge parser,
quarantine rule, limits, and analysis remain unchanged. This amendment repairs
serialization of the published prompt; it does not relax the required judge
format.

## Evidence impact and rerun rule

The Amendment 006 pilot is valid evidence that provider transport, generation,
extraction, persistence, and quarantine paths execute, but it cannot pass the
pilot conformance gate and is never pooled or scored. A fresh four-task pilot
must run in a new output root. Only that fresh pilot can unlock the scored run.

The user-authorized USD 10 ceiling remains cumulative. The two invalid pilots
cost USD 0.515369 in total. The parser repair is covered by a regression test
that fails when an inline TeX line break reaches the effective prompt and
passes when it becomes a newline. This amendment is immutable after sealing.
