# V3 research frame: repeat issue #377 without rewriting V2

Status: **pre-observation frame**. This file and all decision-critical source
must be committed and pushed before the first provider-backed preflight or
scored observation.

## Question

Does a durable, workflow-scoped handoff improve externally verified dependent
workflow outcomes or repeated resource measurements over current Hermes
artifact and Kanban handoff on `main@c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf`?

V3 repeats the bounded A/B/C comparison. It does not evaluate general shared
memory, CAMEL, a workflow engine, or a proposed production API.

## Changes from V2

1. The protocol and source seal are published in a remote commit before any
   provider-backed observation. GitHub therefore supplies the chronology V2
   could only assert locally.
2. `kanban_block` targeting the worker's own active card is an observed terminal
   outcome. A foreign task target remains an integrity violation.
3. C commits context to SQLite, closes the writer, and reads committed values
   from a fresh process. The in-memory V2 store is no longer the scored C
   treatment.
4. Three frozen cohorts are mandatory: Haiku at seeds 377 and 378, and Sonnet
   at seed 377.
5. Public evidence contains privacy-safe lifecycle receipts and the public
   verifier recomputes the decision instead of trusting `receipt.json`.
6. The report will say “archived run complete; product question unresolved”
   whenever the result is inconclusive.

## Checkable criteria

| id | criterion |
| --- | --- |
| AC1 | Every observation targets the clean exact target SHA. |
| AC2 | A public remote commit containing the exact protocol seal predates every provider-backed observation. |
| AC3 | All 18 frozen fixture/cohort pairs run or are recorded as provider failures; no observation is silently dropped. |
| AC4 | Own-task blocking is scored as an outcome; every foreign Kanban task target invalidates the fixture. |
| AC5 | Every C handoff is committed, writer-closed, and read by a fresh process before consumer dispatch. |
| AC6 | Public evidence independently recomputes the decision and rejects a mutated receipt. |
| AC7 | Raw traces remain private while lifecycle receipts expose operation, own/foreign relation, and hashed identities. |
| AC8 | No Hermes production file or upstream issue/PR is changed by the experiment. |

Coverage is a mapping contract, not proof that the experimental design is
good. The adversarial review must challenge the frame before sealing.

## Closed questions

- **Target:** current GitHub `main` verified identical to the SHA above at frame
  creation.
- **Models:** `claude-haiku-4-5` twice and `claude-sonnet-4-6` once through the
  same `claude-code` provider path.
- **Remote boundary:** local cross-process durability is part of C. A Docker
  probe may be reported separately, but it is not multi-host evidence and
  cannot change the product verdict.
- **Prior work:** real Kanban/file handoff remains B. Open persistent-memory,
  Hindsight, cron-notepad, and private deployment reports remain adjacent
  evidence, not replacement arms.

## Non-goals

- no implementation PR;
- no new core tool;
- no claim of equivalence;
- no retrospective modification of V2; and
- no multi-host, SSH, or Modal claim unless actually exercised in a separately
  declared experiment.

